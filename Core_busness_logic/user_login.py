# user_login.py
# Module to handle user login and authentication across multiple stores

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from  Databases.database_connection import get_db_connection, INVENTORY_DB, SALES_DB, DEBTS_DB, OTHER_PAYMENTS_DB 
from main import boss_menu
from business_costs_manager import business_costs_menu
from sale_products import make_sale,initialize_sales_system
import sqlite3
import getpass
from datetime import datetime

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def hash_password(password):
    """Hash password using SHA-256"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash""" 
    return hash_password(password) == hashed

def check_unsynced_data(store_id):
    """Check for unsynced data across all databases"""
    unsynced_data = {
        'sales': 0,
        'sale_items': 0,
        'debts': 0,
        'debt_payments': 0,
        'other_payments': 0
    }
    
    try:
        # Check sales and sale_items
        conn = get_db_connection(SALES_DB)
        cursor = conn.execute("SELECT COUNT(*) as count FROM sales WHERE store_id = ? AND synced = 0", (store_id,))
        unsynced_data['sales'] = cursor.fetchone()['count']
        
        cursor = conn.execute("""
            SELECT COUNT(*) as count FROM sale_items si 
            JOIN sales s ON si.sale_id = s.id 
            WHERE s.store_id = ? AND si.synced = 0
        """, (store_id,))
        unsynced_data['sale_items'] = cursor.fetchone()['count']
        conn.close()
        
        # Check debts and debt_payments
        conn = get_db_connection(DEBTS_DB)
        cursor = conn.execute("SELECT COUNT(*) as count FROM debts WHERE store_id = ? AND synced = 0", (store_id,))
        unsynced_data['debts'] = cursor.fetchone()['count']
        
        cursor = conn.execute("SELECT COUNT(*) as count FROM debt_payments WHERE store_id = ? AND synced = 0", (store_id,))
        unsynced_data['debt_payments'] = cursor.fetchone()['count']
        conn.close()
        
        # Check other_payments
        conn = get_db_connection(OTHER_PAYMENTS_DB)
        cursor = conn.execute("SELECT COUNT(*) as count FROM other_payments WHERE store_id = ? AND synced = 0", (store_id,))
        unsynced_data['other_payments'] = cursor.fetchone()['count']
        conn.close()
        
    except Exception as e:
        print(f"{Colors.RED}Error checking unsynced data: {e}{Colors.RESET}")
    
    return unsynced_data

def login():
    """
    Log in a user (Boss or Seller) and return the user object
    """
    print("=== User Login ===")
    print("Select your role:")
    print("1. Boss")
    print("2. Seller")
    role_choice = input("Choose an option (1-2): ").strip()

    role = None
    if role_choice == "1":
        role = "boss"
    elif role_choice == "2":
        role = "seller"
    else:
        print(f"{Colors.RED}Invalid role selection.{Colors.RESET}")
        return None

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ").strip()

    conn = get_db_connection(INVENTORY_DB)
    try:
        # Query for user
        cursor = conn.execute("""
            SELECT * FROM users 
            WHERE username = ? AND role = ?
        """, (username, role))
        
        user = cursor.fetchone()
        
        if not user:
            print(f"{Colors.RED}User not found or role mismatch. Please register if you are a new user.{Colors.RESET}")
            return None

        # Check password
        if not verify_password(password, user['password']):
            print(f"{Colors.RED}Incorrect password.{Colors.RESET}")
            return None

        # Query for stores associated with the user
        cursor = conn.execute("""
            SELECT s.* FROM stores s
            JOIN user_stores us ON s.id = us.store_id
            WHERE us.user_id = ?
        """, (user['id'],))
        
        stores = cursor.fetchall()
        
        if not stores:
            print(f"{Colors.RED}No stores assigned to this user. Please contact the administrator.{Colors.RESET}")
            return None

        selected_store = None
        if len(stores) > 1:
            print("Select a store:")
            for i, store in enumerate(stores, 1):
                print(f"{i}. {store['name']} - {store['location'] or 'No location'}")
            
            try:
                store_choice = int(input("Enter store number: ").strip())
                if 1 <= store_choice <= len(stores):
                    selected_store = stores[store_choice - 1]
                else:
                    print(f"{Colors.RED}Invalid store selection.{Colors.RESET}")
                    return None
            except ValueError:
                print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.RESET}")
                return None
        else:
            selected_store = stores[0]

        # Verify store password
        max_attempts = 3
        attempts = 0
        while attempts < max_attempts:
            store_password = getpass.getpass(
                f"Enter password for store '{selected_store['name']}' "
                f"(attempt {attempts + 1}/{max_attempts}): "
            ).strip()
            
            if verify_password(store_password, selected_store['password']):
                # Update user's current store
                conn.execute(
                    "UPDATE users SET current_store_id = ?, current_store_code = ? WHERE id = ?",
                    (selected_store['id'], selected_store['store_code'], user['id'])
                )
                conn.commit()
                
                full_name = f"{user['first_name']} {user['middle_name'] or ''} {user['last_name']}".strip()
                print(f"{Colors.GREEN}Welcome, {full_name} to store {selected_store['name']}{Colors.RESET}")
                
                
                # Check for unsynced data
                unsynced_data = check_unsynced_data(selected_store['id'])
                total_unsynced = (unsynced_data['sales'] + unsynced_data['sale_items'] + 
                                unsynced_data['debts'] + unsynced_data['debt_payments'] + 
                                unsynced_data['other_payments'])
                
                if total_unsynced > 0:
                    print(f"\n{Colors.YELLOW}Note: {total_unsynced} unsynced records found.{Colors.RESET}")
                    print(f"{Colors.YELLOW}Details - Sales: {unsynced_data['sales']}, Sale Items: {unsynced_data['sale_items']}, "
                          f"Debts: {unsynced_data['debts']}, Debt Payments: {unsynced_data['debt_payments']}, "
                          f"Other Payments: {unsynced_data['other_payments']}{Colors.RESET}")
                
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'role': user['role'],
                    'current_store_id': selected_store['id'],
                    'current_store_code': selected_store['store_code'],
                    'password': user['password'] 
                }
            else:
                print(f"{Colors.RED}Incorrect store password. Please try again.{Colors.RESET}")
                attempts += 1

        print(f"{Colors.RED}Too many incorrect attempts. Access denied.{Colors.RESET}")
        return None

    except Exception as e:
        print(f"{Colors.RED}Unexpected error during login: {e}{Colors.RESET}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    user = login()
    if user:
        try:
            print("Enter number 1 to access make sale flow or 2 to access boss menu and 3 for business cost menu(if boss):")
            choice = input("Choose an option (1-3): ").strip()
            if choice == "2" and user['role'] == 'boss':
                boss_menu(user)
            elif choice == "1":
               initialize_sales_system()
               if initialize_sales_system():
                   print(f"{Colors.GREEN}Sales system initialized successfully.{Colors.RESET}")
               else:
                   print(f"{Colors.RED}Failed to initialize sales system.{Colors.RESET}")
                   
               make_sale(user)
            else:
                business_costs_menu(user)
        except Exception as e:
            print(f"{Colors.RED}Error while starting sale flow: {e}{Colors.RESET}")

