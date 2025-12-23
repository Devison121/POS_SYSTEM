# database_setup.py
# Module to create all database tables
import sqlite3
from database_connection import get_db_connection, INVENTORY_DB, SALES_DB, DEBTS_DB, OTHER_PAYMENTS_DB

def create_inventory_tables():
    """Create all tables for inventory database"""
    conn = get_db_connection(INVENTORY_DB)
    cursor = conn.cursor()
    
    try:
        # Create stores table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            location TEXT,
            business_type TEXT NOT NULL DEFAULT 'retail',
            owner_id INTEGER,
            synced BOOLEAN DEFAULT 0,
            has_boss BOOLEAN DEFAULT 0 NOT NULL,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            country TEXT,
            currency_code TEXT,
            symbol TEXT,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
        ''')
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            middle_name TEXT,
            last_name TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            role_description TEXT,
            email TEXT UNIQUE,
            address TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            current_store_id INTEGER,
            current_store_code TEXT,
            whatsapp_number TEXT,
            synced BOOLEAN DEFAULT 0,
            salary_amount REAL DEFAULT 0,
            salary_frequency TEXT CHECK(salary_frequency IN ('daily', 'weekly', 'monthly')) DEFAULT 'monthly',
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (current_store_id) REFERENCES stores(id),
            FOREIGN KEY (current_store_code) REFERENCES stores(store_code)
        )
        ''')
        # Create user_stores table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
            FOREIGN KEY (store_code) REFERENCES stores(store_code),
            UNIQUE(user_id, store_id)
        )
        ''')
        
        # Create products table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            sequence_number INTEGER NOT NULL,
            image TEXT,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            parent_product_id INTEGER,
            relation_to_parent INTEGER,
            low_stock_threshold INTEGER DEFAULT 5,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            synced BOOLEAN DEFAULT 0,
            unit TEXT DEFAULT 'unit',
            big_unit TEXT DEFAULT 'unit',
            expiry_date TEXT,
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (parent_product_id) REFERENCES products(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code),
            UNIQUE(name, store_id),
            UNIQUE(store_code, sequence_number)
        )
        ''')
        
        # Create store_product_prices table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS store_product_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            retail_price REAL NOT NULL,
            wholesale_price REAL NOT NULL,
            wholesale_threshold INTEGER NOT NULL,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (product_code) REFERENCES products(product_code),
            UNIQUE(store_id, product_id)
        )
        ''')
        
        # Create stock_batches table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            batch_number TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            buying_price REAL NOT NULL,
            shipping_cost REAL DEFAULT 0,
            handling_cost REAL DEFAULT 0,
            landed_cost REAL GENERATED ALWAYS AS (buying_price + shipping_cost + handling_cost) VIRTUAL,
            received_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            expiry_date DATETIME,
            is_active BOOLEAN DEFAULT 1,
            synced BOOLEAN DEFAULT 0,
            expected_margin REAL DEFAULT 0,
            actual_margin REAL DEFAULT 0,
            total_expected_profit REAL DEFAULT 0,
            total_actual_profit REAL DEFAULT 0,
            original_quantity INTEGER,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (product_code) REFERENCES products(product_code),
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code)
        )
        ''')
        
        # Create user_commissions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            commission_rate REAL NOT NULL DEFAULT 0.0,
            commission_frequency TEXT CHECK(commission_frequency IN ('one_time', 'daily', 'weekly', 'monthly', 'yearly')) DEFAULT 'monthly',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expiry_date DATETIME,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        conn.commit()
        print("Inventory database tables created successfully!")
        
    except sqlite3.Error as e:
        print(f"Error creating inventory tables: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_sales_tables():
    """Create all tables for sales database"""
    conn = get_db_connection(SALES_DB)
    cursor = conn.cursor()
    
    try:
        # Create sales table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            total_price REAL NOT NULL,
            payment_method TEXT NOT NULL CHECK (payment_method IN ('CASH', 'MPESA', 'BANK', 'DEBT', 'OTHER')),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            synced BOOLEAN DEFAULT 0 NOT NULL,
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Create sale_items table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            is_wholesale BOOLEAN NOT NULL DEFAULT 0,
            synced BOOLEAN DEFAULT 0 NOT NULL,
            cost_price REAL,
            profit REAL GENERATED ALWAYS AS (unit_price - cost_price) VIRTUAL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (product_code) REFERENCES products(product_code)
        )
        ''')
        
        # Create sale_batch_allocations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_batch_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            batch_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            allocated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (batch_id) REFERENCES stock_batches(id)
        )
        ''')
        
        conn.commit()
        print("Sales database tables created successfully!")
        
    except sqlite3.Error as e:
        print(f"Error creating sales tables: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_debts_tables():
    """Create all tables for debts database"""
    conn = get_db_connection(DEBTS_DB)
    cursor = conn.cursor()
    
    try:
        # Create debts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            debtor_name TEXT NOT NULL,
            debtor_phone TEXT NOT NULL,
            amount_owed REAL NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Create debt_payments table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS debt_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            synced BOOLEAN DEFAULT 0 NOT NULL,
            FOREIGN KEY (debt_id) REFERENCES debts(id),
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        conn.commit()
        print("Debts database tables created successfully!")
        
    except sqlite3.Error as e:
        print(f"Error creating debts tables: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_other_payments_tables():
    """Create all tables for other payments database"""
    conn = get_db_connection(OTHER_PAYMENTS_DB)
    cursor = conn.cursor()
    
    try:
        # Create business_costs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS business_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            cost_category TEXT NOT NULL CHECK(cost_category IN (
                'rent', 'electricity', 'loan_interest', 'storage', 
                'marketing', 'insurance', 'other'
            )),
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            cost_date DATE NOT NULL,
            frequency TEXT CHECK(frequency IN ('one_time', 'daily', 'weekly', 'monthly', 'yearly')) DEFAULT 'monthly',
            recurring_end_date DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code)
        )
        ''')
        
        # Create system_costs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            cost_type TEXT NOT NULL CHECK(cost_type IN ('pos_license', 'software_fee', 'maintenance', 'internet', 'other')),
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            frequency TEXT CHECK(frequency IN ('daily', 'weekly', 'monthly', 'yearly', 'one_time')) DEFAULT 'monthly',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code)
        )
        ''')
        
        # Create other_payments table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS other_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            synced BOOLEAN DEFAULT 0,
            payment_type TEXT DEFAULT "",
            amount REAL NOT NULL,
            payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            recipient TEXT,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code)
        )
        ''')
        
        conn.commit()
        print("Other payments database tables created successfully!")
        
    except sqlite3.Error as e:
        print(f"Error creating other payments tables: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_all_tables():
    """Create all tables in all databases"""
    print("Starting database setup...")
    
    create_inventory_tables()
    create_sales_tables()
    create_debts_tables()
    create_other_payments_tables()
    
    print("All database tables created successfully!")


if __name__ == "__main__":
    # Create all tables
    create_all_tables()
    
    print("Database setup completed!")