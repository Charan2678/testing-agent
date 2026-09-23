# Autonomous AI Testing and QA Agent

## Phase 1: Autonomous Application Explorer

An AI-powered QA system that accepts an application's environment URL, autonomously explores the application, understands its pages and interactive workflows, executes automated tests, investigates failures, identifies bugs, and generates evidence-based QA reports.

---

### Phase 1 Scope: Real Application Exploration
- **Target App Exploration**: Launch real Playwright Chromium browser to crawl application endpoints.
- **Element Discovery**: Extract buttons, inputs, links, forms, and interactive controls with resilient CSS selectors.
- **Evidence Collection**: Record real-time console messages, console errors, network requests, failed requests, and page screenshots.
- **Zero Dummy Data**: Every metric, record, and log originates from actual executions stored in the database.

---

### Project Structure
```
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   ├── database/
│   │   ├── api/
│   │   ├── browser/
│   │   └── services/
│   └── requirements.txt
├── frontend/
├── playwright/
├── artifacts/
│   ├── screenshots/
│   ├── videos/
│   ├── traces/
│   └── logs/
├── docker-compose.yml
├── .env.example
└── .env
```

---

### Getting Started

#### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Install dependencies:
pip install -r requirements.txt
playwright install chromium
# Run FastAPI server:
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
