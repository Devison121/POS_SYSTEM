PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE store_product_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,  -- PRODUCT_ID
    retail_price REAL NOT NULL,
    wholesale_price REAL NOT NULL,
    wholesale_threshold INTEGER NOT NULL,
    synced BOOLEAN DEFAULT 0,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (product_code) REFERENCES products(product_code),
    UNIQUE(store_id, product_id)
);
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    last_name TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('boss', 'seller')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    current_store_id INTEGER,
    current_store_code TEXT,  -- STORE_ID ya duka la sasa
    whatsapp_number TEXT,
    synced BOOLEAN DEFAULT 0, salary_amount REAL DEFAULT 0, salary_frequency TEXT CHECK(salary_frequency IN ('daily', 'weekly', 'monthly')) DEFAULT 'monthly', commission_rate REAL DEFAULT 0, is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (current_store_id) REFERENCES stores(id),
    FOREIGN KEY (current_store_code) REFERENCES stores(store_code)
);
CREATE TABLE user_stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    store_code TEXT NOT NULL,  -- STORE_ID
    synced BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
    FOREIGN KEY (store_code) REFERENCES stores(store_code),
    UNIQUE(user_id, store_id)
);
CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_code TEXT UNIQUE NOT NULL,  -- STORE_ID ya kipekee (4-7 characters)
    name TEXT NOT NULL,
    location TEXT,
    business_type TEXT NOT NULL DEFAULT 'retail',
    owner_id INTEGER,
    synced BOOLEAN DEFAULT 0,
    has_boss BOOLEAN DEFAULT 0 NOT NULL,
    password TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, country text, currency_code, symbol,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE NOT NULL,            -- PRODUCT_ID (store_code_sequence)
    name TEXT NOT NULL,
    store_id INTEGER NOT NULL,
    store_code TEXT NOT NULL,                     -- STORE_ID
    sequence_number INTEGER NOT NULL,             -- PRODUCT_SEQUENCE_NUMBER
    image TEXT,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    parent_product_id INTEGER,
    relation_to_parent INTEGER,
    low_stock_threshold INTEGER DEFAULT 5,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0, unit TEXT DEFAULT 'unit', big_unit TEXT DEFAULT 'unit', expiry_date TEXT,

    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (parent_product_id) REFERENCES products(id),
    FOREIGN KEY (store_code) REFERENCES stores(store_code),

    UNIQUE(name, store_id),
    UNIQUE(store_code, sequence_number)           -- Uhakikisha sequence ni unique kwa kila duka
);
CREATE TABLE stock_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,
    store_id INTEGER NOT NULL, 
    store_code TEXT NOT NULL,  
    batch_number TEXT NOT NULL, 
    quantity INTEGER NOT NULL,
    buying_price REAL NOT NULL, 
    shipping_cost REAL DEFAULT 0, 
    landed_cost REAL GENERATED ALWAYS AS (buying_price + shipping_cost + handling_cost) VIRTUAL, 
    received_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    expiry_date DATETIME,
    is_active BOOLEAN DEFAULT 1,
    synced BOOLEAN DEFAULT 0, handling_cost REAL DEFAULT 0, expected_margin REAL DEFAULT 0, actual_margin REAL DEFAULT 0, total_expected_profit REAL DEFAULT 0, total_actual_profit REAL DEFAULT 0, original_quantity INTEGER,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (product_code) REFERENCES products(product_code),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (store_code) REFERENCES stores(store_code)
);
DELETE FROM sqlite_sequence;
COMMIT;
