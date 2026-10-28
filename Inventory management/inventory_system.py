from product import Product
import json
from logger import Logger
import threading

class ProductNotFoundError(Exception): pass
class InsufficientStockError(Exception): pass
class DuplicateProductError(Exception): pass

class Inventory:
    def __init__(self, auto_save_file=None):
        self.products = {}
        self.lock = threading.Lock()
        self.auto_save_file = auto_save_file

    def _auto_save(self):
        """Internal helper to automatically sync in-memory state to disk."""
        if self.auto_save_file:
            try:
                data_to_save = {sku: prod.to_dict() for sku, prod in self.products.items()}
                with open(self.auto_save_file, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=4)
            except Exception as e:
                Logger.log(f"Auto-save to {self.auto_save_file} failed: {e}", level="ERROR")

    @Logger.log_activity
    def add_product(self, product):
        """Adds a new product to inventory in a thread-safe manner."""
        with self.lock:
            self.products[product.sku] = product
            self._auto_save()
            return product

    @Logger.log_activity
    def sell_product(self, sku, amount):
        """Reduces quantity of product if sufficient stock exists; raises error otherwise."""
        with self.lock:
            if amount <= 0:
                raise ValueError(f"Sale amount must be greater than zero. Received: {amount}")

            if sku not in self.products:
                raise ProductNotFoundError(f"Product with SKU '{sku}' not found in inventory.")

            product = self.products[sku]
            if product.quantity >= amount:
                product.quantity -= amount
                self._auto_save()
                return product
            else:
                raise InsufficientStockError(
                    f"Not enough stock of '{product.name}' (SKU: {sku}) to sell {amount}. Current stock: {product.quantity}"
                )

    @Logger.log_activity
    def update_item_price(self, sku, price):
        """Updates the unit price of an existing product."""
        with self.lock:
            if sku not in self.products:
                raise ProductNotFoundError(f"Product with SKU '{sku}' not found in inventory.")
            
            p_val = float(price)
            if p_val < 0:
                raise ValueError("Product price cannot be negative.")

            product = self.products[sku]
            product.price = round(p_val, 2)
            self._auto_save()
            return product

    @Logger.log_activity
    def restock_product(self, sku, amount):
        """Increases product quantity by specified amount."""
        with self.lock:
            if sku not in self.products:
                raise ProductNotFoundError(f"Product with SKU '{sku}' not found in inventory.")
            
            amt = int(amount)
            if amt <= 0:
                raise ValueError(f"Restock amount must be greater than zero. Received: {amt}")
            
            product = self.products[sku]
            product.quantity += amt
            self._auto_save()
            return product

    @Logger.log_activity
    def update_product_details(self, sku, name=None, price=None, category=None, description=None):
        """Updates attributes of an existing product."""
        with self.lock:
            if sku not in self.products:
                raise ProductNotFoundError(f"Product with SKU '{sku}' not found in inventory.")
            
            product = self.products[sku]
            if name:
                product.name = str(name).strip()
            if price is not None:
                p_val = float(price)
                if p_val < 0:
                    raise ValueError("Price cannot be negative.")
                product.price = round(p_val, 2)
            if category:
                product.category = str(category).strip()
            if description is not None:
                product.description = str(description).strip()
            
            self._auto_save()
            return product

    @Logger.log_activity
    def delete_product(self, sku):
        """Deletes a product from the inventory."""
        with self.lock:
            if sku not in self.products:
                raise ProductNotFoundError(f"Product with SKU '{sku}' not found in inventory.")
            deleted = self.products.pop(sku)
            self._auto_save()
            return deleted

    def get_product(self, sku):
        """Fetches a single product by SKU."""
        with self.lock:
            if sku not in self.products:
                raise ProductNotFoundError(f"Product with SKU '{sku}' not found.")
            return self.products[sku]

    def get_stats(self):
        """Aggregates inventory summary statistics for dashboard metrics cards."""
        with self.lock:
            items = list(self.products.values())
            total_products = len(items)
            total_quantity = sum(p.quantity for p in items)
            total_valuation = round(sum(p.total_value for p in items), 2)
            low_stock = sum(1 for p in items if 0 < p.quantity < 10)
            out_of_stock = sum(1 for p in items if p.quantity == 0)
            in_stock = sum(1 for p in items if p.quantity >= 10)
            categories = sorted(list({p.category for p in items}))

            return {
                "total_products": total_products,
                "total_quantity": total_quantity,
                "total_valuation": total_valuation,
                "low_stock": low_stock,
                "out_of_stock": out_of_stock,
                "in_stock": in_stock,
                "categories": categories
            }

    def search_and_filter(self, query=None, category=None, stock_status=None, sort_by="name", order="asc"):
        """Filters, searches, and sorts inventory items."""
        with self.lock:
            results = [p.to_dict() for p in self.products.values()]

        # Search query matching SKU or Name
        if query:
            q = query.strip().lower()
            results = [p for p in results if q in p['name'].lower() or q in p['sku'].lower() or q in p['description'].lower()]

        # Category filter
        if category and category.lower() != "all":
            results = [p for p in results if p['category'].lower() == category.lower()]

        # Stock status filter
        if stock_status and stock_status.lower() != "all":
            results = [p for p in results if p['stock_status'].lower() == stock_status.lower()]

        # Sorting
        reverse = (order.lower() == "desc")
        if sort_by == "price":
            results.sort(key=lambda x: x['price'], reverse=reverse)
        elif sort_by == "quantity":
            results.sort(key=lambda x: x['quantity'], reverse=reverse)
        elif sort_by == "total_value":
            results.sort(key=lambda x: x['total_value'], reverse=reverse)
        elif sort_by == "sku":
            results.sort(key=lambda x: x['sku'], reverse=reverse)
        else: # Default sort by name
            results.sort(key=lambda x: x['name'].lower(), reverse=reverse)

        return results

    def __len__(self):
        with self.lock:
            return len(self.products)
    
    def __iter__(self):
        with self.lock:
            return iter(list(self.products.values()))


class DataHandler:
    def save_inventory(self, inventory, file_name):
        """Saves inventory items to disk JSON file."""
        data_to_save = {}
        for product in inventory:
            data_to_save[product.sku] = product.to_dict()
        
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(data_to_save, file, indent=4)

    def load_inventory(self, file_name, auto_save=True):
        """Loads inventory from JSON file and initializes Inventory instance."""
        new_inventory = Inventory(auto_save_file=file_name if auto_save else None)
        try:
            with open(file_name, 'r', encoding='utf-8') as file:
                data_loaded = json.load(file)
            
            for sku, product_data in data_loaded.items():
                prod_obj = Product.from_dict(product_data)
                # Direct assignment during boot to avoid redundant logs
                new_inventory.products[prod_obj.sku] = prod_obj
            
            print(f"Inventory loaded successfully from '{file_name}' ({len(new_inventory.products)} products).")
            return new_inventory
        except FileNotFoundError:
            print(f"File '{file_name}' not found. Initialized empty inventory.")
            return new_inventory
        except json.JSONDecodeError:
            print(f"Error decoding '{file_name}'. Starting fresh empty inventory.")
            return new_inventory
