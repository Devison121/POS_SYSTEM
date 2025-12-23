# sellers.py
"""
Module to manage sellers in the POS system, including adding, viewing, and deleting sellers.
"""

import sys
from pathlib import Path
import sqlite3
import secrets
import string
from datetime import datetime

# Add the parent directory to path for imports
CURRENT_DIR = Path(__file__).parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# Now import local modules
try:
    from Databases.database_connection import get_db_connection, INVENTORY_DB, SALES_DB, DEBTS_DB
    from Core_busness_logic.register_user_for_login import sanitize_input, validate_password, hash_password, verify_password, Colors
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback - define necessary functions locally
    import hashlib
    import re
    
    # Define Colors class locally
    class Colors:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        RESET = '\033[0m'
    
    
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(password, hashed):
        return hash_password(password) == hashed
    
    def sanitize_input(text):
        return re.sub(r'[^\w\s\-\.@]', '', text)
    
    def validate_password(password):
        if not password:
            return False, "Password cannot be empty"
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        return True, "Password is valid"

def generate_unique_username(first_name, last_name, store_id, existing_usernames):
    """Generate unique username for seller"""
    base_username = f"{first_name[0].lower()}{last_name.lower()}"
    
    username = base_username
    counter = 1
    
    # Check if username exists in the same store
    while any(uname == username and sid == store_id for uname, sid in existing_usernames):
        username = f"{base_username}{counter}"
        counter += 1
        
    return username

def add_user_by_boss(current_user):
    """
    Allow a boss to add a new seller to a store, ensuring unique usernames per store.
    """
    conn = get_db_connection(INVENTORY_DB)
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can add sellers.{Colors.RESET}")
            return
        
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        print(f"=== Add Seller to Store ID: {store_id} ===")
        first_name = sanitize_input(input("Enter first name: ").strip())
        middle_name = sanitize_input(input("Enter middle name (optional): ").strip()) or None
        last_name = sanitize_input(input("Enter last name: ").strip())
        
        if not first_name or not last_name:
            print(f"{Colors.RED}First name and last name are required.{Colors.RESET}")
            return
        
        # Get list of existing usernames and their store IDs
        cursor = conn.execute("""
            SELECT u.username, us.store_id 
            FROM users u 
            JOIN user_stores us ON u.id = us.user_id
        """)
        existing_usernames = [(row['username'], row['store_id']) for row in cursor.fetchall()]
        
        username = generate_unique_username(first_name, last_name, store_id, existing_usernames)
        
        while True:
            password = input("Enter seller password: ").strip()
            valid, message = validate_password(password)
            if not valid:
                print(f"{Colors.RED}{message} Please try again.{Colors.RESET}")
                continue
            
            # Check if username and password combination exists
            cursor = conn.execute("SELECT username, password FROM users WHERE username = ?", (username,))
            existing_user = cursor.fetchone()
            
            if existing_user and verify_password(password, existing_user['password']):
                username = generate_unique_username(first_name, last_name, store_id, existing_usernames)
                print(f"{Colors.RED}Username '{existing_user['username']}' with the same password already exists. Generated new username: '{username}'{Colors.RESET}")
                existing_usernames.append((username, store_id))
                continue
            break
        
        hashed_password = hash_password(password)
        
        # Create user
        user_data = {
            'username': username,
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'password': hashed_password,
            'role': 'seller',
            'current_store_id': store_id,
            'current_store_code': current_user['current_store_code'],
            'created_at': datetime.now().isoformat(),
            'synced': 0
        }
        
        cursor = conn.execute("""
            INSERT INTO users (username, first_name, middle_name, last_name, password, role, 
                             current_store_id, current_store_code, created_at, synced)
            VALUES (:username, :first_name, :middle_name, :last_name, :password, :role,
                   :current_store_id, :current_store_code, :created_at, :synced)
        """, user_data)
        user_id = cursor.lastrowid
        
        # Create user_store entry
        user_store_data = {
            'user_id': user_id,
            'store_id': store_id,
            'store_code': current_user['current_store_code'],
            'synced': 0
        }
        
        conn.execute("""
            INSERT INTO user_stores (user_id, store_id, store_code, synced)
            VALUES (:user_id, :store_id, :store_code, :synced)
        """, user_store_data)
        
        conn.commit()
        
        print(f"{Colors.GREEN}Seller '{first_name} {last_name}' added successfully with username '{username}'.{Colors.RESET}")
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"{Colors.RED}Error adding seller: {e}{Colors.RESET}")
    finally:
        conn.close()

def view_sellers(current_user):
    """
    Display all sellers in the current store (Username, First Name, Middle Name, Last Name, Store ID).
    Only accessible by users with BOSS role.
    """
    conn = get_db_connection(INVENTORY_DB)
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can view sellers.{Colors.RESET}")
            return
        
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        # Get store name
        cursor = conn.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
        store = cursor.fetchone()
        if not store:
            print(f"{Colors.RED}Store not found.{Colors.RESET}")
            return
        
        # Query sellers in the current store
        cursor = conn.execute("""
            SELECT u.username, u.first_name, u.middle_name, u.last_name, us.store_id
            FROM users u 
            JOIN user_stores us ON u.id = us.user_id 
            WHERE u.role = 'seller' AND us.store_id = ?
        """, (store_id,))
        
        sellers = cursor.fetchall()
        if not sellers:
            print(f"{Colors.RED}No sellers found in store '{store['name']}'.{Colors.RESET}")
            return
        
        # Display sellers in a table
        print(f"\nSellers in Store: {store['name']}")
        for seller in sellers:
            middle_name = seller['middle_name'] or ''
            print(f"Username: {seller['username']}, Name: {seller['first_name']} {middle_name} {seller['last_name']}, Store ID: {seller['store_id']}")
        
    except sqlite3.Error as e:
        print(f"{Colors.RED}Database error viewing sellers: {e}{Colors.RESET}")
    finally:
        conn.close()

def delete_user_by_boss(current_user):
    conn_inventory = get_db_connection(INVENTORY_DB)
    conn_sales = get_db_connection(SALES_DB)
    conn_debts = get_db_connection(DEBTS_DB)
    
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can delete sellers.{Colors.RESET}")
            return
        
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        # Get store name
        cursor = conn_inventory.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
        store = cursor.fetchone()
        
        print(f"\n=== Delete Seller for Store: {store['name']} ===")
        
        # Get sellers in the store
        cursor = conn_inventory.execute("""
            SELECT u.id, u.username 
            FROM users u 
            JOIN user_stores us ON u.id = us.user_id 
            WHERE us.store_id = ? AND u.role = 'seller'
        """, (store_id,))
        
        sellers = cursor.fetchall()
        if not sellers:
            print(f"{Colors.RED}No sellers available to delete.{Colors.RESET}")
            return
        
        # Display sellers
        print("\nAvailable Sellers:")
        for seller in sellers:
            print(f"ID: {seller['id']}, Username: {seller['username']}")
        
        try:
            user_id = int(input("Enter User ID to delete: ").strip())
            
            # Verify seller exists in the store
            cursor = conn_inventory.execute("""
                SELECT u.id, u.username 
                FROM users u 
                JOIN user_stores us ON u.id = us.user_id 
                WHERE u.id = ? AND us.store_id = ? AND u.role = 'seller'
            """, (user_id, store_id))
            
            user = cursor.fetchone()
            if not user:
                print(f"{Colors.RED}Seller not found or not in your store.{Colors.RESET}")
                return
            
            confirm = input(f"Are you sure you want to delete seller '{user['username']}'? This will also delete their sales and debts. (yes/no): ").strip().lower()
            if confirm != 'yes':
                print(f"{Colors.RED}Deletion cancelled.{Colors.RESET}")
                return
            
            # Delete from sales database
            conn_sales.execute("DELETE FROM sales WHERE user_id = ? AND store_id = ?", (user_id, store_id))
            
            # Delete from debts database
            conn_debts.execute("DELETE FROM debts WHERE user_id = ? AND store_id = ?", (user_id, store_id))
            
            # Delete from user_stores
            conn_inventory.execute("DELETE FROM user_stores WHERE user_id = ? AND store_id = ?", (user_id, store_id))
            
            # Delete user if they don't have other stores
            cursor = conn_inventory.execute("SELECT COUNT(*) FROM user_stores WHERE user_id = ?", (user_id,))
            remaining_stores = cursor.fetchone()[0]
            
            if remaining_stores == 0:
                conn_inventory.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            conn_inventory.commit()
            conn_sales.commit()
            conn_debts.commit()
            
            print(f"{Colors.GREEN}Seller '{user['username']}' deleted successfully.{Colors.RESET}")
            
        except ValueError:
            print(f"{Colors.RED}Invalid input. User ID must be a number.{Colors.RESET}")
            
    except sqlite3.Error as e:
        conn_inventory.rollback()
        conn_sales.rollback()
        conn_debts.rollback()
        print(f"{Colors.RED}Error deleting seller: {e}{Colors.RESET}")
    finally:
        conn_inventory.close()
        conn_sales.close()
        conn_debts.close()