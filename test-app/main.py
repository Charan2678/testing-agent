from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import os
import sys

# Ensure local test-app directory is on path for db import
sys.path.insert(0, os.path.dirname(__file__))
from db import init_crm_db, get_connection

app = FastAPI(title="QA Target Test Application")

@app.on_event("startup")
def startup_event():
    init_crm_db()

def get_head(title: str) -> str:
    return f"""
    <head>
        <title>{title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; margin: 0; padding: 0; }}
            nav {{ background: #0f172a; color: white; padding: 14px 28px; display: flex; justify-content: space-between; align-items: center; }}
            nav a {{ color: #94a3b8; text-decoration: none; margin-left: 20px; font-weight: 500; font-size: 14px; }}
            nav a:hover {{ color: white; }}
            .container {{ max-width: 960px; margin: 40px auto; padding: 0 20px; }}
            .card {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
            h1 {{ margin-top: 0; font-size: 24px; color: #0f172a; }}
            button, .btn {{ background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; text-decoration: none; display: inline-block; }}
            button:hover, .btn:hover {{ background: #1d4ed8; }}
            input, select {{ width: 100%; padding: 8px 12px; margin-top: 6px; margin-bottom: 16px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
            th {{ background: #f1f5f9; font-weight: 600; }}
        </style>
    </head>
    """

NAV_BAR = """
<nav>
    <div style="font-weight: 700; font-size: 16px;">Test Target CRM</div>
    <div>
        <a href="/dashboard">Dashboard</a>
        <a href="/products">Products</a>
        <a href="/orders">Orders</a>
        <a href="/profile">Profile</a>
        <a href="/login">Logout</a>
    </div>
</nav>
"""

@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return f"""
    <!DOCTYPE html>
    <html>
    {get_head("User Login - QA Target")}
    <body>
        <div class="container" style="max-width: 400px; margin-top: 80px;">
            <div class="card">
                <h1>Sign in to CRM</h1>
                <form action="/dashboard" method="get">
                    <label>Username or Email</label>
                    <input type="text" name="username" placeholder="admin@example.com" required>
                    <label>Password</label>
                    <input type="password" name="password" placeholder="••••••••" required>
                    <button type="submit" id="login-submit" style="width: 100%;">Sign In</button>
                </form>
                <p style="text-align: center; margin-top: 16px; font-size: 13px;">
                    <a href="/dashboard" id="bypass-login">Explore as Guest</a>
                </p>
            </div>
        </div>
        <script>
            console.log("Login page loaded successfully.");
        </script>
    </body>
    </html>
    """

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return f"""
    <!DOCTYPE html>
    <html>
    {get_head("CRM Dashboard")}
    <body>
        {NAV_BAR}
        <div class="container">
            <div class="card">
                <h1>Welcome to Dashboard</h1>
                <p>Overview of current system activity, sales performance, and recent operations.</p>
                <div style="display: flex; gap: 12px; margin-top: 20px;">
                    <a href="/products" class="btn" id="nav-products">Manage Products</a>
                    <a href="/orders" class="btn" id="nav-orders">View Orders</a>
                    <button id="btn-export">Export Summary</button>
                </div>
            </div>
        </div>
        <script>
            console.log("Dashboard loaded.");
            document.getElementById("btn-export")?.addEventListener("click", function() {{
                // Bug: Attempting to call non-existent method on undefined reports service
                window.reportsService.generateCsv();
            }});
        </script>
    </body>
    </html>
    """

@app.get("/products", response_class=HTMLResponse)
def products_page(title: str = None, category: str = None, price: str = None):
    # Simulated realistic application defect: Negative or zero price causes unhandled backend failure
    if price is not None:
        try:
            p_val = float(price)
            if p_val <= 0:
                raise HTTPException(
                    status_code=500,
                    detail="Database constraint violation: Product price must be greater than $0.00 (SQL_ERR_CHECK_PRICE_POSITIVE)"
                )
            
            # Phase 6 data integrity test scenario:
            # If title is "Data Bug Widget" or "Price Corrupt Test", store 10x the price in DB
            stored_price = p_val * 10 if title in ("Data Bug Widget", "Price Corrupt Test") else p_val
            cat_map = {"saas": 1, "services": 2, "infrastructure": 3}
            cat_id = cat_map.get((category or "saas").lower(), 1)

            conn = get_connection()
            conn.execute(
                "INSERT INTO products (title, description, price, category_id) VALUES (?, ?, ?, ?)",
                (title or "New Product", "Added via QA workflow", stored_price, cat_id)
            )
            conn.commit()
            conn.close()
        except ValueError:
            pass

    # Read live products from real database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.title, c.name as category, p.price 
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id 
        ORDER BY p.id ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    table_rows = "".join([
        f"<tr><td>#{r['id']}</td><td>{r['title']}</td><td>{r['category'] or 'General'}</td><td>${float(r['price']):.2f}</td></tr>"
        for r in rows
    ])

    return f"""
    <!DOCTYPE html>
    <html>
    {get_head("Products Catalog")}
    <body>
        {NAV_BAR}
        <div class="container">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h1>Product Management</h1>
                    <a href="/products/create" class="btn" id="btn-add-product">+ Add Product</a>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Product ID</th>
                            <th>Title</th>
                            <th>Category</th>
                            <th>Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>
        <script>
            console.log("Products page rendered with live database items.");
        </script>
    </body>
    </html>
    """

@app.get("/products/create", response_class=HTMLResponse)
def create_product_page():
    return f"""
    <!DOCTYPE html>
    <html>
    {get_head("Create New Product")}
    <body>
        {NAV_BAR}
        <div class="container" style="max-width: 600px;">
            <div class="card">
                <h1>New Product Entry</h1>
                <form action="/products" method="get">
                    <label>Product Title</label>
                    <input type="text" name="title" placeholder="e.g. Premium Analytics" required>
                    <label>Category</label>
                    <select name="category">
                        <option value="saas">Software as a Service</option>
                        <option value="infrastructure">Infrastructure</option>
                        <option value="support">Support & SLA</option>
                    </select>
                    <label>Price (USD)</label>
                    <input type="number" name="price" placeholder="199" required>
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <button type="submit" id="btn-save-product">Save Product</button>
                        <a href="/products" class="btn" style="background: #64748b;">Cancel</a>
                    </div>
                </form>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/orders", response_class=HTMLResponse)
def orders_page():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.order_number, u.username, o.total_amount, o.status
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        ORDER BY o.id ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    order_rows = "".join([
        f"<tr><td>{r['order_number']}</td><td>{r['username']}</td><td>${float(r['total_amount']):.2f}</td><td>{r['status']}</td></tr>"
        for r in rows
    ])

    return f"""
    <!DOCTYPE html>
    <html>
    {get_head("Order History")}
    <body>
        {NAV_BAR}
        <div class="container">
            <div class="card">
                <h1>Customer Orders</h1>
                <table>
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Customer</th>
                            <th>Amount</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {order_rows}
                    </tbody>
                </table>
            </div>
        </div>
        <script>
            console.warn("Order cache revalidation pending for ORD-9022");
        </script>
    </body>
    </html>
    """

@app.get("/profile", response_class=HTMLResponse)
def profile_page():
    return f"""
    <!DOCTYPE html>
    <html>
    {get_head("User Profile")}
    <body>
        {NAV_BAR}
        <div class="container" style="max-width: 500px;">
            <div class="card">
                <h1>User Account Settings</h1>
                <label>Full Name</label>
                <input type="text" name="fullname" value="Alex QA Lead">
                <label>Email Address</label>
                <input type="email" name="email" value="alex.lead@example.com">
                <button id="btn-save-profile">Update Profile</button>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3000)
