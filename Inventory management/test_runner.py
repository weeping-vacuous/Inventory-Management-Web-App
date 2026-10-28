import threading
import time
import random
import uuid
from logger import Logger
from inventory_system import ProductNotFoundError, InsufficientStockError

class TestSimulationRunner:
    def __init__(self, inventory):
        self.inventory = inventory
        self.lock = threading.Lock()
        self.active_test = None
        self.history = []

    def get_status(self):
        """Returns the current status of the active test run and recent test history."""
        with self.lock:
            active_info = None
            if self.active_test:
                active_info = dict(self.active_test)
                # Calculate live progress percentage
                total = active_info.get("total_threads", 0)
                completed = active_info.get("completed_threads", 0)
                active_info["progress_percent"] = round((completed / total * 100), 1) if total > 0 else 0
                if active_info.get("status") == "running":
                    active_info["elapsed_ms"] = round((time.time() - active_info["start_time"]) * 1000, 1)

            return {
                "active_test": active_info,
                "history": list(reversed(self.history[-10:])) # Latest first
            }

    def start_concurrency_test(self, sku="PROD-1002", num_threads=100, amount_per_thread=1, delay_ms=0):
        """Launches a concurrent sales stress test in a background thread."""
        with self.lock:
            if self.active_test and self.active_test.get("status") == "running":
                raise RuntimeError("A test run is already in progress. Please wait for it to complete.")

            # Validate product exists
            try:
                product = self.inventory.get_product(sku)
                initial_stock = product.quantity
                product_name = product.name
            except ProductNotFoundError:
                raise ValueError(f"Cannot run test: Product with SKU '{sku}' does not exist.")

            test_id = str(uuid.uuid4())[:8]
            self.active_test = {
                "id": test_id,
                "type": "concurrency_stress_test",
                "sku": sku,
                "product_name": product_name,
                "initial_stock": initial_stock,
                "final_stock": None,
                "total_threads": int(num_threads),
                "completed_threads": 0,
                "amount_per_thread": int(amount_per_thread),
                "delay_ms": int(delay_ms),
                "successful_sales": 0,
                "out_of_stock_failures": 0,
                "other_errors": 0,
                "error_messages": [],
                "status": "running",
                "start_time": time.time(),
                "duration_ms": 0
            }

        # Start execution in a dedicated background worker thread
        worker = threading.Thread(
            target=self._run_concurrency_worker,
            args=(test_id, sku, num_threads, amount_per_thread, delay_ms),
            daemon=True
        )
        worker.start()
        return self.active_test

    def _run_concurrency_worker(self, test_id, sku, num_threads, amount_per_thread, delay_ms):
        """Worker executing concurrent threads against the inventory."""
        Logger.log(f"[TEST RUN {test_id}] Started concurrency stress test: {num_threads} customers buying SKU {sku}", level="INFO")
        
        threads = []
        for i in range(num_threads):
            t = threading.Thread(
                target=self._simulate_customer_purchase,
                args=(sku, amount_per_thread, delay_ms, i + 1)
            )
            threads.append(t)

        start_time = time.time()
        for t in threads:
            t.start()
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

        for t in threads:
            t.join()

        duration = round((time.time() - start_time) * 1000, 2)

        with self.lock:
            if self.active_test and self.active_test["id"] == test_id:
                try:
                    current_stock = self.inventory.get_product(sku).quantity
                except Exception:
                    current_stock = "N/A"

                self.active_test["status"] = "completed"
                self.active_test["final_stock"] = current_stock
                self.active_test["duration_ms"] = duration
                
                # Append copy to history
                self.history.append(dict(self.active_test))
                
        Logger.log(
            f"[TEST RUN {test_id}] Completed in {duration}ms. "
            f"Success: {self.active_test['successful_sales']}, "
            f"Out of stock: {self.active_test['out_of_stock_failures']}, "
            f"Remaining stock: {current_stock}",
            level="SUCCESS"
        )

    def _simulate_customer_purchase(self, sku, amount, delay_ms, customer_id):
        """Individual customer thread operation."""
        try:
            self.inventory.sell_product(sku, amount)
            with self.lock:
                if self.active_test:
                    self.active_test["successful_sales"] += 1
                    self.active_test["completed_threads"] += 1
        except InsufficientStockError:
            with self.lock:
                if self.active_test:
                    self.active_test["out_of_stock_failures"] += 1
                    self.active_test["completed_threads"] += 1
        except Exception as e:
            with self.lock:
                if self.active_test:
                    self.active_test["other_errors"] += 1
                    self.active_test["completed_threads"] += 1
                    if str(e) not in self.active_test["error_messages"]:
                        self.active_test["error_messages"].append(str(e))
