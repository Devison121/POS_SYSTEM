PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    store_code TEXT NOT NULL,  -- STORE_ID
    user_id INTEGER NOT NULL,
    total_price REAL NOT NULL,
    payment_method TEXT NOT NULL CHECK (payment_method IN ('CASH', 'MPESA', 'BANK', 'DEBT', 'OTHER')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0 NOT NULL,
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (store_code) REFERENCES stores(store_code),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE TABLE sale_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,  -- PRODUCT_ID
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    is_wholesale BOOLEAN NOT NULL DEFAULT 0,
    synced BOOLEAN DEFAULT 0 NOT NULL, cost_price REAL, profit REAL GENERATED ALWAYS AS (unit_price - cost_price) VIRTUAL,
    FOREIGN KEY (sale_id) REFERENCES sales(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (product_code) REFERENCES products(product_code)
);
CREATE TABLE sale_batch_allocations (
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
            );
DELETE FROM sqlite_sequence;
COMMIT;
