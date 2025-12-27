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
INSERT INTO stores VALUES(1,'2rwkF','Davo store','Gujarati','both retail and wholesale',1,0,1,'e41269450870c97e274bd36458bd294c7127d7a0fbb08a2b10de2243dd0341e4','2025-12-27T11:02:19.430548','india','INR','₹');
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
INSERT INTO users VALUES(1,'dphilipo','devison','mhepela','philipo','e41269450870c97e274bd36458bd294c7127d7a0fbb08a2b10de2243dd0341e4','boss',NULL,'devisonmhepela07@gmail.com','61 golden vally amoda gujarati vadodara india','2025-12-27T11:02:32.458927',1,'2rwkF',NULL,0,0.0,'monthly',1);
INSERT INTO users VALUES(2,'dmhepela','devison','philipo','mhepela','e41269450870c97e274bd36458bd294c7127d7a0fbb08a2b10de2243dd0341e4','seller','Davo seller','devison07@gmail.com','61 gujarati vadodara india','2025-12-27T11:11:33.037150',1,'2rwkF','0766878300',0,50000.0,'monthly',1);
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
INSERT INTO user_stores VALUES(1,1,1,'2rwkF',0);
INSERT INTO user_stores VALUES(2,2,1,'2rwkF',0);
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
            commission_rate REAL NOT NULL DEFAULT 0.0,
            commission_frequency TEXT CHECK(commission_frequency IN ('one_time', 'daily', 'weekly', 'monthly', 'yearly')) DEFAULT 'monthly',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expiry_date DATETIME,
            is_active INTEGER NOT NULL DEFAULT 1,
            synced BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (store_code) REFERENCES stores(store_code)
        );
INSERT INTO user_commissions VALUES(1,2,'2rwkF',0.5,'weekly','2025-12-27 05:41:33','2026-01-03T11:11:33.037083',1,0);
DELETE FROM sqlite_sequence;
INSERT INTO sqlite_sequence VALUES('stores',1);
INSERT INTO sqlite_sequence VALUES('users',2);
INSERT INTO sqlite_sequence VALUES('user_stores',2);
INSERT INTO sqlite_sequence VALUES('user_commissions',1);
COMMIT;
