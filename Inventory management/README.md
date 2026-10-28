# 📦 StockFlow: Real-Time Inventory Management & Concurrency Test Lab

A refined inventory management system featuring both a **Modern Web Application** (HTML/CSS/JS frontend with a zero-dependency Python backend) and the original **Terminal CLI**.

---

## 🌟 Key Features

1. **📊 Real-Time Web Dashboard**:
   - Live KPI cards: Total SKUs, total units, real-time inventory valuation (₹), and stock health breakdown.
   - Low stock warning badges (`In Stock`, `Low Stock (<10)`, `Out of Stock`).
   - Dynamic search by product name/SKU/description, category filtering, and multi-field sorting.

2. **🔍 Product Details & Attributes Modal**:
   - Inspect all product attributes: Name, SKU, Category, Unit Price, Stock Quantity, Valuation, and Description.
   - Quick Actions: Direct Sell, Instant Restock, In-place Attribute Editing, and Deletion.
   - Add new products with SKU format validation (`PROD-XXXX`).

3. **⚡ Concurrency & Stress Test Suite**:
   - Configure simulated customer threads (1 to 200+ simultaneous buyers).
   - Target any product in your inventory with custom quantities and simulated network delay.
   - Live real-time progress bar, request counters, out-of-stock race condition detection, and before/after stock comparison.
   - Historical test log table tracking performance and latency across runs.

4. **📜 Live System & Audit Logs**:
   - Captured in real-time by the `@Logger.log_activity` decorator.
   - Terminal-style dark console in the UI with auto-scrolling, level filtering (`INFO`, `SUCCESS`, `ERROR`), and keyword search.
   - Dual-write architecture: persists to disk (`Acitvity.log`) and in-memory ring buffer for sub-millisecond UI rendering.

5. **⚙️ Zero External Dependencies**:
   - Built entirely using Python's standard library (`http.server.ThreadingHTTPServer`, `threading`, `json`, `urllib`).
   - Runs out-of-the-box on Python 3.8+ without needing `pip install` or complex virtual environments.

---

## 🚀 Quick Start

### Option 1: Run the Web Application (Recommended)

```bash
# Start the web server
python3 server.py
```

Then open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

### Option 2: Run the Terminal CLI

```bash
python3 main.py
```

---

## 📂 Project Structure

```
Inventory management/
├── server.py              # Multi-threaded HTTP REST API server (Python standard library)
├── inventory_system.py    # Core thread-safe inventory domain model & DataHandler
├── product.py             # Product class with category inference & valuation attributes
├── logger.py              # Activity logger with @log_activity decorator & dual-write buffer
├── test_runner.py         # Multi-threaded concurrency stress test & simulation engine
├── inventory.json         # Persisted inventory database (JSON format)
├── Acitvity.log           # Permanent transaction & activity log file
├── static/                # Modern Single-Page Application (SPA) frontend
│   ├── index.html         # Responsive dashboard layout & modals
│   ├── style.css          # Dark slate theme, glassmorphism, responsive styles
│   └── app.js             # Client state management, API calls, and telemetry polling
└── README.md              # Project documentation
```

---

## 🌐 REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves web app frontend (`index.html`) |
| `GET` | `/api/stats` | Summary statistics (total items, valuation, health) |
| `GET` | `/api/products` | Query products (`?query=...&category=...&stock_status=...&sort_by=...`) |
| `GET` | `/api/products/<SKU>` | Retrieve a single product by SKU |
| `POST` | `/api/products` | Create a new product |
| `PUT` | `/api/products/<SKU>` | Update product name, price, category, description |
| `POST` | `/api/products/<SKU>/sell` | Sell units of a product (`{"amount": 1}`) |
| `POST` | `/api/products/<SKU>/restock` | Restock units of a product (`{"amount": 10}`) |
| `DELETE` | `/api/products/<SKU>` | Remove a product from inventory |
| `GET` | `/api/logs` | Fetch system audit logs (`?limit=100&level=INFO&q=...`) |
| `POST` | `/api/tests/run` | Launch concurrency test (`{"sku": "PROD-1002", "threads": 100}`) |
| `GET` | `/api/tests/status` | Real-time test progress & past runs history |
