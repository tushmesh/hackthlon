-- products.sql
-- SQL script to create the 'products' table and insert sample data.

-- Drop the table if it already exists to ensure a clean start
-- This is useful for development purposes when you might run the script multiple times.
-- In a production environment, you might want to be more careful with dropping tables.
DROP TABLE IF EXISTS products CASCADE;

-- Create the 'products' table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,           -- Unique identifier for each product, auto-increments
    item_name VARCHAR(255) NOT NULL, -- Name of the product, e.g., 'Whole Milk'
    category VARCHAR(255) NOT NULL,  -- Product category, e.g., 'Dairy', 'Bakery'
    brand VARCHAR(255),              -- Brand name, e.g., 'Fresh Farm' (can be NULL if no specific brand)
    price NUMERIC(10, 2) NOT NULL,   -- Price of the product, e.g., 4.52 (10 total digits, 2 after decimal)
    stock_quantity INTEGER NOT NULL, -- Number of units in stock, e.g., 300
    supplier VARCHAR(255)            -- Supplier of the product, e.g., 'DairyCorp'
);

-- Insert sample data into the 'products' table

INSERT INTO products (item_name, category, brand, price, stock_quantity, supplier) VALUES
('Whole Milk', 'Dairy', 'Fresh Farm', 4.52, 300, 'DairyCorp'),
('Organic Eggs', 'Dairy & Eggs', 'Green Valley', 6.10, 150, 'PoultryPros'),
('Artisan Sourdough Bread', 'Bakery', 'BakeHouse', 5.75, 50, 'FlourPower'),
('Ground Beef (Lean)', 'Meat', 'Butchers Best', 8.99, 100, 'MeatMasters'),
('Wild Salmon Fillet', 'Seafood', 'Ocean Delights', 15.20, 75, 'FishCo'),
('Fresh Broccoli', 'Vegetables', NULL, 2.99, 200, 'FarmFresh'),
('Fuji Apples', 'Fruits', NULL, 3.50, 250, 'OrchardGro'),
('Cheddar Cheese Block', 'Dairy', 'Creamy Goods', 7.80, 120, 'DairyCorp'),
('Chicken Breast (Boneless)', 'Meat', 'Poultry Perfect', 10.50, 180, 'PoultryPros'),
('Pasta Spaghetti', 'Pantry', 'Primo Pasta', 2.25, 400, 'GrainSupply'),
('Tomato Sauce', 'Pantry', 'Saucy Chef', 3.10, 350, 'SauceCo'),
('Olive Oil (Extra Virgin)', 'Pantry', 'Oliva Mia', 12.00, 90, 'OilTrade'),
('Coffee Beans (Dark Roast)', 'Beverages', 'Bean Bliss', 9.50, 80, 'RoastMasters'),
('Green Tea Bags', 'Beverages', 'Zen Tea', 4.75, 110, 'TeaTime'),
('Dish Soap', 'Household', 'Sparkle Clean', 3.00, 200, 'CleanCorp'),
('Paper Towels', 'Household', 'Absorb Pro', 6.00, 100, 'PaperWorks'),
('Laundry Detergent', 'Household', 'Fresh Scent', 15.00, 70, 'CleanCorp'),
('Shampoo', 'Health & Beauty', 'HairCare Pro', 7.50, 130, 'BeautyCo'),
('Toothpaste', 'Health & Beauty', 'Bright Smile', 4.00, 150, 'OralHealth Inc.'),
('Vitamin D Supplements', 'Health & Beauty', 'NutriMax', 18.00, 60, 'HealthSupplements'),
('Banana', 'Fruits', NULL, 0.79, 400, 'FarmFresh'),
('Greek Yogurt', 'Dairy', 'YogurtLand', 3.25, 180, 'DairyCorp'),
('Dark Chocolate Bar', 'Snacks', 'ChocoDelight', 4.00, 90, 'SweetTreats'),
('Frozen Peas', 'Frozen Foods', 'VeggieFreeze', 2.50, 250, 'FarmFrozen'),
('White Rice (Basmati)', 'Pantry', 'GrainHarvest', 6.80, 150, 'GrainSupply'),
('Orange Juice', 'Beverages', 'Citrus Fresh', 5.00, 100, 'JuicePro'),
('Cleaning Wipes', 'Household', 'CleanSweep', 4.50, 170, 'CleanCorp'),
('Moisturizer', 'Health & Beauty', 'SkinGlo', 12.00, 80, 'BeautyCo'),
('Notebook', 'Stationery', 'PaperGoods', 2.00, 300, 'OfficeSupply'),
('AAA Batteries (4-pack)', 'Electronics', 'PowerUp', 6.50, 120, 'ElectroSupply');