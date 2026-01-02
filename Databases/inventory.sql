PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE stores (
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
        );
CREATE TABLE users (
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
        );
CREATE TABLE user_stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
            FOREIGN KEY (store_code) REFERENCES stores(store_code),
            UNIQUE(user_id, store_id)
        );
CREATE TABLE products (
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
        );
CREATE TABLE store_product_prices (
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
        );
CREATE TABLE stock_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            store_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            batch_number TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            sold_wholesale_qty INTEGER DEFAULT 0, -- For expected margin calculations based on sales type
            sold_retail_qty INTEGER DEFAULT 0,  -- For expected margin calculations based on sales type
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
        );
CREATE TABLE user_commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            store_code TEXT NOT NULL,
            commission_amount REAL NOT NULL DEFAULT 0.0,
            commission_frequency TEXT CHECK(commission_frequency IN ('one_time', 'daily', 'weekly', 'monthly', 'yearly')) DEFAULT 'monthly',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expiry_date DATETIME,
            is_active INTEGER NOT NULL DEFAULT 1,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code)
        );
DELETE FROM sqlite_sequence;
COMMIT;
