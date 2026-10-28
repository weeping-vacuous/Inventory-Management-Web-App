class Product:
    def __init__(self, name, sku, price, quantity, category=None, description=""):
        self.name = str(name).strip()
        self.sku = str(sku).strip().upper()
        self.price = round(float(price), 2)
        self.quantity = int(quantity)
        self.category = category.strip() if category else self.infer_category(self.name)
        self.description = description.strip() if description else f"SKU: {self.sku} - {self.name}"

    @property
    def total_value(self):
        """Calculates total monetary value of current stock for this product."""
        return round(self.price * self.quantity, 2)

    @property
    def stock_status(self):
        """Returns stock health status badge: Out of Stock, Low Stock (<10), or In Stock."""
        if self.quantity <= 0:
            return "Out of Stock"
        elif self.quantity < 10:
            return "Low Stock"
        return "In Stock"

    def __str__(self):
        return f"Product(Name: {self.name}, SKU: {self.sku}, Price: ₹{self.price:.2f}, Quantity: {self.quantity}, Category: {self.category})"
    
    def __repr__(self):
        return f"Product('{self.name}', '{self.sku}', {self.price}, {self.quantity}, '{self.category}')"
    
    def __eq__(self, other):
        if not isinstance(other, Product):
            return False
        return self.sku == other.sku
    
    def to_dict(self):
        """Serializes product object to a JSON-ready Python dictionary."""
        return {
            'name': self.name,
            'sku': self.sku,
            'price': self.price,
            'quantity': self.quantity,
            'category': self.category,
            'description': self.description,
            'total_value': self.total_value,
            'stock_status': self.stock_status
        }
    
    @staticmethod
    def infer_category(name):
        """Infers a reasonable category based on product title keywords."""
        name_lower = name.lower()
        if any(w in name_lower for w in ["laptop", "desktop", "macbook", "pc", "computer"]):
            return "Computers"
        if any(w in name_lower for w in ["phone", "iphone", "pixel", "galaxy", "smartphone"]):
            return "Mobile"
        if any(w in name_lower for w in ["monitor", "display", "screen", "4k"]):
            return "Displays"
        if any(w in name_lower for w in ["headphone", "earbud", "speaker", "audio", "mic", "microphone"]):
            return "Audio"
        if any(w in name_lower for w in ["keyboard", "mouse", "hub", "dock", "stylus", "pad", "stand", "webcam"]):
            return "Peripherals"
        if any(w in name_lower for w in ["ssd", "hdd", "drive", "card", "storage", "usb", "flash"]):
            return "Storage"
        if any(w in name_lower for w in ["cable", "charger", "adapter", "power", "battery"]):
            return "Power & Cables"
        if any(w in name_lower for w in ["watch", "band", "tracker"]):
            return "Wearables"
        return "General"

    @staticmethod
    def is_valid_sku(sku):
        """SKU must start with 'PROD-' and have an identifier suffix."""
        if not isinstance(sku, str):
            return False
        clean = sku.strip().upper()
        return clean.startswith("PROD-") and len(clean) > 5
    
    @classmethod
    def from_dict(cls, data_dict):
        """Factory method to instantiate a Product from dictionary representation."""
        name = data_dict['name']
        sku = data_dict['sku']
        price = data_dict['price']
        quantity = data_dict['quantity']
        category = data_dict.get('category')
        description = data_dict.get('description', '')
        return cls(name, sku, price, quantity, category, description)
