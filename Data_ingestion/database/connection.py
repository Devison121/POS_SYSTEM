

import os
import sqlite3
from typing import Dict, Optional, Any
from dataclasses import dataclass
from utils.color_output import Colors

@dataclass
class DatabaseConfig:
    """Configuration for database connections"""
    database_path: str
    sales_db_path: str

class DatabaseManager:
    """Manages database connections and operations for the POS system"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connections: Dict[str, sqlite3.Connection] = {}
        self.setup_databases()
    
    def setup_databases(self) -> bool:
        """Setup database connections with manual transaction control"""
        try:
            inventory_db = os.path.join(self.config.database_path, 'inventory.db')
            if not os.path.exists(inventory_db):
                print(f"{Colors.RED}Error: inventory.db not found at {inventory_db}{Colors.RESET}")
                return False
                
            conn = sqlite3.connect(inventory_db)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.isolation_level = None  #  disable autocommit mode
            
            self.connections['inventory'] = conn
            
            print(f"{Colors.GREEN}✓ Database connection established (manual transaction mode){Colors.RESET}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}Error setting up database: {e}{Colors.RESET}")
            return False
        
    def check_table_exists(self, db_name: str, table_name: str) -> bool:
        """Check if a specific table exists in the database"""
        try:
            conn = self.connections[db_name]
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"{Colors.RED}Error checking table {table_name}: {e}{Colors.RESET}")
            return False
        
    # Manual transaction management
    def begin(self, db_name: str):
        """Begin transaction manually"""
        conn = self.connections[db_name]
        conn.execute("BEGIN TRANSACTION")

    def commit(self, db_name: str):
        """Commit current transaction"""
        conn = self.connections[db_name]
        conn.execute("COMMIT")

    def rollback(self, db_name: str):
        """Rollback current transaction"""
        conn = self.connections[db_name]
        conn.execute("ROLLBACK")

    # Safe query execution (no auto-commit)
    def execute_query(self, db_name: str, query: str, params: tuple = (), fetch: bool = False) -> Optional[Any]:
        """Execute SQL query safely inside manual transaction control"""
        try:
            conn = self.connections[db_name]
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch:
                return cursor.fetchall()
            else:
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            print(f"{Colors.RED}Database error in {db_name}: {e}{Colors.RESET}")
            raise
        except Exception as e:
            print(f"{Colors.RED}Unexpected error in {db_name}: {e}{Colors.RESET}")
            raise
    
    def close_all(self) -> None:
        """Close all database connections"""
        for name, conn in self.connections.items():
            conn.close()
        print(f"{Colors.GREEN}Database connections closed{Colors.RESET}")

# Note: The above code modifies the DatabaseManager to handle transactions manually.