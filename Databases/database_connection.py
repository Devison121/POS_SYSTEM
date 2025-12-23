# database_connection.py 
# Module to handle database connections and paths
import sqlite3
import os

# Define database file paths 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database file paths 
INVENTORY_DB = os.path.join(BASE_DIR, "inventory.db") # Path to inventory database
SALES_DB = os.path.join(BASE_DIR, "sales.db")# Path to sales database
DEBTS_DB = os.path.join(BASE_DIR, "debts.db")# Path to debts database
OTHER_PAYMENTS_DB = os.path.join(BASE_DIR, "other_payments.db")# Path to other payments database

# Function to get a database connection
def get_db_connection(db_path):
    db_dir = os.path.dirname(db_path) # Ensure the database directory exists
    # Create directory if it doesn't exist then connect to the database 
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)# Connect to the specified database file
    conn.row_factory = sqlite3.Row # Enable dictionary-like row access
    return conn # Return the database connection