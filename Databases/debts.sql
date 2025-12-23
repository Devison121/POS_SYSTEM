PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE debts (
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
        );
CREATE TABLE debt_payments (
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
        );
DELETE FROM sqlite_sequence;
COMMIT;
