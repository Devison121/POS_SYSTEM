PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE business_costs (
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
        );
CREATE TABLE system_costs (
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
        );
CREATE TABLE other_payments (
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
        );
DELETE FROM sqlite_sequence;
COMMIT;
