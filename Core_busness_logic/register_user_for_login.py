# register_user_for_login.py
# Module to handle user registration and store creation for BOSS users

import sys
from pathlib import Path

# Ensure POS_SYSTEM package root is on sys.path so imports resolve whether running as a package or directly
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    # Prefer importing the local Databases package when running from the POS_SYSTEM folder
    from Databases.database_connection import get_db_connection, INVENTORY_DB, SALES_DB, DEBTS_DB, OTHER_PAYMENTS_DB
    from import_currency_symbols import get_currency_symbol
    from valid_email import get_valid_email
except Exception:
    # Fallback to absolute package import when running as an installed package or different import context
    from POS_SYSTEM.Databases.database_connection import get_db_connection, INVENTORY_DB, SALES_DB, DEBTS_DB, OTHER_PAYMENTS_DB

import sqlite3
import hashlib
import secrets  
from datetime import datetime
import os
import re
import string

# Color output for terminal messages
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

# Helper functions for user registration and validation process we use sha256 algorithm to hash passwords becouase it is more secure than md5
def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def sanitize_input(text):
    """Sanitize user input"""
    return re.sub(r'[^\w\s\-\.@]', '', text)

def validate_phone(phone):
    """Validate phone number format"""
    pattern = r'^\+?255\d{9}$|^0\d{9}$'
    return re.match(pattern, phone) is not None

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password cannot be empty"

    errors = []

    # Length
    if len(password) < 8:
        errors.append("at least 8 characters")

    # Character classes
    if not re.search(r"[A-Z]", password):
        errors.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("a lowercase letter")
    if not re.search(r"\d", password):
        errors.append("a digit")
    if not re.search(r"[!@#$%^&*()_\-+=\[\]{}|;:,.<>?/~`]", password):
        errors.append("a special character")

    # No spaces allowed
    if re.search(r"\s", password):
        errors.append("no spaces")

    # Reject very common/simple passwords
    common_passwords = {
        "password", "123456", "123456789", "qwerty", "letmein",
        "admin", "111111", "12345678", "abc123", "password1"
    }
    if password.lower() in common_passwords:
        errors.append("not a common/simple password")

    if errors:
        return False, "Password must contain: " + ", ".join(errors)
    return True, "Password is strong"

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

def generate_store_code():
    """Generate unique store code that meets requirements"""
    conn = get_db_connection(INVENTORY_DB)
    try:
        # Fetch all existing store codes from the stores table
        cursor = conn.execute("SELECT store_code FROM stores")
        existing_codes = set(row['store_code'] for row in cursor.fetchall() if row['store_code'])
        
        # Generate unique codes until we find one that doesn't exist
        max_attempts = 100
        attempts = 0
        
        while attempts < max_attempts:
            # Generate random code with 4-7 characters (mix of letters and numbers)
            code_length = secrets.choice([4, 5, 6, 7])  # Random length between 4-7
            
            # Create pool of characters: uppercase, lowercase, and digits
            characters = string.ascii_letters + string.digits  # A-Z, a-z, 0-9
            
            # Generate random code
            store_code = ''.join(secrets.choice(characters) for _ in range(code_length))
            
                    # Fetch all existing store codes from the stores table
            cursor = conn.execute("SELECT store_code FROM stores where store_code =?", (store_code,))
            existing_codes =  set(row['store_code'] for row in cursor.fetchall() if row['store_code'])

            # Ensure it's unique
            if store_code not in existing_codes:
                return store_code
            
            attempts += 1
        
        # If we can't find a unique code after many attempts, use a different approach
        # This fallback ensures we always get a unique code
        timestamp = str(int(datetime.now().timestamp()))[-4:]  # Last 4 digits of timestamp
        fallback_code = f"ST{timestamp}"
        
        # Ensure fallback is also unique
        counter = 1
        while fallback_code in existing_codes and counter < 100:
            fallback_code = f"ST{timestamp}{counter:02d}"
            counter += 1
            
        return fallback_code
    finally:
        conn.close()

# Helper function to generate unique username and it helps to avoid duplicates
def generate_username(first_name, last_name, store_id):
    """Generate unique username"""
    base_username = f"{first_name[0].lower()}{last_name.lower()}"
    
    conn = get_db_connection(INVENTORY_DB)
    try:
        # Check existing usernames
        cursor = conn.execute("SELECT username FROM users")
        existing_usernames = [row['username'] for row in cursor.fetchall()]
        
        username = base_username
        counter = 1
        
        while username in existing_usernames:
            username = f"{base_username}{counter}"
            counter += 1
            
        return username
    finally:
        conn.close()



# Main registration function only for BOSS user and other users will be added later by the BOSS
def register_user():
    """
    Register a new BOSS user and create their store
    """
    print("=== BOSS Registration ===")
    
    # Get user information
    first_name = sanitize_input(input("Enter first name: ").strip())
    middle_name = sanitize_input(input("Enter middle name (optional): ").strip()) or None
    last_name = sanitize_input(input("Enter last name: ").strip())
    whatsapp_number = input("Enter WhatsApp number (e.g., +255743114080, press Enter to skip): ").strip()
    user_email = get_valid_email()
    
    if user_email:
        print(f"\n✓ Final email saved: {user_email}")
    else:
        print("\n✓ No email saved (user skipped)")
    
    address = sanitize_input(input("Enter address (optional): ").strip()) or None
    # The store location is optional and can be set to None
    store_location = sanitize_input(input("Enter store location (optional): ").strip()) or None

    # Validate required fields
    if not (first_name and last_name):
        print(f"{Colors.RED}First name and last name are required.{Colors.RESET}")
        return None
    
    if whatsapp_number and not validate_phone(whatsapp_number):
        print(f"{Colors.RED}Invalid WhatsApp number format.{Colors.RESET}")
        return None

    # Create store
    print("Creating a new store for the boss...")
    store_name = input("Enter store name: ").strip()
    if not store_name:
        print(f"{Colors.RED}Store name cannot be empty.{Colors.RESET}")
        return None

    # Check if store already exists
    conn = get_db_connection(INVENTORY_DB)
    try:
        cursor = conn.execute("SELECT id FROM stores WHERE name = ?", (store_name,))
        if cursor.fetchone():
            print(f"{Colors.RED}Store '{store_name}' already exists.{Colors.RESET}")
            return None

        # Get and confirm store password
        max_attempts = 3
        attempts = 0
        store_password = None
        
        while attempts < max_attempts:
            spw = input("Enter store password: ").strip()
            valid, message = validate_password(spw)
            
            if not spw:
                print(f"{Colors.RED}Store password cannot be empty.{Colors.RESET}")
                attempts += 1
                continue
            
            if not valid:
                print(f"{Colors.RED}{message} Please try again.{Colors.RESET}")
                attempts += 1
                continue
            
            # Only ask for confirmation if password is valid
            spw_confirm = input("Confirm store password: ").strip()
            if spw != spw_confirm:
                print(f"{Colors.RED}Store passwords do not match. Try again.{Colors.RESET}")
                attempts += 1
                continue
            
            store_password = spw
            break
        
        if store_password is None:
            print(f"{Colors.RED}Failed to set store password. Registration cancelled.{Colors.RESET}")
            return None       

        # Generate store code
        store_code = generate_store_code()
        country = input(f"Enter country located for store: {store_code}: ").strip()

        business_types = [
            "Retail",
            "Wholesale",
            "Restaurant",
            "Pharmacy",
            "Services",
            "Manufacturing"
        ]

        while True:
            print("\nSelect your business type:")
            for i, bt in enumerate(business_types, start=1):
                print(f"{i}. {bt}")
            print(f"{len(business_types) + 1}. Other")

            choice = input(
                f"Enter a number (1 - {len(business_types) + 1}): "
            ).strip()

            # Validate numeric input
            if not choice.isdigit():
                print("Please enter a valid number.")
                continue

            choice = int(choice)

            # Known business types
            if 1 <= choice <= len(business_types):
                business_type = business_types[choice - 1]
                break

            # Other (custom business type)
            elif choice == len(business_types) + 1:
                business_type = input(
                    "Enter your business type: "
                ).strip()

                if business_type == "":
                    print(" Business type cannot be empty.")
                    continue
                break

            else:
                print(" Invalid choice. Please try again.")



        symbol,currency_code  = get_currency_symbol(country)
        # Create store
        store_data = {
            'store_code': store_code,
            'name': store_name,
            'location': store_location,
            'business_type': business_type,
            'owner_id': None,  # Will be updated after user creation
            'has_boss': 1,
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
        
        # Generate username
        username = generate_username(first_name, last_name, store_id)
        
        # Get and validate user password
        max_attempts = 3
        attempts = 0
        user_password = None
        
        while attempts < max_attempts:
            password = input("Enter user password: ").strip()
            valid, message = validate_password(password)
            
            if not password:
               print(f"{Colors.RED}User password cannot be empty.{Colors.RESET}")
               attempts += 1
               continue
            
            if not valid:
                 print(f"{Colors.RED}{message} Please try again.{Colors.RESET}")
                 attempts += 1
                 continue
            
            # Only ask for confirmation if password is valid
            password_confirm = input("Confirm user password: ").strip()
            if password != password_confirm:
                print(f"{Colors.RED}Passwords do not match. Please try again.{Colors.RESET}")
                attempts += 1
                continue
            
            user_password = password
            break

        if user_password is None:
            print(f"{Colors.RED}Failed to set user password. Registration cancelled.{Colors.RESET}")
            return None
        # Create user
        user_data = {
            'username': username,
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'password': hash_password(user_password),
            'role': 'boss',
            'email': user_email,
            'address': address,
            'created_at': datetime.now().isoformat(),
            'current_store_id': store_id,
            'current_store_code': store_code,
            'whatsapp_number': whatsapp_number or None,
            'synced': 0
        }
        
        cursor = conn.execute("""
            INSERT INTO users (username, first_name, middle_name, last_name, password, role, email, address, created_at,
                             current_store_id, current_store_code, whatsapp_number, synced)
            VALUES (:username, :first_name, :middle_name, :last_name, :password, :role, :email, :address, :created_at,
                   :current_store_id, :current_store_code, :whatsapp_number, :synced)
        """, user_data)
        user_id = cursor.lastrowid
        

        # Update store with owner_id
        conn.execute("UPDATE stores SET owner_id = ? WHERE id = ?", (user_id, store_id))
        
        # Create user_store entry
        user_store_data = {
            'user_id': user_id,
            'store_id': store_id,
            'store_code': store_code,
            'synced': 0
        }
        
        conn.execute("""
            INSERT INTO user_stores (user_id, store_id, store_code, synced)
            VALUES (:user_id, :store_id, :store_code, :synced)
        """, user_store_data)
        
        conn.commit()
        
        print(f"{Colors.GREEN}Registration successful!{Colors.RESET}")
        print(f"{Colors.GREEN}Store: {store_name} (Code: {store_code}){Colors.RESET}")
        print(f"{Colors.GREEN}Username: {username}{Colors.RESET}")
        print(f"{Colors.GREEN}Role: BOSS{Colors.RESET}")
        
        return {
            'user_id': user_id,
            'username': username,
            'store_id': store_id,
            'store_code': store_code
        }
        
    except Exception as e:
        conn.rollback()
        print(f"{Colors.RED}Registration failed: {e}{Colors.RESET}")
        return None
    finally:
        conn.close()

if __name__ == "__main__":
    register_user()