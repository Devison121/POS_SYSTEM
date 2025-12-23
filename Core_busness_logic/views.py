import sys
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta

# Add the parent directory to path for imports
CURRENT_DIR = Path(__file__).parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

try:
    from Databases.database_connection import get_db_connection, INVENTORY_DB, SALES_DB, DEBTS_DB
    from Core_busness_logic.register_user_for_login import Colors
except ImportError as e:
    print(f"Import error: {e}")
    class Colors:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        RESET = '\033[0m'

def view_stock(current_user):
    """View stock for current store or all stores"""
    conn = get_db_connection(INVENTORY_DB)
    
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can view stock.{Colors.RESET}")
            return
        
        print("\n=== View Stock ===")
        print("1. Current Store")
        print("2. All Stores")
        
        choice = input("Choose an option (1-2): ").strip()
        
        if choice == "1":
            store_id = current_user['current_store_id']
            if not store_id:
                print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
                return
            
            # Get store name
            cursor = conn.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
            store = cursor.fetchone()
            
            print(f"\n=== Stock for Store: {store['name']} ===")
            
            # Get products with their prices
            cursor = conn.execute("""
                SELECT p.id, p.name, p.stock_quantity, p.low_stock_threshold, p.expiry_date,
                       spp.retail_price, spp.wholesale_price, spp.wholesale_threshold
                FROM products p
                JOIN store_product_prices spp ON p.id = spp.product_id
                WHERE p.store_id = ? AND spp.store_id = ?
            """, (store_id, store_id))
            
            products = cursor.fetchall()
            
            if not products:
                print("No products available in this store.")
                return
            
            # Display products
            print("\nStock:")
            for product in products:
                expiry = product['expiry_date'] or 'N/A'
                print(f"ID: {product['id']}, Name: {product['name']}, Retail: {product['retail_price']}, "
                      f"Wholesale: {product['wholesale_price']}, Threshold: {product['wholesale_threshold']}, "
                      f"Stock: {product['stock_quantity']}, Low Threshold: {product['low_stock_threshold']}, "
                      f"Expiry: {expiry}")
            
            # Check for low stock
            low_stock = [p for p in products if p['stock_quantity'] < p['low_stock_threshold']]
            if low_stock:
                print(f"\n{Colors.RED}Warning: The following products are below their low stock threshold:{Colors.RESET}")
                for product in low_stock:
                    print(f"- {product['name']}: {product['stock_quantity']} units (threshold: {product['low_stock_threshold']})")
        
        elif choice == "2":
            # Get all stores for the user
            cursor = conn.execute("""
                SELECT s.id, s.name 
                FROM stores s 
                JOIN user_stores us ON s.id = us.store_id 
                WHERE us.user_id = ?
            """, (current_user['id'],))
            
            stores = cursor.fetchall()
            
            if not stores:
                print("No stores assigned to this user.")
                return
            
            for store in stores:
                print(f"\n=== Stock for Store: {store['name']} ===")
                
                cursor = conn.execute("""
                    SELECT p.id, p.name, p.stock_quantity, p.low_stock_threshold, p.expiry_date,
                           spp.retail_price, spp.wholesale_price, spp.wholesale_threshold
                    FROM products p
                    JOIN store_product_prices spp ON p.id = spp.product_id
                    WHERE p.store_id = ? AND spp.store_id = ?
                """, (store['id'], store['id']))
                
                products = cursor.fetchall()
                
                if not products:
                    print("No products available in this store.")
                    continue
                
                # Display products
                print("\nStock:")
                for product in products:
                    expiry = product['expiry_date'] or 'N/A'
                    print(f"ID: {product['id']}, Name: {product['name']}, Retail: {product['retail_price']}, "
                          f"Wholesale: {product['wholesale_price']}, Threshold: {product['wholesale_threshold']}, "
                          f"Stock: {product['stock_quantity']}, Low Threshold: {product['low_stock_threshold']}, "
                          f"Expiry: {expiry}")
                
                # Check for low stock
                low_stock = [p for p in products if p['stock_quantity'] < p['low_stock_threshold']]
                if low_stock:
                    print(f"\n{Colors.RED}Warning: The following products are below their low stock threshold:{Colors.RESET}")
                    for product in low_stock:
                        print(f"- {product['name']}: {product['stock_quantity']} units (threshold: {product['low_stock_threshold']})")
        
        else:
            print("Invalid choice.")
            
    except sqlite3.Error as e:
        print(f"{Colors.RED}Error viewing stock: {e}{Colors.RESET}")
    finally:
        conn.close()

def view_sales(current_user):
    """Display today's sales for the current store"""
    conn_sales = get_db_connection(SALES_DB)
    conn_inventory = get_db_connection(INVENTORY_DB)
    
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can view sales.{Colors.RESET}")
            return
        
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        # Get store name
        cursor = conn_inventory.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
        store = cursor.fetchone()
        if not store:
            print(f"{Colors.RED}Store not found.{Colors.RESET}")
            return
        
        print(f"\n=== Today's Sales for Store: {store['name']} ===")
        
        today = datetime.now().date()
        
        # Query today's sales
        cursor = conn_sales.execute("""
            SELECT s.id, s.total_price, s.payment_method, s.created_at, s.user_id
            FROM sales s
            WHERE s.store_id = ? AND DATE(s.created_at) = ?
            ORDER BY s.created_at DESC
        """, (store_id, today.isoformat()))
        
        sales = cursor.fetchall()
        
        if not sales:
            print(f"{Colors.RED}No sales recorded for today.{Colors.RESET}")
            return
        
        # Get user names from inventory database
        user_ids = [sale['user_id'] for sale in sales]
        user_names = {}
        if user_ids:
            placeholders = ','.join('?' * len(user_ids))
            cursor = conn_inventory.execute(f"SELECT id, username FROM users WHERE id IN ({placeholders})", user_ids)
            for user in cursor.fetchall():
                user_names[user['id']] = user['username']
        
        total_amount = sum(sale['total_price'] for sale in sales)
        
        print(f"\nToday's Sales for Store: {store['name']}")
        for sale in sales:
            seller_name = user_names.get(sale['user_id'], 'Unknown')
            print(f"ID: {sale['id']}, Seller: {seller_name}, "
                  f"Amount: {sale['total_price']}, Method: {sale['payment_method']}, "
                  f"Date: {sale['created_at']}")
        
        print(f"\nTotal Amount Sold: {total_amount}")
        
        # Payment method summary
        payment_summary = {}
        for sale in sales:
            method = sale['payment_method']
            if method not in payment_summary:
                payment_summary[method] = {'count': 0, 'amount': 0}
            payment_summary[method]['count'] += 1
            payment_summary[method]['amount'] += sale['total_price']
        
        if payment_summary:
            print("\nSummary by Payment Method:")
            for method, data in payment_summary.items():
                print(f"{method}: {data['count']} sales, Total: {data['amount']}")
        
    except sqlite3.Error as e:
        print(f"{Colors.RED}Error viewing sales: {e}{Colors.RESET}")
    finally:
        conn_sales.close()
        conn_inventory.close()

def view_tables(current_user):
    """View all tables for the current store"""
    conn_inventory = get_db_connection(INVENTORY_DB)
    conn_sales = get_db_connection(SALES_DB)
    conn_debts = get_db_connection(DEBTS_DB)
    
    try:
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        # Get store name
        cursor = conn_inventory.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
        store = cursor.fetchone()
        
        print(f"\n=== All Tables for Store: {store['name']} ===")
        
        # Products table
        print("\nProducts Table:")
        cursor = conn_inventory.execute("""
            SELECT p.id, p.name, p.stock_quantity, p.expiry_date,
                   spp.retail_price, spp.wholesale_price, spp.wholesale_threshold
            FROM products p
            JOIN store_product_prices spp ON p.id = spp.product_id
            WHERE p.store_id = ? AND spp.store_id = ?
        """, (store_id, store_id))
        
        products = cursor.fetchall()
        if products:
            for product in products:
                expiry = product['expiry_date'] or 'N/A'
                print(f"ID: {product['id']}, Name: {product['name']}, Retail: {product['retail_price']}, "
                      f"Wholesale: {product['wholesale_price']}, Threshold: {product['wholesale_threshold']}, "
                      f"Stock: {product['stock_quantity']}, Expiry: {expiry}")
        else:
            print("No products available.")
        
        # Sales table
        print("\nSales Table:")
        cursor = conn_sales.execute("""
            SELECT s.id, s.total_price, s.payment_method, s.created_at, s.user_id
            FROM sales s
            WHERE s.store_id = ?
            ORDER BY s.created_at DESC
            LIMIT 20
        """, (store_id,))
        
        sales = cursor.fetchall()
        if sales:
            # Get user names
            user_ids = [sale['user_id'] for sale in sales]
            user_names = {}
            if user_ids:
                placeholders = ','.join('?' * len(user_ids))
                cursor = conn_inventory.execute(f"SELECT id, username FROM users WHERE id IN ({placeholders})", user_ids)
                for user in cursor.fetchall():
                    user_names[user['id']] = user['username']
            
            for sale in sales:
                seller_name = user_names.get(sale['user_id'], 'Unknown')
                print(f"ID: {sale['id']}, Seller: {seller_name}, "
                      f"Amount: {sale['total_price']}, Method: {sale['payment_method']}, "
                      f"Date: {sale['created_at']}")
        else:
            print("No sales recorded.")
        
        # Debts table
        print("\nDebts Table:")
        cursor = conn_debts.execute("""
            SELECT d.id, d.sale_id, d.debtor_name, d.debtor_phone, d.amount_owed, d.created_at
            FROM debts d
            WHERE d.store_id = ?
            ORDER BY d.created_at DESC
            LIMIT 20
        """, (store_id,))
        
        debts = cursor.fetchall()
        if debts:
            for debt in debts:
                print(f"ID: {debt['id']}, Sale ID: {debt['sale_id']}, Debtor: {debt['debtor_name']}, "
                      f"Phone: {debt['debtor_phone']}, Amount: {debt['amount_owed']}, Date: {debt['created_at']}")
        else:
            print("No debts recorded.")
            
    except sqlite3.Error as e:
        print(f"{Colors.RED}Error viewing tables: {e}{Colors.RESET}")
    finally:
        conn_inventory.close()
        conn_sales.close()
        conn_debts.close()

def view_reports(current_user):
    """View various reports for the store"""
    if current_user['role'] != 'boss':
        print(f"{Colors.RED}Only bosses can view reports.{Colors.RESET}")
        return
    
    conn_inventory = get_db_connection(INVENTORY_DB)
    conn_sales = get_db_connection(SALES_DB)
    
    try:
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        # Get store name
        cursor = conn_inventory.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
        store = cursor.fetchone()
        
        print(f"\n=== Reports for Store: {store['name']} ===")
        print("1. Best-Selling Products")
        print("2. Total Revenue")
        print("3. Sales by Seller")
        print("4. List All Users")
        print("5. Expired Stock")
        print("6. Back to Main Menu")
        
        choice = input("Choose an option: ").strip()
        
        if choice == "1":
            # Best-selling products
            cursor = conn_sales.execute("""
                SELECT si.product_id, SUM(si.quantity) as total_quantity, 
                       SUM(si.quantity * si.unit_price) as total_revenue
                FROM sale_items si
                JOIN sales s ON si.sale_id = s.id
                WHERE s.store_id = ?
                GROUP BY si.product_id
                ORDER BY total_quantity DESC
                LIMIT 10
            """, (store_id,))
            
            product_sales = cursor.fetchall()
            if not product_sales:
                print("No sales recorded.")
                return
            
            # Get product names from inventory
            product_ids = [ps['product_id'] for ps in product_sales]
            product_names = {}
            if product_ids:
                placeholders = ','.join('?' * len(product_ids))
                cursor = conn_inventory.execute(f"SELECT id, name FROM products WHERE id IN ({placeholders})", product_ids)
                for product in cursor.fetchall():
                    product_names[product['id']] = product['name']
            
            print("\nBest-Selling Products:")
            for ps in product_sales:
                product_name = product_names.get(ps['product_id'], 'Unknown Product')
                print(f"Product: {product_name}, Quantity Sold: {ps['total_quantity']}, Revenue: {ps['total_revenue']}")
        
        elif choice == "2":
            # Total revenue
            cursor = conn_sales.execute("""
                SELECT SUM(total_price) as total_revenue
                FROM sales
                WHERE store_id = ?
            """, (store_id,))
            
            result = cursor.fetchone()
            total_revenue = result['total_revenue'] or 0
            
            print(f"\nTotal Revenue: {total_revenue}")
        
        elif choice == "3":
            # Sales by seller
            cursor = conn_sales.execute("""
                SELECT user_id, COUNT(id) as sale_count, 
                       SUM(total_price) as total_revenue
                FROM sales
                WHERE store_id = ?
                GROUP BY user_id
                ORDER BY total_revenue DESC
            """, (store_id,))
            
            seller_sales = cursor.fetchall()
            if not seller_sales:
                print("No sales recorded.")
                return
            
            # Get user names from inventory
            user_ids = [ss['user_id'] for ss in seller_sales]
            user_names = {}
            if user_ids:
                placeholders = ','.join('?' * len(user_ids))
                cursor = conn_inventory.execute(f"SELECT id, username FROM users WHERE id IN ({placeholders})", user_ids)
                for user in cursor.fetchall():
                    user_names[user['id']] = user['username']
            
            print("\nSales by Seller:")
            for ss in seller_sales:
                seller_name = user_names.get(ss['user_id'], 'Unknown Seller')
                print(f"Seller: {seller_name}, Sales: {ss['sale_count']}, Revenue: {ss['total_revenue']}")
        
        elif choice == "4":
            # List all users
            cursor = conn_inventory.execute("""
                SELECT u.username, u.first_name, u.middle_name, u.last_name, u.role
                FROM users u
                JOIN user_stores us ON u.id = us.user_id
                WHERE us.store_id = ?
            """, (store_id,))
            
            users = cursor.fetchall()
            if not users:
                print("No users found in your store.")
                return
            
            print("\nAll Users in Store:")
            for user in users:
                middle_name = user['middle_name'] or ''
                print(f"Username: {user['username']}, Name: {user['first_name']} {middle_name} {user['last_name']}, Role: {user['role']}")
        
        elif choice == "5":
            # Expired stock
            today = datetime.now().date().isoformat()
            
            cursor = conn_inventory.execute("""
                SELECT id, name, stock_quantity, expiry_date
                FROM products
                WHERE store_id = ? AND expiry_date IS NOT NULL AND expiry_date < ?
            """, (store_id, today))
            
            expired_products = cursor.fetchall()
            if not expired_products:
                print("No expired products found.")
                return
            
            print("\nExpired Stock:")
            for product in expired_products:
                print(f"ID: {product['id']}, Name: {product['name']}, Stock: {product['stock_quantity']}, Expiry: {product['expiry_date']}")
        
        elif choice == "6":
            return
        
        else:
            print("Invalid choice.")
            
    except sqlite3.Error as e:
        print(f"{Colors.RED}Error viewing reports: {e}{Colors.RESET}")
    finally:
        conn_inventory.close()
        conn_sales.close()

def view_sales_by_seller(current_user):
    """View sales by specific seller with date filters"""
    conn_sales = get_db_connection(SALES_DB)
    conn_inventory = get_db_connection(INVENTORY_DB)
    
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can view sales by seller.{Colors.RESET}")
            return
        
        store_id = current_user['current_store_id']
        if not store_id:
            print(f"{Colors.RED}No store selected. Please switch to a store first.{Colors.RESET}")
            return
        
        # Get store name
        cursor = conn_inventory.execute("SELECT name FROM stores WHERE id = ?", (store_id,))
        store = cursor.fetchone()
        
        print(f"\n=== Sales by Seller for Store: {store['name']} ===")
        
        # Get sellers in the store
        cursor = conn_inventory.execute("""
            SELECT u.username, u.first_name, u.last_name
            FROM users u
            JOIN user_stores us ON u.id = us.user_id
            WHERE us.store_id = ? AND u.role = 'seller'
        """, (store_id,))
        
        sellers = cursor.fetchall()
        if not sellers:
            print(f"{Colors.RED}No sellers found in your store.{Colors.RESET}")
            return
        
        print("\nAvailable Sellers:")
        for seller in sellers:
            print(f"Username: {seller['username']}, Name: {seller['first_name']} {seller['last_name']}")
        
        username = input("Enter seller's username: ").strip()
        
        # Verify seller exists in the store
        cursor = conn_inventory.execute("""
            SELECT u.id
            FROM users u
            JOIN user_stores us ON u.id = us.user_id
            WHERE u.username = ? AND us.store_id = ? AND u.role = 'seller'
        """, (username, store_id))
        
        seller = cursor.fetchone()
        if not seller:
            print(f"{Colors.RED}No seller found with username '{username}' in your store.{Colors.RESET}")
            return
        
        # Date filter options
        print("\nSelect Date Filter Type:")
        print("1. Specific Date")
        print("2. This Week")
        print("3. This Month")
        print("4. No Filter")
        
        date_filter = input("Choose (1-4): ").strip()
        
        # Build query based on date filter
        query = """
            SELECT s.id, s.total_price, s.payment_method, s.created_at
            FROM sales s
            WHERE s.store_id = ? AND s.user_id = ?
        """
        params = [store_id, seller['id']]
        
        if date_filter == "1":
            date_input = input("Enter date (YYYY-MM-DD): ").strip()
            query += " AND DATE(s.created_at) = ?"
            params.append(date_input)
        elif date_filter == "2":
            # This week (Monday to Sunday)
            today = datetime.now().date()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            
            query += " AND DATE(s.created_at) BETWEEN ? AND ?"
            params.extend([start_of_week.isoformat(), end_of_week.isoformat()])
        elif date_filter == "3":
            # This month
            today = datetime.now().date()
            start_of_month = today.replace(day=1)
            next_month = today.replace(day=28) + timedelta(days=4)  # Move to next month
            end_of_month = next_month - timedelta(days=next_month.day)
            
            query += " AND DATE(s.created_at) BETWEEN ? AND ?"
            params.extend([start_of_month.isoformat(), end_of_month.isoformat()])
        elif date_filter != "4":
            print(f"{Colors.RED}Invalid date filter choice.{Colors.RESET}")
            return
        
        query += " ORDER BY s.created_at DESC"
        
        cursor = conn_sales.execute(query, params)
        sales = cursor.fetchall()
        
        if not sales:
            print(f"{Colors.RED}No sales recorded for seller '{username}' with the selected filters.{Colors.RESET}")
            return
        
        total_amount = sum(sale['total_price'] for sale in sales)
        
        print(f"\nSales by Seller '{username}':")
        for sale in sales:
            print(f"ID: {sale['id']}, Amount: {sale['total_price']}, Method: {sale['payment_method']}, Date: {sale['created_at']}")
        
        print(f"\nTotal Amount Sold: {total_amount}")
        
        # Payment method summary
        payment_summary = {}
        for sale in sales:
            method = sale['payment_method']
            if method not in payment_summary:
                payment_summary[method] = {'count': 0, 'amount': 0}
            payment_summary[method]['count'] += 1
            payment_summary[method]['amount'] += sale['total_price']
        
        if payment_summary:
            print("\nSummary by Payment Method:")
            for method, data in payment_summary.items():
                print(f"{method}: {data['count']} sales, Total: {data['amount']}")
        
    except sqlite3.Error as e:
        print(f"{Colors.RED}Error viewing sales by seller: {e}{Colors.RESET}")
    finally:
        conn_sales.close()
        conn_inventory.close()