# sale_products.py
"""
Module to handle sales of products with FIFO stock management and profit calculation
"""

from Databases.database_connection import get_db_connection, INVENTORY_DB, SALES_DB, DEBTS_DB, OTHER_PAYMENTS_DB
import sqlite3
from datetime import datetime
import re
import time

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def sanitize_input(text):
    """Sanitize user input"""
    return re.sub(r'[^\w\s\-\.@]', '', text)

def validate_phone(phone):
    """Validate phone number format"""
    pattern = r'^\+?255\d{9}$|^0\d{9}$'
    return re.match(pattern, phone) is not None

def initialize_sales_system():
    """
    Initialize the sales system with required tables and columns
    """
    try:
        # make sure all tables exist
        if not create_sale_batch_allocation_table():
            return False
        
        # Then add columns if they don't exist for original_quantity
        if not add_original_quantity_column():
            return False
            
        print(f"{Colors.GREEN}Sales system initialized successfully.{Colors.RESET}")
        return True
    except Exception as e:
        print(f"{Colors.RED}Error initializing sales system: {e}{Colors.RESET}")
        return False

def create_sale_batch_allocation_table():
    """
    Create table to track which batches were used for which sales
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_db_connection(SALES_DB)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sale_batch_allocations (
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
                )
            """)
            conn.commit()
            conn.close()
            print(f"{Colors.GREEN}Sale batch allocations table created/verified.{Colors.RESET}")
            return True
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Database locked, retrying... ({attempt + 1}/{max_retries}){Colors.RESET}")
                time.sleep(0.5)
                continue
            else:
                print(f"{Colors.RED}Error creating sale batch allocations table: {e}{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.RED}Error creating sale batch allocations table: {e}{Colors.RESET}")
            return False

def add_original_quantity_column():
    """
    Add original_quantity column to stock_batches table if it doesn't exist
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_db_connection(INVENTORY_DB)
            
            # Check if column exists
            cursor = conn.execute("PRAGMA table_info(stock_batches)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'original_quantity' not in columns:
                conn.execute("ALTER TABLE stock_batches ADD COLUMN original_quantity INTEGER")
                
                # Update existing records
                conn.execute("UPDATE stock_batches SET original_quantity = quantity WHERE original_quantity IS NULL")
                
                conn.commit()
                print(f"{Colors.GREEN}Added original_quantity column to stock_batches.{Colors.RESET}")
            
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Database locked, retrying... ({attempt + 1}/{max_retries}){Colors.RESET}")
                time.sleep(0.5)
                continue
            else:
                print(f"{Colors.RED}Error adding original_quantity column: {e}{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.RED}Error adding original_quantity column: {e}{Colors.RESET}")
            return False

def search_products(current_user):
    """Search for products in the current store"""
    store_id = current_user['current_store_id']
    
    try:
        conn = get_db_connection(INVENTORY_DB)
        
        search_term = input("Enter product name to search (or press Enter to see all): ").strip()
        
        if search_term:
            # Search by product name
            cursor = conn.execute("""
                SELECT 
                    p.id,
                    p.name, 
                    p.stock_quantity, 
                    p.unit,
                    p.product_code,
                    spp.retail_price, 
                    spp.wholesale_price,
                    spp.wholesale_threshold
                FROM products p
                LEFT JOIN store_product_prices spp ON p.id = spp.product_id AND p.store_id = spp.store_id
                WHERE p.store_id = ? AND p.name LIKE ?
                ORDER BY p.name
            """, (store_id, f'%{search_term}%'))
        else:
            # Show all products
            cursor = conn.execute("""
                SELECT 
                    p.id,
                    p.name, 
                    p.stock_quantity, 
                    p.unit,
                    p.product_code,
                    spp.retail_price, 
                    spp.wholesale_price,
                    spp.wholesale_threshold
                FROM products p
                LEFT JOIN store_product_prices spp ON p.id = spp.product_id AND p.store_id = spp.store_id
                WHERE p.store_id = ? 
                ORDER BY p.name
            """, (store_id,))
        
        products = cursor.fetchall()
        conn.close()
        
        if not products:
            print(f"{Colors.RED}No products found.{Colors.RESET}")
            return None
        
        # Display products
        print(f"\n{Colors.BLUE}=== Search Results ==={Colors.RESET}")
        for i, product in enumerate(products, 1):
            print(f"{i}. {product['name']} - Stock: {product['stock_quantity']} {product['unit']} - "
                  f"Retail: {product['retail_price'] or 'N/A'} - Wholesale: {product['wholesale_price'] or 'N/A'}")
        
        # Let user select a product
        while True:
            try:
                choice = input(f"\nSelect product (1-{len(products)}) or 0 to cancel: ").strip()
                if choice == '0':
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(products):
                    selected_product = products[choice_num - 1]
                    
                    # Check if product has prices
                    if selected_product['retail_price'] is None:
                        print(f"{Colors.RED}This product has no pricing information. Please set prices first.{Colors.RESET}")
                        return None
                    
                    return selected_product
                else:
                    print(f"{Colors.RED}Invalid selection.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}Please enter a valid number.{Colors.RESET}")
                
    except Exception as e:
        print(f"{Colors.RED}Error searching products: {e}{Colors.RESET}")
        return None

def get_stock_batches_for_sale(product_id, store_id, quantity_needed):
    """
    Get stock batches using FIFO method for sale
    Returns: list of batches with quantities to deduct
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_db_connection(INVENTORY_DB)
            cursor = conn.execute("""
                SELECT 
                    id, product_id, product_code, store_id, store_code,
                    batch_number, quantity, buying_price, shipping_cost, 
                    handling_cost, landed_cost, received_date, expiry_date,
                    is_active, expected_margin, actual_margin, original_quantity
                FROM stock_batches 
                WHERE product_id = ? AND store_id = ? AND is_active = 1 AND quantity > 0
                ORDER BY received_date ASC, id ASC
            """, (product_id, store_id))
            
            batches = cursor.fetchall()
            conn.close()
            
            if not batches:
                return None
            
            # Distribute quantity needed across batches (FIFO)
            remaining_quantity = quantity_needed
            batches_to_update = []
            
            for batch in batches:
                if remaining_quantity <= 0:
                    break
                    
                batch_quantity = min(batch['quantity'], remaining_quantity)
                batches_to_update.append({
                    'batch_id': batch['id'],
                    'batch_number': batch['batch_number'],
                    'quantity_to_deduct': batch_quantity,
                    'current_quantity': batch['quantity'],
                    'landed_cost': batch['landed_cost'],
                    'buying_price': batch['buying_price'],
                    'shipping_cost': batch['shipping_cost'],
                    'handling_cost': batch['handling_cost'],
                    'expected_margin': batch['expected_margin'],
                    'original_quantity': batch['original_quantity']
                })
                
                remaining_quantity -= batch_quantity
            
            # If not enough stock across all batches
            if remaining_quantity > 0:
                return None
                
            return batches_to_update
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Database locked, retrying... ({attempt + 1}/{max_retries}){Colors.RESET}")
                time.sleep(0.5)
                continue
            else:
                print(f"{Colors.RED}Error getting stock batches: {e}{Colors.RESET}")
                return None
        except Exception as e:
            print(f"{Colors.RED}Error getting stock batches: {e}{Colors.RESET}")
            return None

def update_stock_batches_after_sale(batches_to_update, sale_price_per_unit, total_quantity):
    """
    Update stock batches after sale and calculate actual profit
    """
    max_retries = 5  # Ongeza retries
    for attempt in range(max_retries):
        try:
            conn = get_db_connection(INVENTORY_DB)
            total_actual_profit = 0
            
            for batch in batches_to_update:
                # Calculate actual margin per unit for this batch
                actual_margin_per_unit = sale_price_per_unit - batch['landed_cost']
                
                # Calculate total actual profit for this batch portion
                batch_actual_profit = actual_margin_per_unit * batch['quantity_to_deduct']
                
                # Update batch quantity
                new_quantity = batch['current_quantity'] - batch['quantity_to_deduct']
                is_active = 1 if new_quantity > 0 else 0
                
                # Update the batch
                conn.execute("""
                    UPDATE stock_batches 
                    SET quantity = ?, 
                        is_active = ?,
                        actual_margin = ?,
                        synced = 0,
                        total_actual_profit = COALESCE(total_actual_profit, 0) + ?
                    WHERE id = ?
                """, (new_quantity, is_active, actual_margin_per_unit, batch_actual_profit, batch['batch_id']))
                
                total_actual_profit += batch_actual_profit
            
            conn.commit()
            conn.close()
            
            print(f"{Colors.GREEN}Successfully updated {len(batches_to_update)} stock batches.{Colors.RESET}")
            return {
                'total_actual_profit': total_actual_profit
            }
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Database locked, retrying... ({attempt + 1}/{max_retries}){Colors.RESET}")
                time.sleep(1.0)  
                continue
            else:
                print(f"{Colors.RED}Error updating stock batches: {e}{Colors.RESET}")
                return None
        except Exception as e:
            print(f"{Colors.RED}Error updating stock batches: {e}{Colors.RESET}")
            return None

def calculate_batch_profit(batch_id):
    """
    Calculate and update final profit for a batch when stock reaches 0
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_db_connection(INVENTORY_DB)
            
            # Get batch information
            cursor = conn.execute("""
                SELECT 
                    id, quantity, landed_cost, expected_margin,
                    actual_margin, total_actual_profit, original_quantity
                FROM stock_batches 
                WHERE id = ?
            """, (batch_id,))
            
            batch = cursor.fetchone()
            
            if not batch:
                conn.close()
                return False
            
            # If batch is empty, ensure profit is calculated
            if batch['quantity'] == 0:
                # Use actual margin if available, otherwise use expected margin
                final_actual_margin = batch['actual_margin'] if batch['actual_margin'] is not None else batch['expected_margin']
                
                # Calculate total actual profit based on original quantity
                if batch['total_actual_profit'] is None and final_actual_margin is not None:
                    final_actual_profit = final_actual_margin * batch['original_quantity']
                    
                    # Update the batch with final profit calculations
                    conn.execute("""
                        UPDATE stock_batches 
                        SET actual_margin = ?,
                            total_actual_profit = ?
                        WHERE id = ?
                    """, (final_actual_margin, final_actual_profit, batch_id))
                    
                    conn.commit()
                    print(f"{Colors.GREEN}Batch {batch_id} final profit calculated: {final_actual_profit}{Colors.RESET}")
            
            conn.close()
            return True
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Database locked, retrying... ({attempt + 1}/{max_retries}){Colors.RESET}")
                time.sleep(0.5)
                continue
            else:
                print(f"{Colors.RED}Error calculating batch profit: {e}{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.RED}Error calculating batch profit: {e}{Colors.RESET}")
            return False

def ensure_sale_batch_allocations_table():
    """
    Ensure the sale_batch_allocations table exists
    """
    try:
        conn = get_db_connection(SALES_DB)
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sale_batch_allocations'
        """)
        table_exists = cursor.fetchone()
        conn.close()
        
        if not table_exists:
            print(f"{Colors.YELLOW}Creating sale_batch_allocations table...{Colors.RESET}")
            return create_sale_batch_allocation_table()
        else:
            print(f"{Colors.GREEN}sale_batch_allocations table verified.{Colors.RESET}")
            return True
    except Exception as e:
        print(f"{Colors.RED}Error checking sale_batch_allocations table: {e}{Colors.RESET}")
        return False

def calculate_sale_profit(sale_id, sale_items):
    """
    Calculate profit for each sale item and update sale_items table
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Hakikisha kwanza table ipo kwenye SALES_DB
            if not ensure_sale_batch_allocations_table():
                print(f"{Colors.RED}Cannot calculate profit: sale_batch_allocations table missing{Colors.RESET}")
                return False
            
            sales_conn = get_db_connection(SALES_DB)
            
            for item in sale_items:
                product_id = item['product_id']
                quantity = item['quantity']
                unit_price = item['unit_price']
                
                # STEP 1: Pata batch allocations kutoka SALES_DB
                sales_cursor = sales_conn.execute("""
                    SELECT batch_id, quantity 
                    FROM sale_batch_allocations 
                    WHERE sale_id = ? AND product_id = ?
                """, (sale_id, product_id))
                
                batch_allocations = sales_cursor.fetchall()
                
                if not batch_allocations:
                    print(f"{Colors.YELLOW}No batch allocations found for product {product_id} in sale {sale_id}{Colors.RESET}")
                    # Use fallback method
                    average_cost_price = calculate_fallback_cost_price(product_id)
                    profit_per_unit = unit_price - average_cost_price
                    total_profit = profit_per_unit * quantity
                else:
                    # STEP 2: Pata landed_cost kutoka INVENTORY_DB kwa kila batch
                    total_cost = 0
                    total_allocated_quantity = 0
                    
                    for allocation in batch_allocations:
                        batch_id = allocation['batch_id']
                        allocated_quantity = allocation['quantity']
                        
                        # Pata landed_cost kutoka inventory database
                        inventory_conn = get_db_connection(INVENTORY_DB)
                        batch_cursor = inventory_conn.execute("""
                            SELECT landed_cost 
                            FROM stock_batches 
                            WHERE id = ?
                        """, (batch_id,))
                        
                        batch_data = batch_cursor.fetchone()
                        inventory_conn.close()
                        
                        if batch_data and batch_data['landed_cost'] is not None:
                            total_cost += batch_data['landed_cost'] * allocated_quantity
                            total_allocated_quantity += allocated_quantity
                    
                    if total_allocated_quantity > 0:
                        average_cost_price = total_cost / total_allocated_quantity
                        profit_per_unit = unit_price - average_cost_price
                        total_profit = profit_per_unit * quantity
                    else:
                        # Fallback ikiwa hakuna allocated quantities
                        average_cost_price = calculate_fallback_cost_price(product_id)
                        profit_per_unit = unit_price - average_cost_price
                        total_profit = profit_per_unit * quantity
                
                # STEP 3: Update sale_items table kwenye SALES_DB
                sales_conn.execute("""
                    UPDATE sale_items 
                    SET cost_price = ?
                    
                    WHERE sale_id = ? AND product_id = ?
                """, (average_cost_price,sale_id, product_id))
                
                print(f"{Colors.GREEN}Updated profit for product {product_id}: cost={average_cost_price}, profit={total_profit}{Colors.RESET}")
            
            sales_conn.commit()
            sales_conn.close()
            
            print(f"{Colors.GREEN}Sale profit calculated successfully for sale ID: {sale_id}{Colors.RESET}")
            return True
            
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"{Colors.YELLOW}Database locked, retrying... ({attempt + 1}/{max_retries}){Colors.RESET}")
                time.sleep(0.5)
                continue
            else:
                print(f"{Colors.RED}Error calculating sale profit: {e}{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.RED}Error calculating sale profit: {e}{Colors.RESET}")
            return False
        
def calculate_fallback_cost_price(product_id):
    """
    Calculate fallback cost price kama hakuna batch allocations
    """
    try:
        inventory_conn = get_db_connection(INVENTORY_DB)
        cursor = inventory_conn.execute("""
            SELECT AVG(landed_cost) as avg_cost 
            FROM stock_batches 
            WHERE product_id = ? AND is_active = 1 AND landed_cost IS NOT NULL
        """, (product_id,))
        
        avg_cost_data = cursor.fetchone()
        inventory_conn.close()
        
        return avg_cost_data['avg_cost'] if avg_cost_data and avg_cost_data['avg_cost'] is not None else 0
        
    except Exception as e:
        print(f"{Colors.YELLOW}Error calculating fallback cost price: {e}{Colors.RESET}")
        return 0

def make_sale(current_user):
    """
    Process a sale for the current user and store with FIFO stock management
    """
    if not current_user or 'current_store_id' not in current_user:
        print(f"{Colors.RED}No store selected. Please login first.{Colors.RESET}")
        return
    
    store_id = current_user['current_store_id']
    user_id = current_user['id']
    
    try:
        # Verify store exists
        conn = get_db_connection(INVENTORY_DB)
        cursor = conn.execute("SELECT * FROM stores WHERE id = ?", (store_id,))
        store = cursor.fetchone()
        conn.close()
        
        if not store:
            print(f"{Colors.RED}Store not found.{Colors.RESET}")
            return
        
        # Initialize sales system if not done - HAKIKISHA hii imekamilika kwanza
        print(f"{Colors.BLUE}Initializing sales system...{Colors.RESET}")
        if not initialize_sales_system():
            print(f"{Colors.RED}Failed to initialize sales system. Cannot proceed with sale.{Colors.RESET}")
            return
        
        cart = []
        batch_allocations = {}  # To track batch allocations for each product
        
        while True:
            # Search and select product
            product = search_products(current_user)
            if not product:
                if not cart:
                    print(f"{Colors.RED}No product selected. Sale cancelled.{Colors.RESET}")
                    return
                else:
                    print("Returning to cart options.")
                    break
            
            # Get quantity
            while True:
                try:
                    quantity = int(input(f"Enter quantity for '{product['name']}' (available: {product['stock_quantity']}): ").strip())
                    if quantity <= 0:
                        print(f"{Colors.RED}Invalid quantity. Please enter a positive number.{Colors.RESET}")
                        continue
                    
                    if quantity > product['stock_quantity']:
                        print(f"{Colors.RED}Insufficient stock. Available: {product['stock_quantity']}{Colors.RESET}")
                        continue
                    
                    break
                except ValueError:
                    print(f"{Colors.RED}Invalid quantity. Please enter a number.{Colors.RESET}")
            
            # Check FIFO stock availability across batches
            batches_for_sale = get_stock_batches_for_sale(product['id'], store_id, quantity)
            if not batches_for_sale:
                print(f"{Colors.RED}Insufficient stock across batches for {product['name']}. Available: {product['stock_quantity']}{Colors.RESET}")
                continue
            
            # Check if wholesale
            is_wholesale = False
            if product['wholesale_price'] and product['wholesale_threshold']:
                if quantity >= product['wholesale_threshold']:
                    is_wholesale = input("This qualifies for wholesale price. Use wholesale? (yes/no): ").strip().lower() == "yes"
            
            # Calculate price
            if is_wholesale:
                price = product['wholesale_price']
            else:
                price = product['retail_price']
            
            total_price = price * quantity
            
            print(f"Total Price for {quantity} units of {product['name']}: {total_price}")
            
            # Add to cart
            cart.append({
                'product_id': product['id'],
                'product_code': product['product_code'],
                'name': product['name'],
                'quantity': quantity,
                'unit_price': price,
                'is_wholesale': is_wholesale,
                'total_price': total_price,
                'current_stock': product['stock_quantity'],
                'batches': batches_for_sale  # Store batch information
            })
            
            # Store batch allocations for this product
            batch_allocations[product['id']] = batches_for_sale
            
            # Ask to continue
            continue_adding = input("Add another product? (yes/no): ").strip().lower()
            if continue_adding != 'yes':
                break
        
        if not cart:
            print(f"{Colors.RED}Cart is empty. Sale cancelled.{Colors.RESET}")
            return
        
        # Display cart summary
        print(f"\n{Colors.BLUE}=== Cart Summary ==={Colors.RESET}")
        total_cart_value = 0
        for i, item in enumerate(cart, 1):
            print(f"{i}. {item['name']} - Qty: {item['quantity']} - "
                  f"{'Wholesale' if item['is_wholesale'] else 'Retail'} - "
                  f"Price: {item['total_price']}")
            total_cart_value += item['total_price']
        
        print(f"\nTotal Cart Value: {total_cart_value}")
        
        # Confirm sale
        confirm = input("\nConfirm sale? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print(f"{Colors.YELLOW}Sale cancelled.{Colors.RESET}")
            return
        
        # Get payment method
        print("\nPayment Methods:")
        print("1. CASH")
        print("2. MPESA") 
        print("3. BANK")
        print("4. DEBT")
        print("5. OTHER")
        
        payment_choice = input("Choose payment method (1-5): ").strip()
        payment_methods = {
            '1': 'CASH',
            '2': 'MPESA', 
            '3': 'BANK',
            '4': 'DEBT',
            '5': 'OTHER'
        }
        
        payment_method = payment_methods.get(payment_choice)
        if not payment_method:
            print(f"{Colors.RED}Invalid payment method.{Colors.RESET}")
            return
        
        debtor_info = None
        other_description = None
        
        if payment_method == 'DEBT':
            debtor_name = sanitize_input(input("Enter debtor's name: ").strip())
            debtor_phone = input("Enter debtor's phone number: ").strip()
            if not debtor_name or not validate_phone(debtor_phone):
                print(f"{Colors.RED}Debtor's name is required and phone number must be valid.{Colors.RESET}")
                return
            debtor_info = (debtor_name, debtor_phone)
        
        elif payment_method == 'OTHER':
            other_description = sanitize_input(input("Enter payment description: ").strip())
            if not other_description:
                print(f"{Colors.RED}Payment description cannot be empty.{Colors.RESET}")
                return
        
        # Start transaction - FANYA KILA KITU KWA MTIRIRIKO
        print(f"{Colors.BLUE}Starting sale transaction...{Colors.RESET}")
        
        # STEP 1: Create sale in sales.db - HAKIKISHA hii imekamilika kwanza
        print(f"{Colors.BLUE}Step 1: Creating sale record...{Colors.RESET}")
        try:
            sales_conn = get_db_connection(SALES_DB)
            
            # Insert main sale record
            sale_data = {
                'store_id': store_id,
                'store_code': store['store_code'],
                'user_id': user_id,
                'total_price': total_cart_value,
                'payment_method': payment_method,
                'created_at': datetime.now().isoformat(),
                'synced': 0
            }
            
            cursor = sales_conn.execute("""
                INSERT INTO sales (store_id, store_code, user_id, total_price, payment_method, created_at, synced)
                VALUES (:store_id, :store_code, :user_id, :total_price, :payment_method, :created_at, :synced)
            """, sale_data)
            sale_id = cursor.lastrowid
            
            # STEP 2: Insert sale items
            print(f"{Colors.BLUE}Step 2: Recording sale items...{Colors.RESET}")
            for item in cart:
                sale_item_data = {
                    'sale_id': sale_id,
                    'product_id': item['product_id'],
                    'product_code': item['product_code'],
                    'quantity': item['quantity'],
                    'unit_price': item['unit_price'],
                    'is_wholesale': 1 if item['is_wholesale'] else 0,
                    'synced': 0
                }
                
                sales_conn.execute("""
                    INSERT INTO sale_items (sale_id, product_id, product_code, quantity, unit_price, is_wholesale, synced)
                    VALUES (:sale_id, :product_id, :product_code, :quantity, :unit_price, :is_wholesale, :synced)
                """, sale_item_data)
            
            # STEP 3: Record batch allocations - HAKIKISHA table ipo
            print(f"{Colors.BLUE}Step 3: Recording batch allocations...{Colors.RESET}")
            if not ensure_sale_batch_allocations_table():
                raise Exception("Failed to create sale_batch_allocations table")
                
            for item in cart:
                for batch in item['batches']:
                    allocation_data = {
                        'sale_id': sale_id,
                        'product_id': item['product_id'],
                        'batch_id': batch['batch_id'],
                        'quantity': batch['quantity_to_deduct'],
                        'synced': 0
                    }
                    
                    sales_conn.execute("""
                        INSERT INTO sale_batch_allocations (sale_id, product_id, batch_id, quantity, synced)
                        VALUES (:sale_id, :product_id, :batch_id, :quantity, :synced)
                    """, allocation_data)
            
            sales_conn.commit()
            sales_conn.close()
            print(f"{Colors.GREEN}Sale record created successfully. Sale ID: {sale_id}{Colors.RESET}")
            
        except Exception as e:
            print(f"{Colors.RED}Error creating sale record: {e}{Colors.RESET}")
            return
        
        # STEP 4: Update inventory and stock batches - FANYA hii baada ya kurecord sale
        print(f"{Colors.BLUE}Step 4: Updating inventory...{Colors.RESET}")
        try:
            inventory_conn = get_db_connection(INVENTORY_DB)
            for item in cart:
                # Update product stock quantity
                new_stock = item['current_stock'] - item['quantity']
                inventory_conn.execute(
                    "UPDATE products SET stock_quantity = ?, synced = 0 WHERE id = ?",
                    (new_stock, item['product_id'])
                )
                print(f"{Colors.GREEN}Updated product {item['name']} stock to {new_stock}{Colors.RESET}")
            
            inventory_conn.commit()
            inventory_conn.close()
            
            # STEP 5: Update stock batches using FIFO - FANYA hii baada ya kuhakikisha inventory imesave
            print(f"{Colors.BLUE}Step 5: Updating stock batches...{Colors.RESET}")
            for item in cart:
                profit_data = update_stock_batches_after_sale(
                    item['batches'], 
                    item['unit_price'], 
                    item['quantity']
                )
                
                if not profit_data:
                    print(f"{Colors.RED}Failed to update stock batches for {item['name']}{Colors.RESET}")
                    # Continue with other items but log the error
                    continue
                
                # STEP 6: Calculate final profit for batches that reached 0
                print(f"{Colors.BLUE}Step 6: Calculating batch profits...{Colors.RESET}")
                for batch in item['batches']:
                    if batch['current_quantity'] - batch['quantity_to_deduct'] <= 0:
                        if not calculate_batch_profit(batch['batch_id']):
                            print(f"{Colors.YELLOW}Warning: Failed to calculate profit for batch {batch['batch_id']}{Colors.RESET}")
            
        except Exception as e:
            print(f"{Colors.RED}Error updating inventory: {e}{Colors.RESET}")
            return
        
        # STEP 7: Calculate and update sale profit - FANYA hii mwisho
        print(f"{Colors.BLUE}Step 7: Calculating sale profit...{Colors.RESET}")
        if not calculate_sale_profit(sale_id, cart):
            print(f"{Colors.YELLOW}Warning: Failed to calculate sale profit, but sale was recorded.{Colors.RESET}")
        
        # STEP 8: Handle debt and other payments - FANYA hii baada ya kila kitu
        print(f"{Colors.BLUE}Step 8: Processing payment...{Colors.RESET}")
        if payment_method == 'DEBT' and debtor_info:
            try:
                debts_conn = get_db_connection(DEBTS_DB)
                debt_data = {
                    'sale_id': sale_id,
                    'store_id': store_id,
                    'store_code': store['store_code'],
                    'user_id': user_id,
                    'debtor_name': debtor_info[0],
                    'debtor_phone': debtor_info[1],
                    'amount_owed': total_cart_value,
                    'created_at': datetime.now().isoformat(),
                    'synced': 0
                }
                
                debts_conn.execute("""
                    INSERT INTO debts (sale_id, store_id, store_code, user_id, debtor_name, debtor_phone, amount_owed, created_at, synced)
                    VALUES (:sale_id, :store_id, :store_code, :user_id, :debtor_name, :debtor_phone, :amount_owed, :created_at, :synced)
                """, debt_data)
                debts_conn.commit()
                debts_conn.close()
                print(f"{Colors.GREEN}Debt record created.{Colors.RESET}")
                
            except Exception as e:
                print(f"{Colors.YELLOW}Warning: Failed to create debt record: {e}{Colors.RESET}")
        
        elif payment_method == 'OTHER' and other_description:
            try:
                other_conn = get_db_connection(OTHER_PAYMENTS_DB)
                other_payment_data = {
                    'sale_id': sale_id,
                    'store_id': store_id,
                    'store_code': store['store_code'],
                    'description': other_description,
                    'created_at': datetime.now().isoformat(),
                    'synced': 0
                }
                
                other_conn.execute("""
                    INSERT INTO other_payments (sale_id, store_id, store_code, description, created_at, synced)
                    VALUES (:sale_id, :store_id, :store_code, :description, :created_at, :synced)
                """, other_payment_data)
                other_conn.commit()
                other_conn.close()
                print(f"{Colors.GREEN}Other payment record created.{Colors.RESET}")
                
            except Exception as e:
                print(f"{Colors.YELLOW}Warning: Failed to create other payment record: {e}{Colors.RESET}")
        
        # Final success message
        print(f"\n{Colors.GREEN}=== SALE COMPLETED SUCCESSFULLY ==={Colors.RESET}")
        print(f"Sale ID: {sale_id}")
        print(f"Total Amount: {total_cart_value}")
        print(f"Payment Method: {payment_method}")
        print(f"Stock updated using FIFO method.{Colors.RESET}")
            
    except Exception as e:
        print(f"{Colors.RED}An unexpected error occurred during sale: {e}{Colors.RESET}")