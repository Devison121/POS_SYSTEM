# delete.py
"""
Module to handle deletion of stores, products, sales, and sellers in the POS system
"""

import sys
from pathlib import Path
import sqlite3

# Add the parent directory to path for imports
CURRENT_DIR = Path(__file__).parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

try:
    from Databases.database_connection import get_db_connection, INVENTORY_DB, SALES_DB, DEBTS_DB, OTHER_PAYMENTS_DB
    from Core_busness_logic.register_user_for_login import Colors, verify_password
except ImportError as e:
    print(f"Import error: {e}")
    # Fallback definitions
    class Colors:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        RESET = '\033[0m'
    
    def verify_password(password, hashed):
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == hashed

def delete_store(current_user):
    """Delete a store and all its related data"""
    conn_inventory = get_db_connection(INVENTORY_DB)
    conn_sales = get_db_connection(SALES_DB)
    conn_debts = get_db_connection(DEBTS_DB)
    conn_other = get_db_connection(OTHER_PAYMENTS_DB)
    
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can delete stores.{Colors.RESET}")
            return False
        
        # Get stores assigned to the user
        cursor = conn_inventory.execute("""
            SELECT s.id, s.name, s.location 
            FROM stores s 
            JOIN user_stores us ON s.id = us.store_id 
            WHERE us.user_id = ?
        """, (current_user['id'],))
        
        stores = cursor.fetchall()
        
        if not stores:
            print(f"{Colors.RED}No stores assigned to this user.{Colors.RESET}")
            return False
        
        print("\nSelect a store to delete:")
        for store in stores:
            location = store['location'] or 'No location'
            print(f"ID: {store['id']}, Name: {store['name']}, Location: {location}")
        
        try:
            store_id = int(input("Enter store ID to delete: ").strip())
            
            # Verify user has access to this store
            cursor = conn_inventory.execute("""
                SELECT s.id, s.name 
                FROM stores s 
                JOIN user_stores us ON s.id = us.store_id 
                WHERE us.user_id = ? AND s.id = ?
            """, (current_user['id'], store_id))
            
            selected_store = cursor.fetchone()
            if not selected_store:
                print(f"{Colors.RED}Invalid store ID or you do not have access to this store.{Colors.RESET}")
                return False
            
            # Password confirmation - FIXED: Use current_user['password'] instead of undefined 'password'
            user_password = input("Enter your password to confirm store deletion: ").strip()
            if not verify_password(user_password, current_user['password']):
                print(f"{Colors.RED}Incorrect password. Store deletion cancelled.{Colors.RESET}")
                return False
            
            confirm = input(f"Are you sure you want to delete store '{selected_store['name']}'? This will delete ALL related data including users, sales, debts, products, and prices. This action cannot be undone! (yes/no): ").strip().lower()
            if confirm != 'yes':
                print(f"{Colors.YELLOW}Deletion cancelled.{Colors.RESET}")
                return False
            
            print(f"{Colors.YELLOW}Starting store deletion process...{Colors.RESET}")
            
            # Begin deletion process
            # 1. Update users' current_store_id to avoid foreign key issues
            conn_inventory.execute("UPDATE users SET current_store_id = NULL, current_store_code = NULL WHERE current_store_id = ?", (store_id,))
            print(f"{Colors.BLUE}✓ Updated users' current store references{Colors.RESET}")
            
            # 2. Delete related data from all databases
            
            # Delete from other_payments database
            conn_other.execute("DELETE FROM other_payments WHERE store_id = ?", (store_id,))
            conn_other.execute("DELETE FROM business_costs WHERE store_id = ?", (store_id,))
            conn_other.execute("DELETE FROM system_costs WHERE store_id = ?", (store_id,))
            print(f"{Colors.BLUE}✓ Deleted other payments data{Colors.RESET}")
            
            # Delete from debts database
            conn_debts.execute("DELETE FROM debt_payments WHERE store_id = ?", (store_id,))
            conn_debts.execute("DELETE FROM debts WHERE store_id = ?", (store_id,))
            print(f"{Colors.BLUE}✓ Deleted debts data{Colors.RESET}")
            
            # Delete from sales database
            # First get sale IDs for this store
            cursor = conn_sales.execute("SELECT id FROM sales WHERE store_id = ?", (store_id,))
            sale_ids = [row['id'] for row in cursor.fetchall()]
            
            # Delete sale items
            if sale_ids:
                placeholders = ','.join('?' * len(sale_ids))
                conn_sales.execute(f"DELETE FROM sale_items WHERE sale_id IN ({placeholders})", sale_ids)
            
            # Delete sales
            conn_sales.execute("DELETE FROM sales WHERE store_id = ?", (store_id,))
            print(f"{Colors.BLUE}✓ Deleted sales data{Colors.RESET}")
            
            # Delete from inventory database
            # Get product IDs for this store
            cursor = conn_inventory.execute("SELECT id FROM products WHERE store_id = ?", (store_id,))
            product_ids = [row['id'] for row in cursor.fetchall()]
            
            # Delete store product prices
            conn_inventory.execute("DELETE FROM store_product_prices WHERE store_id = ?", (store_id,))
            print(f"{Colors.BLUE}✓ Deleted store product prices{Colors.RESET}")
            
            # Delete products
            if product_ids:
                placeholders = ','.join('?' * len(product_ids))
                # Delete stock batches first
                conn_inventory.execute(f"DELETE FROM stock_batches WHERE product_id IN ({placeholders})", product_ids)
                # Then delete products
                conn_inventory.execute(f"DELETE FROM products WHERE id IN ({placeholders})", product_ids)
            print(f"{Colors.BLUE}✓ Deleted products data{Colors.RESET}")
            
            # Delete user store associations
            conn_inventory.execute("DELETE FROM user_stores WHERE store_id = ?", (store_id,))
            print(f"{Colors.BLUE}✓ Deleted user store associations{Colors.RESET}")
            
            # Delete the store
            conn_inventory.execute("DELETE FROM stores WHERE id = ?", (store_id,))
            print(f"{Colors.BLUE}✓ Deleted store record{Colors.RESET}")
            
            # Commit all changes
            conn_inventory.commit()
            conn_sales.commit()
            conn_debts.commit()
            conn_other.commit()
            
            print(f"{Colors.GREEN}✓ Store '{selected_store['name']}' and all related data deleted successfully.{Colors.RESET}")
            
            # Check if current user's store was deleted
            if current_user.get('current_store_id') == store_id:
                print(f"{Colors.BLUE}The deleted store was your current store. Please switch to another store.{Colors.RESET}")
                current_user['current_store_id'] = None
                current_user['current_store_code'] = None
                return True
            
            return False
            
        except ValueError:
            print(f"{Colors.RED}Invalid input. Store ID must be a number.{Colors.RESET}")
            return False
            
    except sqlite3.Error as e:
        conn_inventory.rollback()
        conn_sales.rollback()
        conn_debts.rollback()
        conn_other.rollback()
        print(f"{Colors.RED}Error deleting store: {e}{Colors.RESET}")
        return False
    except Exception as e:
        conn_inventory.rollback()
        conn_sales.rollback()
        conn_debts.rollback()
        conn_other.rollback()
        print(f"{Colors.RED}Unexpected error: {e}{Colors.RESET}")
        return False
    finally:
        conn_inventory.close()
        conn_sales.close()
        conn_debts.close()
        conn_other.close()

def delete_data(current_user):
    """
    Main delete data function - provides menu for different deletion options
    """
    if current_user['role'] != 'boss':
        print(f"{Colors.RED}Only bosses can delete data.{Colors.RESET}")
        return
    
    while True:
        print(f"\n{Colors.BLUE}=== DELETE DATA ==={Colors.RESET}")
        print("1. Delete a Specific Sale")
        print("2. Delete a Seller")
        print("3. Delete a Product")
        print("4. Delete a Store")
        print("5. Back to Main Menu")
        
        choice = input("Choose an option: ").strip()
        
        if choice == "1":
            delete_sale(current_user)
        elif choice == "2":
            from Core_busness_logic.sellers import delete_user_by_boss
            delete_user_by_boss(current_user)
        elif choice == "3":
            delete_product(current_user)
        elif choice == "4":
            success = delete_store(current_user)
            if success:
                # If store was deleted and it was current store, return to main menu
                return
        elif choice == "5":
            print(f"{Colors.YELLOW}Returning to main menu...{Colors.RESET}")
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please try again.{Colors.RESET}")

def delete_sale(current_user):
    """Delete a specific sale"""
    conn_sales = get_db_connection(SALES_DB)
    conn_debts = get_db_connection(DEBTS_DB)
    
    try:
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        # Get recent sales for the store
        cursor = conn_sales.execute("""
            SELECT s.id, s.total_price, s.payment_method, s.created_at
            FROM sales s
            WHERE s.store_id = ?
            ORDER BY s.created_at DESC
            LIMIT 20
        """, (store_id,))
        
        sales = cursor.fetchall()
        
        if not sales:
            print(f"{Colors.RED}No sales available to delete.{Colors.RESET}")
            return
        
        print(f"\n{Colors.BLUE}Recent Sales:{Colors.RESET}")
        for sale in sales:
            print(f"ID: {sale['id']}, Amount: {sale['total_price']}, Method: {sale['payment_method']}, Date: {sale['created_at']}")
        
        try:
            sale_id = int(input("\nEnter Sale ID to delete: ").strip())
            
            # Verify sale exists and belongs to the store
            cursor = conn_sales.execute("SELECT id FROM sales WHERE id = ? AND store_id = ?", (sale_id, store_id))
            sale = cursor.fetchone()
            
            if not sale:
                print(f"{Colors.RED}Sale not found or not in your store.{Colors.RESET}")
                return
            
            confirm = input(f"Are you sure you want to delete Sale ID {sale_id}? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print(f"{Colors.YELLOW}Deletion cancelled.{Colors.RESET}")
                return
            
            # Delete associated debts first
            conn_debts.execute("DELETE FROM debts WHERE sale_id = ?", (sale_id,))
            
            # Delete sale items
            conn_sales.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
            
            # Delete sale
            conn_sales.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            
            conn_sales.commit()
            conn_debts.commit()
            
            print(f"{Colors.GREEN}✓ Sale ID {sale_id} and associated debts deleted successfully.{Colors.RESET}")
            
        except ValueError:
            print(f"{Colors.RED}Invalid input. Sale ID must be a number.{Colors.RESET}")
            
    except sqlite3.Error as e:
        conn_sales.rollback()
        conn_debts.rollback()
        print(f"{Colors.RED}Error deleting sale: {e}{Colors.RESET}")
    finally:
        conn_sales.close()
        conn_debts.close()

def delete_product(current_user):
    """Delete a product from the current store"""
    conn_inventory = get_db_connection(INVENTORY_DB)
    conn_sales = get_db_connection(SALES_DB)
    conn_debts = get_db_connection(DEBTS_DB)
    
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can delete products.{Colors.RESET}")
            return
        
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        # Get store name
        cursor = conn_inventory.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
        store = cursor.fetchone()
        
        print(f"\n{Colors.BLUE}=== DELETE PRODUCT FOR STORE: {store['name']} ==={Colors.RESET}")
        
        # Get products in the store
        cursor = conn_inventory.execute("""
            SELECT p.id, p.name, p.stock_quantity, p.expiry_date
            FROM products p
            WHERE p.store_id = ?
        """, (store_id,))
        
        products = cursor.fetchall()
        
        if not products:
            print(f"{Colors.RED}No products available to delete.{Colors.RESET}")
            return
        
        print("\nAvailable Products:")
        for product in products:
            expiry = product['expiry_date'] or 'N/A'
            print(f"ID: {product['id']}, Name: {product['name']}, Stock: {product['stock_quantity']}, Expiry: {expiry}")
        
        try:
            product_id = int(input("\nEnter Product ID to delete: ").strip())
            
            # Verify product exists in the store
            cursor = conn_inventory.execute("SELECT id, name FROM products WHERE id = ? AND store_id = ?", (product_id, store_id))
            product = cursor.fetchone()
            
            if not product:
                print(f"{Colors.RED}Product not found or not in your store.{Colors.RESET}")
                return
            
            confirm = input(f"Are you sure you want to delete product '{product['name']}'? This will also delete associated sales, debts, and pricing for this store. (yes/no): ").strip().lower()
            if confirm != 'yes':
                print(f"{Colors.YELLOW}Deletion cancelled.{Colors.RESET}")
                return
            
            # Get sale IDs that involve this product
            cursor = conn_sales.execute("""
                SELECT si.sale_id 
                FROM sale_items si 
                WHERE si.product_id = ?
            """, (product_id,))
            
            sale_ids = [row['sale_id'] for row in cursor.fetchall()]
            
            # Delete associated debts
            if sale_ids:
                placeholders = ','.join('?' * len(sale_ids))
                conn_debts.execute(f"DELETE FROM debts WHERE sale_id IN ({placeholders})", sale_ids)
            
            # Delete sale items
            conn_sales.execute("DELETE FROM sale_items WHERE product_id = ?", (product_id,))
            
            # Delete store product prices
            conn_inventory.execute("DELETE FROM store_product_prices WHERE product_id = ? AND store_id = ?", (product_id, store_id))
            
            # Delete product
            conn_inventory.execute("DELETE FROM products WHERE id = ? AND store_id = ?", (product_id, store_id))
            
            conn_inventory.commit()
            conn_sales.commit()
            conn_debts.commit()
            
            print(f"{Colors.GREEN}✓ Product '{product['name']}' and associated data deleted successfully.{Colors.RESET}")
            
        except ValueError:
            print(f"{Colors.RED}Invalid input. Product ID must be a number.{Colors.RESET}")
            
    except sqlite3.Error as e:
        conn_inventory.rollback()
        conn_sales.rollback()
        conn_debts.rollback()
        print(f"{Colors.RED}Error deleting product: {e}{Colors.RESET}")
    finally:
        conn_inventory.close()
        conn_sales.close()
        conn_debts.close()