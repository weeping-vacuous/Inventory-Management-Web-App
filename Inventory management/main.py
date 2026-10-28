from product import Product
from inventory_system import Inventory,DataHandler, ProductNotFoundError,InsufficientStockError
import threading

data_handler=DataHandler()
inventory=data_handler.load_inventory('inventory.json')

print(f"Welcome to the Inventory Management System")


def main():
    
    while True:

        print("\n--- Main Menu ---")
        print("1. Add/Restock Product")
        print("2. Sell Product")
        print("3. List All Products")
        print("4. Save and Exit")
        print("5. Run Stress test")
        print("---------------")

        choice=input("Enter you choice(1-4):")

        match choice:
            case "1":
                add_or_restock_product(inventory)

            case "2":
                sell_product(inventory)

            case "3":
                list_all_products(inventory)

            case "4":
                print("Saving inventory....")
                break
            case "5":
                print("Simulating sales of 100 customers for PROD-1002")
                threads=[]
                for _ in range(100):
                    thread=threading.Thread(target=simulate_sale,args=(inventory,"PROD-1002",1))
                    threads.append(thread)

                for thread in threads:
                    thread.start()
                
                for thread in threads:
                    thread.join()

                print("Simulation complete.")

            case _:
                print("Invalid choice. please slect between 1-4.")
        
    data_handler.save_inventory(inventory,'inventory.json')
    print("Invetory saved successfully. Goodbye!")

def add_or_restock_product(inventory):
    sku=input("Enter product sku:")
    if Product.is_valid_sku(sku):
        try:
            amount=int(input("Enter amount to add/restock:"))
            
            inventory.restock_product(sku,amount)
        except ProductNotFoundError as e:
            print(e)
            try:
                print("Adding new product.")
                name=input("Enter product name:")
                price=float(input("Enter product price:"))
                new_product=Product(name,sku,price,amount)
                inventory.add_product(new_product)
                print(f"Product {new_product.name} added to inventory.")
            except ValueError:
                print("Invalid price entered. Product not added.")
        except ValueError :
            print("Please enter a valid integer for amount.")
    else:
        print("Invalid SKU formnat.")
        
def sell_product(inventory):
    sku=input("Enter product to SKU to sell:")
    try:
        amount=int(input("Enter amount to sell:"))
        inventory.sell_product(sku,amount)
    except ProductNotFoundError as e:
        print(e)
    except InsufficientStockError as e:
        print(e)
    except ValueError:
        print("Invalid amount entered. please enter a valid integer")

def list_all_products(inventory):
    print("\n---Products in inventory---")
    for product in inventory:
        print(product)

def simulate_sale(inventory,sku,amount):
    try:
        inventory.sell_product(sku,amount)
    except (ProductNotFoundError,InsufficientStockError):
        pass

if __name__=="__main__":
    main()