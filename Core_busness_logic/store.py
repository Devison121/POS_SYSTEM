# store.py
# Module to manage store creation and switching in the POS system

import sys
from pathlib import Path

# Ensure POS_SYSTEM package root is on sys.path
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    from Databases.database_connection import get_db_connection, INVENTORY_DB
    from import_currency_symbols import get_currency_symbol
    from register_user_for_login import sanitize_input, validate_password, hash_password, verify_password, Colors, generate_store_code
except Exception:
    from POS_SYSTEM.Databases.database_connection import get_db_connection, INVENTORY_DB
    from POS_SYSTEM.Core_business_logic.register_user_for_login import sanitize_input, validate_password, hash_password, verify_password, Colors, generate_store_code

import sqlite3
from datetime import datetime

def create_store(current_user=None):
    """
    Creates a new store in the database and optionally assigns it to a user.
    """
    conn = get_db_connection(INVENTORY_DB)
    
    try:
        # Check if user has permission to create a store
        if current_user and current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can create stores.{Colors.RESET}")
            return None
        
        print("=== Create New Store ===")
        name = input("Enter store name: ").strip()
        if not name:
            print(f"{Colors.RED}Store name cannot be empty.{Colors.RESET}")
            return None
        
        # Check for existing store with the same name
        cursor = conn.execute("SELECT id FROM stores WHERE name = ?", (name,))
        if cursor.fetchone():
            print(f"{Colors.RED}Store '{name}' already exists.{Colors.RESET}")
            return None
        
        # Get store location (optional)
        location = sanitize_input(input("Enter store location (optional): ").strip()) or None
        
        # Get and validate store password
        max_attempts = 3
        attempts = 0
        store_password = None
        
        while attempts < max_attempts:
            password = input("Enter store password: ").strip()
            if not password:
                print(f"{Colors.RED}Store password cannot be empty.{Colors.RESET}")
                attempts += 1
                continue
            
            valid, message = validate_password(password)
            if not valid:
                print(f"{Colors.RED}{message} Please try again.{Colors.RESET}")
                attempts += 1
                continue
            
            confirm = input("Confirm store password: ").strip()
            if password != confirm:
                print(f"{Colors.RED}Passwords do not match. Please try again.{Colors.RESET}")
                attempts += 1
                continue
            
            store_password = password
            break
        
        if store_password is None:
            print(f"{Colors.RED}Too many incorrect attempts. Store creation cancelled.{Colors.RESET}")
            return None
        
        # Generate store code
        store_code = generate_store_code()

        country = input(f"Enter country located for store: {store_code}: ").strip()
        symbol,currency_code  = get_currency_symbol(country)
        
        # Create new store
        store_data = {
            'store_code': store_code,
            'name': name,
            'location': location,
            'business_type': 'retail',
            'owner_id': current_user['id'] if current_user else None,
            'has_boss': 1 if current_user else 0,
            'password': hash_password(store_password),
            'created_at': datetime.now().isoformat(),
            'synced': 0,
            'country': country,
            'symbol': symbol,
            'currency_code': currency_code
        }
        
        cursor = conn.execute("""
            INSERT INTO stores (store_code, name, location, business_type, owner_id, has_boss, password, created_at, synced, country, symbol, currency_code)
            VALUES (:store_code, :name, :location, :business_type, :owner_id, :has_boss, :password, :created_at, :synced, :country, :symbol, :currency_code)
        """, store_data)
        store_id = cursor.lastrowid
        
        # Assign store to current user if provided
        if current_user:
            user_store_data = {
                'user_id': current_user['id'],
                'store_id': store_id,
                'store_code': store_code,
                'synced': 0
            }
            
            conn.execute("""
                INSERT INTO user_stores (user_id, store_id, store_code, synced)
                VALUES (:user_id, :store_id, :store_code, :synced)
            """, user_store_data)
            
            # Update user's current store
            conn.execute("""
                UPDATE users SET current_store_id = ?, current_store_code = ? WHERE id = ?
            """, (store_id, store_code, current_user['id']))
            
            print(f"{Colors.GREEN}Store '{name}' created and assigned to user '{current_user['username']}'.{Colors.RESET}")
        else:
            print(f"{Colors.GREEN}Store '{name}' created successfully.{Colors.RESET}")
        
        conn.commit()
        
        return {
            'store_id': store_id,
            'store_code': store_code,
            'name': name
        }
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"{Colors.RED}Error creating store: {e}{Colors.RESET}")
        return None
    finally:
        conn.close()

def switch_store(current_user):
    """
    Switch to a different store and update both database and current_user object
    """
    conn = get_db_connection(INVENTORY_DB)
    try:
        # Query stores linked to the user via user_stores
        cursor = conn.execute("""
            SELECT s.id, s.name, s.location, s.store_code 
            FROM stores s 
            JOIN user_stores us ON s.id = us.store_id 
            WHERE us.user_id = ?
        """, (current_user['id'],))
        
        stores = cursor.fetchall()
        
        if not stores:
            print(f"{Colors.RED}You are not associated with any stores.{Colors.RESET}")
            return False, current_user
        
        print(f"\n{Colors.BLUE}=== SWITCH STORE ==={Colors.RESET}")
        print("Your Stores:")
        for i, store in enumerate(stores, 1):
            location = store['location'] or "N/A"
            print(f"{i}. {store['name']} (ID: {store['id']}) - Location: {location}")
        
        try:
            choice = input("\nEnter Store NUMBER to switch to (or 'c' to cancel): ").strip()
            if choice.lower() == 'c':
                print(f"{Colors.YELLOW}Store switch cancelled.{Colors.RESET}")
                return False, current_user
            
            choice_num = int(choice)
            if choice_num < 1 or choice_num > len(stores):
                print(f"{Colors.RED}Invalid store number. Please choose from 1 to {len(stores)}.{Colors.RESET}")
                return False, current_user
            
            selected_store = stores[choice_num - 1]
            store_id = selected_store['id']
            store_name = selected_store['name']
            store_code = selected_store['store_code']
            
            # Check if already in this store
            if current_user.get('current_store_id') == store_id:
                print(f"{Colors.YELLOW}You are already in store: {store_name}{Colors.RESET}")
                return False, current_user
            
            # Verify user has access to this store
            cursor = conn.execute("""
                SELECT s.id, s.name, s.store_code 
                FROM stores s 
                JOIN user_stores us ON s.id = us.store_id 
                WHERE us.user_id = ? AND s.id = ?
            """, (current_user['id'], store_id))
            
            store = cursor.fetchone()
            if not store:
                print(f"{Colors.RED}Store ID {store_id} not found or you are not associated with it.{Colors.RESET}")
                return False, current_user
            
            # Update user's current store in database
            conn.execute("""
                UPDATE users SET current_store_id = ?, current_store_code = ? WHERE id = ?
            """, (store_id, store_code, current_user['id']))
            
            conn.commit()
            
            # Update current_user object with new store info
            current_user['current_store_id'] = store_id
            current_user['current_store_code'] = store_code
            
            print(f"{Colors.GREEN}✓ Successfully switched to store: {store_name}{Colors.RESET}")
            print(f"{Colors.BLUE}Store ID: {store_id}, Store Code: {store_code}{Colors.RESET}")
            
            return True, current_user
            
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.RESET}")
            return False, current_user
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"{Colors.RED}Error switching store: {e}{Colors.RESET}")
        return False, current_user
    finally:
        conn.close()