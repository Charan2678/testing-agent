import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "crm_development.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_crm_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Categories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Products
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        price DECIMAL(10, 2) NOT NULL,
        category_id INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT
    )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_title ON products(title)")

    # 3. Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(100) NOT NULL UNIQUE,
        email VARCHAR(255) NOT NULL UNIQUE,
        role VARCHAR(50) DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. Orders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number VARCHAR(50) NOT NULL UNIQUE,
        user_id INTEGER NOT NULL,
        total_amount DECIMAL(10, 2) NOT NULL,
        status VARCHAR(50) DEFAULT 'completed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT
    )
    """)

    # 5. Order Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        price DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE RESTRICT
    )
    """)

    # Seed initial data if empty
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO categories (name, description) VALUES ('SaaS', 'Cloud and subscription software')")
        cursor.execute("INSERT INTO categories (name, description) VALUES ('Services', 'Professional and security services')")
        cursor.execute("INSERT INTO categories (name, description) VALUES ('Infrastructure', 'Dedicated hosting and API gateways')")
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO products (title, description, price, category_id) VALUES ('Enterprise Cloud Suite', 'Flagship SaaS platform', 499.00, 1)")
        cursor.execute("INSERT INTO products (title, description, price, category_id) VALUES ('Security Audit Package', 'Full security compliance audit', 1200.00, 2)")
        cursor.execute("INSERT INTO products (title, description, price, category_id) VALUES ('Dedicated API Gateway', 'High-throughput ingress proxy', 250.00, 3)")
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, email, role) VALUES ('alex.lead', 'alex.lead@example.com', 'admin')")
        cursor.execute("INSERT INTO users (username, email, role) VALUES ('sarah.qa', 'sarah.qa@example.com', 'qa_engineer')")
        cursor.execute("INSERT INTO users (username, email, role) VALUES ('acme.client', 'client@acme.com', 'customer')")
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO orders (order_number, user_id, total_amount, status) VALUES ('ORD-9021', 3, 1497.00, 'Completed')")
        cursor.execute("INSERT INTO orders (order_number, user_id, total_amount, status) VALUES ('ORD-9022', 2, 499.00, 'Processing')")
        cursor.execute("INSERT INTO orders (order_number, user_id, total_amount, status) VALUES ('ORD-9023', 1, 2400.00, 'Completed')")
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_crm_db()
    print("CRM Database initialized at:", DB_PATH)
