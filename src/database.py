# src/database.py
import psycopg2
from psycopg2 import Error
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_product_data(query: str = None, category: str = None, brand: str = None):
    """
    Retrieves product information from the database based on query, category, or brand.
    If no specific filter is provided, it fetches a limited number of products.
    """
    conn = get_db_connection()
    if not conn:
        return []
    
    products = []
    try:
        cursor = conn.cursor()
        sql_query = "SELECT id, item_name, category, brand, price, stock_quantity, supplier FROM products"
        params = []
        conditions = []

        if query:
            conditions.append("(item_name ILIKE %s OR category ILIKE %s OR brand ILIKE %s)")
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
        if category:
            conditions.append("category ILIKE %s")
            params.append(f"%{category}%")
        if brand:
            conditions.append("brand ILIKE %s")
            params.append(f"%{brand}%")

        if conditions:
            sql_query += " WHERE " + " AND ".join(conditions)
        
        sql_query += " LIMIT 20;" # Limit results for brevity and performance

        cursor.execute(sql_query, tuple(params))
        
        for row in cursor.fetchall():
            products.append({
                "ID": row[0],
                "Item Name": row[1],
                "Category": row[2],
                "Brand": row[3],
                "Price": row[4],
                "Stock Quantity": row[5],
                "Supplier": row[6]
            })
    except Error as e:
        print(f"Error executing query: {e}")
    finally:
        if conn:
            conn.close()
    return products

def update_product_stock(product_id: int, new_quantity: int):
    """Updates the stock quantity for a given product ID."""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET stock_quantity = %s WHERE id = %s;", (new_quantity, product_id))
        conn.commit()
        return True
    except Error as e:
        print(f"Error updating stock: {e}")
        conn.rollback() # Rollback in case of error
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("--- Sample Product Data Retrieval ---")
    all_products = get_product_data()
    print(f"First 5 products: {all_products[:5]}")

    print("\n--- Searching for 'Milk' ---")
    milk_products = get_product_data(query="Milk")
    print(milk_products)

    print("\n--- Searching for Dairy category ---")
    dairy_products = get_product_data(category="Dairy")
    print(dairy_products)

    print("\n--- Updating stock for Product ID 1 (Whole Milk) ---")
    initial_stock = get_product_data(query="Whole Milk")[0]['Stock Quantity'] if get_product_data(query="Whole Milk") else None
    print(f"Initial stock for Whole Milk (ID 1): {initial_stock}")
    if update_product_stock(1, 290):
        print("Stock updated successfully.")
        updated_stock = get_product_data(query="Whole Milk")[0]['Stock Quantity'] if get_product_data(query="Whole Milk") else None
        print(f"Updated stock for Whole Milk (ID 1): {updated_stock}")
    else:
        print("Failed to update stock.")

    # Revert stock for demo purposes
    if update_product_stock(1, initial_stock):
         print("Stock reverted successfully for demo.")