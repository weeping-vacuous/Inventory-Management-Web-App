#!/usr/bin/env python3
"""
Inventory Management Web Application Server
A clean, zero-dependency HTTP REST API backend built entirely with Python standard library.
"""

import json
import os
import mimetypes
import urllib.parse
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from product import Product
from inventory_system import DataHandler, ProductNotFoundError, InsufficientStockError
from test_runner import TestSimulationRunner
from logger import Logger

PORT = 8000
DATA_FILE = 'inventory.json'
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Initialize data and services
data_handler = DataHandler()
inventory = data_handler.load_inventory(DATA_FILE, auto_save=True)
test_runner = TestSimulationRunner(inventory)


class InventoryRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP Request Handler managing REST API routes and static asset serving.
    Each incoming connection runs on its own thread via ThreadingHTTPServer.
    """

    def log_message(self, format, *args):
        """Silences standard BaseHTTPRequestHandler console spam for cleaner output."""
        pass

    # --- HTTP Pipeline Helpers ---

    def send_json(self, data, status=HTTPStatus.OK):
        """Pipeline Stage: Serializes Python dict/list to JSON and writes HTTP response."""
        response_bytes = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response_bytes)

    def send_error_json(self, message, status=HTTPStatus.BAD_REQUEST):
        """Sends a structured JSON error response."""
        self.send_json({"error": True, "message": str(message)}, status=status)

    def read_json_body(self):
        """Pipeline Stage: Reads raw request stream by Content-Length and parses JSON."""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length <= 0:
            return {}
        raw_body = self.rfile.read(content_length).decode('utf-8')
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON in request payload: {e}")

    def do_OPTIONS(self):
        """Handles CORS pre-flight requests from modern web browsers."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # --- Static File Pipeline ---

    def serve_static(self, file_path):
        """Pipeline Stage: Static File Delivery for HTML, CSS, JavaScript, and Icons."""
        clean_path = os.path.normpath(file_path).lstrip('/')
        if not clean_path or clean_path == '.':
            clean_path = 'index.html'

        abs_file_path = os.path.join(STATIC_DIR, clean_path)

        # Security check: Prevent path traversal attacks outside static/
        if not os.path.commonpath([abs_file_path, STATIC_DIR]) == STATIC_DIR or not os.path.isfile(abs_file_path):
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        mime_type, _ = mimetypes.guess_type(abs_file_path)
        mime_type = mime_type or 'application/octet-stream'

        try:
            with open(abs_file_path, 'rb') as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.end_headers()
            self.wfile.write(f"500 Internal Error: {e}".encode('utf-8'))

    # --- HTTP Routing Pipeline: GET ---

    def do_GET(self):
        """Pipeline Stage: GET Request Dispatcher."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Helper to get single query parameter value
        def param(key, default=None):
            return query_params.get(key, [default])[0]

        try:
            # 1. API: Dashboard Stats Summary
            if path == '/api/stats':
                stats = inventory.get_stats()
                return self.send_json(stats)

            # 2. API: List / Search / Filter Products
            elif path == '/api/products':
                products = inventory.search_and_filter(
                    query=param('query'),
                    category=param('category'),
                    stock_status=param('stock_status'),
                    sort_by=param('sort_by', 'name'),
                    order=param('order', 'asc')
                )
                return self.send_json({"total": len(products), "products": products})

            # 3. API: Single Product Details: /api/products/<SKU>
            elif path.startswith('/api/products/'):
                sku = path[len('/api/products/'):]
                product = inventory.get_product(sku)
                return self.send_json(product.to_dict())

            # 4. API: System Activity Logs
            elif path == '/api/logs':
                limit = int(param('limit', '100'))
                level = param('level')
                q = param('q')
                logs = Logger.get_recent_logs(limit=limit, level_filter=level, query=q)
                return self.send_json({"count": len(logs), "logs": logs})

            # 5. API: Test Simulation Status & History
            elif path == '/api/tests/status':
                status_info = test_runner.get_status()
                return self.send_json(status_info)

            # Fallback: Serve Frontend Static Assets
            else:
                return self.serve_static(path)

        except ProductNotFoundError as e:
            return self.send_error_json(e, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            Logger.log(f"Unhandled GET error on {path}: {e}", level="ERROR")
            return self.send_error_json(e, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    # --- HTTP Routing Pipeline: POST ---

    def do_POST(self):
        """Pipeline Stage: POST Request Dispatcher."""
        path = urllib.parse.urlparse(self.path).path

        try:
            body = self.read_json_body()

            # 1. API: Add New Product
            if path == '/api/products':
                name = body.get('name')
                sku = body.get('sku')
                price = body.get('price')
                quantity = body.get('quantity', 0)
                category = body.get('category')
                description = body.get('description', '')

                if not name or not sku or price is None:
                    return self.send_error_json("Fields 'name', 'sku', and 'price' are required.")

                if not Product.is_valid_sku(sku):
                    return self.send_error_json("Invalid SKU format. Must start with 'PROD-' followed by identifier (e.g. PROD-1099).")

                # If product already exists, prevent duplicate or restock
                if sku.upper() in inventory.products:
                    return self.send_error_json(f"Product with SKU '{sku}' already exists. Use Restock or Edit instead.")

                new_product = Product(name, sku, price, quantity, category, description)
                inventory.add_product(new_product)
                return self.send_json(new_product.to_dict(), status=HTTPStatus.CREATED)

            # 2. API: Restock Product: /api/products/<SKU>/restock
            elif path.startswith('/api/products/') and path.endswith('/restock'):
                sku = path[len('/api/products/'):-len('/restock')]
                amount = int(body.get('amount', 0))
                updated = inventory.restock_product(sku, amount)
                return self.send_json(updated.to_dict())

            # 3. API: Sell Product: /api/products/<SKU>/sell
            elif path.startswith('/api/products/') and path.endswith('/sell'):
                sku = path[len('/api/products/'):-len('/sell')]
                amount = int(body.get('amount', 1))
                updated = inventory.sell_product(sku, amount)
                return self.send_json(updated.to_dict())

            # 4. API: Launch Concurrency / Stress Test Run
            elif path == '/api/tests/run':
                sku = body.get('sku', 'PROD-1002')
                threads = int(body.get('threads', 100))
                amount = int(body.get('amount', 1))
                delay_ms = int(body.get('delay_ms', 0))
                
                run_info = test_runner.start_concurrency_test(
                    sku=sku,
                    num_threads=threads,
                    amount_per_thread=amount,
                    delay_ms=delay_ms
                )
                return self.send_json(run_info, status=HTTPStatus.ACCEPTED)

            else:
                return self.send_error_json("Route not found.", status=HTTPStatus.NOT_FOUND)

        except InsufficientStockError as e:
            return self.send_error_json(e, status=HTTPStatus.CONFLICT)
        except ProductNotFoundError as e:
            return self.send_error_json(e, status=HTTPStatus.NOT_FOUND)
        except ValueError as e:
            return self.send_error_json(e, status=HTTPStatus.BAD_REQUEST)
        except RuntimeError as e:
            return self.send_error_json(e, status=HTTPStatus.CONFLICT)
        except Exception as e:
            Logger.log(f"Unhandled POST error on {path}: {e}", level="ERROR")
            return self.send_error_json(e, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    # --- HTTP Routing Pipeline: PUT ---

    def do_PUT(self):
        """Pipeline Stage: PUT Request Dispatcher for updating product attributes."""
        path = urllib.parse.urlparse(self.path).path

        try:
            body = self.read_json_body()

            # Update Product: /api/products/<SKU>
            if path.startswith('/api/products/'):
                sku = path[len('/api/products/'):]
                updated = inventory.update_product_details(
                    sku=sku,
                    name=body.get('name'),
                    price=body.get('price'),
                    category=body.get('category'),
                    description=body.get('description')
                )
                return self.send_json(updated.to_dict())
            else:
                return self.send_error_json("Route not found.", status=HTTPStatus.NOT_FOUND)

        except ProductNotFoundError as e:
            return self.send_error_json(e, status=HTTPStatus.NOT_FOUND)
        except ValueError as e:
            return self.send_error_json(e, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            Logger.log(f"Unhandled PUT error on {path}: {e}", level="ERROR")
            return self.send_error_json(e, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    # --- HTTP Routing Pipeline: DELETE ---

    def do_DELETE(self):
        """Pipeline Stage: DELETE Request Dispatcher for removing products."""
        path = urllib.parse.urlparse(self.path).path

        try:
            if path.startswith('/api/products/'):
                sku = path[len('/api/products/'):]
                deleted = inventory.delete_product(sku)
                return self.send_json({"success": True, "deleted_sku": sku, "name": deleted.name})
            else:
                return self.send_error_json("Route not found.", status=HTTPStatus.NOT_FOUND)

        except ProductNotFoundError as e:
            return self.send_error_json(e, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            Logger.log(f"Unhandled DELETE error on {path}: {e}", level="ERROR")
            return self.send_error_json(e, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def run(port=PORT):
    """Starts the multi-threaded HTTP server."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, InventoryRequestHandler)

    print("=" * 60)
    print(f"  🚀 Inventory Management Server running at:")
    print(f"     👉 http://localhost:{port}")
    print(f"     👉 http://127.0.0.1:{port}")
    print("=" * 60)
    print(f"  📦 Products loaded: {len(inventory)}")
    print(f"  📁 Data file: {DATA_FILE}")
    print(f"  🌐 Static files directory: {STATIC_DIR}")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.server_close()
        print("Server stopped.")


if __name__ == '__main__':
    run()
