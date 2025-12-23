
"""
Enhanced Manual Data Insertion Script for POS System
Standalone script for inserting products into existing stores
Uses the consolidated inventory.db database structure
Implements FIFO stock management with comprehensive cost tracking
"""
# v1.6 - Structured as Professional Big Project


import os
import sys
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Tuple, Any, Dict


current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Now use absolute imports
from database.connection import DatabaseManager, DatabaseConfig
from models.product import Store, Product, ProductCosts
from services.store_service import StoreService
from services.product_service import ProductService
from services.validation_service import ValidationService
from services.cost_calculation_service import CostCalculationService
from utils.color_output import Colors
from utils.helpers import get_database_path, get_sales_db_path, sanitize_input
from ask_for_image import  ask_image_file_dialog


@dataclass
class ApplicationConfig:
    """Application configuration"""
    database_path: str
    sales_db_path: str

class DataInsertionApp:
    """Main application class for manual data insertion"""
    
    def __init__(self):
        self.config = ApplicationConfig(
            database_path=get_database_path(),
            sales_db_path=get_sales_db_path()
        )
        self.db_manager = None
        self.store_service = None
        self.product_service = None
        self.validation_service = None
        self.cost_calculation_service = None
        self.current_store = None
    
    def initialize_services(self) -> bool:
        """Initialize all services and dependencies"""
        try:
            db_config = DatabaseConfig(
                database_path=self.config.database_path,
                sales_db_path=self.config.sales_db_path
            )
            
            self.db_manager = DatabaseManager(db_config)
            if not self.db_manager.setup_databases():
                return False
            
            self.validation_service = ValidationService()
            self.cost_calculation_service = CostCalculationService()
            self.store_service = StoreService(self.db_manager)
            self.product_service = ProductService(
                self.db_manager, 
                self.validation_service, 
                self.cost_calculation_service
            )
            
            return True
        except Exception as e:
            print(f"{Colors.RED}Error initializing services: {e}{Colors.RESET}")
            return False
    
    def check_database_health(self) -> bool:
        """Check if database is healthy and has required tables and data"""
        try:
            required_tables = ['stores', 'users', 'products', 'store_product_prices']
            
            for table in required_tables:
                if not self.db_manager.check_table_exists('inventory', table):
                    print(f"{Colors.RED}Error: Required table '{table}' not found in inventory.db{Colors.RESET}")
                    return False
            
            stores = self.db_manager.execute_query('inventory', "SELECT COUNT(*) FROM stores", fetch=True)
            if not stores or stores[0][0] == 0:
                print(f"{Colors.RED}Error: No stores found in database{Colors.RESET}")
                return False
            
            print(f"{Colors.GREEN}✓ All required tables found{Colors.RESET}")
            print(f"{Colors.GREEN}✓ Database health check passed{Colors.RESET}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}Database health check failed: {e}{Colors.RESET}")
            return False
    
    def handle_existing_product_flow(self, existing_product: Tuple, product_name: str) -> None:
        """
        Handle the flow for existing products with clear options
        """
        product_id, existing_name, current_stock, current_threshold, current_image = existing_product
        
        print(f"\n{Colors.CYAN}=== PRODUCT ALREADY EXISTS ==={Colors.RESET}")
        print(f"Product: {existing_name}")
        print(f"Current Stock: {current_stock}")
        print(f"Low Stock Threshold: {current_threshold}")
        
        print(f"\n{Colors.BLUE}What would you like to do?{Colors.RESET}")
        print("1. 📦 Add NEW Stock Batch (FIFO System)")
        print("   - Add new stock with current market prices")
        print("   - Old stock will be sold first (FIFO)")
        print("   - Perfect for new purchases")
        
        print("2. ✏️ Update Product Information")
        print("   - Change prices, thresholds, or details")
        print("   - Update existing product data")
        print("   - Use if you made a mistake")
        
        print("3. ❌ Cancel - No changes")
        print("   - Go back to main menu")
        print("   - No data will be modified")
        
        try:
            user_input = input(f"\n{Colors.BLUE}Select option (1-3): {Colors.RESET}").strip()
            
            if not user_input:  # Check if input is empty
                print(f"{Colors.RED}Please enter a number between 1 and 3{Colors.RESET}")
                return
            
            choice = int(user_input)
            
            if choice == 1:
                self.add_new_stock_batch(product_id, existing_name)
            elif choice == 2:
                self.update_existing_product(existing_product, existing_name)
            elif choice == 3:
                print(f"{Colors.YELLOW}Operation cancelled{Colors.RESET}")
            else:
                print(f"{Colors.RED}Invalid option selected. Please choose 1, 2, or 3.{Colors.RESET}")
                
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number (1, 2, or 3){Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}Unexpected error: {e}{Colors.RESET}")
    
    def add_new_stock_batch(self, product_id: int, product_name: str) -> bool:
        """ADD NEW STOCK BATCH - Updated for multi-unit awareness"""
        print(f"\n{Colors.BLUE}=== ADD NEW STOCK BATCH ==={Colors.RESET}")
        print(f"Product: {product_name}")
        
        # Check if this is part of multi-unit product
        child_units = self.db_manager.execute_query(
            'inventory',
            """SELECT id, name, relation_to_parent FROM products 
               WHERE parent_product_id = ? OR id = ?""",
            (product_id, product_id),
            fetch=True
        )
        
        if len(child_units) > 1:
            print(f"{Colors.YELLOW}⚠ This product has multiple units{Colors.RESET}")
            return self.add_multi_unit_batch(product_id, product_name, child_units)
        else:
            # Single unit product - use existing logic
            return self.add_single_unit_batch(product_id, product_name)
        
    def add_single_unit_batch(self, product_id: int, product_name: str) -> bool:
        """Add batch to single unit product (existing logic)"""
        try:
            # Get product code
            product_code_result = self.db_manager.execute_query(
                'inventory',
                "SELECT product_code FROM products WHERE id = ?",
                (product_id,),
                fetch=True
            )
            
            if not product_code_result:
                print(f"{Colors.RED}Error: Could not find product code{Colors.RESET}")
                return False
                
            product_code = product_code_result[0][0]
            
            # Get current stock info
            current_stock_result = self.db_manager.execute_query(
                'inventory',
                "SELECT stock_quantity FROM products WHERE id = ?",
                (product_id,),
                fetch=True
            )
            
            current_stock = current_stock_result[0][0] if current_stock_result else 0
            print(f"{Colors.YELLOW}Current stock: {current_stock} units{Colors.RESET}")
            
            # Get current product data for default values
            current_data = self.product_service.get_current_product_data(product_id, self.current_store.id)
            
            # Get comprehensive cost data for new batch WITH DEFAULT VALUES
            costs = self.product_service.get_comprehensive_product_costs(
                product_id, product_name, is_largest_unit=True, current_data=current_data
            )
            if not costs:
                return False
            
            # ✅ FIXED: Use current stock as default value
            new_quantity = self.validation_service.update_with_validation_int(
                f"Enter quantity to add to stock (current: {current_stock})",
                current_stock,  # ✅ Use current stock as default
                min_value=0
            )
            
            # Create stock batch
            batch_id = self.product_service.create_stock_batch(
                product_id, product_code, self.current_store, costs, new_quantity, None
            )

            if batch_id:
                # Update stock quantity
                new_total_stock = current_stock + new_quantity
                
                update_result = self.db_manager.execute_query(
                    'inventory',
                    """UPDATE products SET 
                        stock_quantity = ?, 
                        updated_at = datetime('now')
                       WHERE id = ?""",
                    (new_total_stock, product_id)
                )
                
                # Update prices
                price_update = self.db_manager.execute_query(
                    'inventory',
                    """UPDATE store_product_prices SET 
                        retail_price = ?, 
                        wholesale_price = ?, 
                        wholesale_threshold = ?,
                        synced = 0
                       WHERE product_id = ? AND store_id = ?""",
                    (costs.retail_price, costs.wholesale_price, costs.wholesale_threshold, 
                     product_id, self.current_store.id)
                )
                
                if update_result is not None and price_update is not None:
                    print(f"{Colors.GREEN}✓ New stock batch added successfully!{Colors.RESET}")
                    print(f"{Colors.GREEN}  Added Quantity: {new_quantity}{Colors.RESET}")
                    print(f"{Colors.GREEN}  New Total Stock: {new_total_stock}{Colors.RESET}")
                    return True
                else:
                    print(f"{Colors.RED}Error: Failed to update product information{Colors.RESET}")
                    return False
            else:
                print(f"{Colors.RED}Error: Failed to create stock batch{Colors.RESET}")
                return False
                
        except Exception as e:
            print(f"{Colors.RED}Error adding stock batch: {e}{Colors.RESET}")
            return False

    def add_multi_unit_batch(self, parent_product_id: int, product_name: str, child_units: List[Tuple]) -> bool:
        """
        Add batch to multi-unit product (all units at once) with SMART DEFAULTS
        FIXED: Proper smart defaults for both stock AND costs
        """
        print(f"\n{Colors.BLUE}=== ADD BATCH TO MULTI-UNIT PRODUCT ==={Colors.RESET}")
        
        batch_data = []
        
        print(f"{Colors.CYAN}Enter stock for all units:{Colors.RESET}")
        
        # 1. GET CURRENT STOCK FOR ALL UNITS FIRST
        current_stocks = {}
        for unit in child_units:
            unit_id = unit[0]
            current_stock_result = self.db_manager.execute_query(
                'inventory',
                "SELECT stock_quantity FROM products WHERE id = ?",
                (unit_id,),
                fetch=True
            )
            current_stocks[unit_id] = current_stock_result[0][0] if current_stock_result else 0
        
            #  FIXED: BUILD PROPER HIERARCHY ORDER - FULL DEPTH (PARENT → ALL CHILDREN)
            ordered_units = []

            try:
                parent_unit = None
                child_units_list = []

                for unit in child_units:
                    unit_id = unit[0]
                    unit_name = unit[1]
                    relation = unit[2] if len(unit) > 2 else 1

                    parent_check = self.db_manager.execute_query(
                        'inventory',
                        "SELECT parent_product_id FROM products WHERE id = ?",
                        (unit_id,),
                        fetch=True
                    )

                    parent_id = parent_check[0][0] if parent_check and parent_check[0][0] is not None else None

                    if parent_id is None:
                        parent_unit = {
                            'id': unit_id,
                            'name': unit_name,
                            'relation': relation,
                            'is_parent': True
                        }
                    else:
                        child_units_list.append({
                            'id': unit_id,
                            'name': unit_name,
                            'relation': relation,
                            'parent_id': parent_id,
                            'is_parent': False
                        })

                # 🧩 Recursive builder ya order yote
                def build_order(parent, children, ordered):
                    ordered.append(parent)
                    direct_kids = [c for c in children if c['parent_id'] == parent['id']]
                    direct_kids.sort(key=lambda x: x['relation'], reverse=True)
                    for kid in direct_kids:
                        build_order(kid, children, ordered)

                if parent_unit:
                    ordered_units = []
                    build_order(parent_unit, child_units_list, ordered_units)
                else:
                    ordered_units = [{'id': u[0], 'name': u[1], 'relation': (u[2] if len(u) > 2 else 1)} for u in child_units]

            except Exception as e:
                print(f"{Colors.YELLOW}⚠ Warning building hierarchy: {e}{Colors.RESET}")
                ordered_units = [{'id': u[0], 'name': u[1], 'relation': (u[2] if len(u) > 2 else 1)} for u in child_units]

        # ✅ DEBUG: Show the order we're using
        print(f"{Colors.CYAN}📦 Processing units in order:{Colors.RESET}")
        for i, unit in enumerate(ordered_units):
            unit_type = "PARENT" if unit.get('is_parent', False) else "CHILD"
            relation_info = f" (1 {ordered_units[i-1]['name']} = {unit['relation']} {unit['name']})" if i > 0 else ""
            print(f"{Colors.CYAN}  {i+1}. {unit['name']} ({unit_type}){relation_info}{Colors.RESET}")
        
        # ✅ 2. COLLECT DATA FOR EACH UNIT WITH SMART DEFAULTS - STARTING WITH PARENT
        parent_costs = None
        parent_quantity = None
        
        for unit in ordered_units:
            unit_id = unit['id']
            unit_name = unit['name']
            relation = unit.get('relation', 1)
            is_parent = unit.get('is_parent', False)
            
            print(f"\n{Colors.YELLOW}--- {unit_name} {'(LARGEST UNIT)' if is_parent else ''} ---{Colors.RESET}")
            
            # ✅ SMART DEFAULT STOCK
            if is_parent:
                # Parent unit: default is current stored stock
                default_stock = current_stocks.get(unit_id, 0)
                print(f"{Colors.CYAN}Current stock: {default_stock} units{Colors.RESET}")
            else:
                # ✅ Child unit: SMART DEFAULT = parent_quantity * relation
                if parent_quantity is not None:
                    calculated_stock = parent_quantity * relation
                    current_stock = current_stocks.get(unit_id, 0)
                    default_stock = calculated_stock
                    print(f"{Colors.CYAN}Smart default: {parent_quantity} (parent) × {relation} (relation) = {calculated_stock} units{Colors.RESET}")
                    print(f"{Colors.CYAN}Current stock: {current_stock} units{Colors.RESET}")
                else:
                    # Fallback to current DB stock if no parent quantity
                    default_stock = current_stocks.get(unit_id, 0)
                    print(f"{Colors.CYAN}Current stock: {default_stock} units{Colors.RESET}")
            
            current_data = self.product_service.get_current_product_data(unit_id, self.current_store.id)
            
            # ✅ VALIDATE STOCK QUANTITY WITH SMART DEFAULT
            quantity = self.validation_service.validate_stock_quantity(
                f"Enter quantity to add for {unit_name}",
                default_stock
            )
            
            # ✅ HIFADHI QUANTITY YA PARENT KWA MATUMIZI YA CHILDREN
            if is_parent:
                parent_quantity = quantity
            
            # ✅ FIXED: SMART DEFAULTS FOR COSTS - OVERRIDE CURRENT DATA WITH CALCULATED DEFAULTS
            if is_parent:
                # Parent unit - get normal costs
                costs = self.product_service.get_comprehensive_product_costs(
                    unit_id, unit_name, is_largest_unit=True, current_data=current_data
                )
                parent_costs = costs
            else:
                # ✅ FIXED: Child unit - CREATE UPDATED CURRENT DATA WITH CALCULATED DEFAULTS
                if parent_costs:
                    # Calculate smart defaults
                    calculated_buying = parent_costs.buying_price ,#/ relation
                    calculated_shipping = parent_costs.shipping_cost, #/ relation
                    calculated_handling = parent_costs.handling_cost, #/ relation
                    
                    # print(f"{Colors.CYAN}Smart cost defaults from parent:{Colors.RESET}")
                    # print(f"{Colors.CYAN}  Buying: {parent_costs.buying_price:.2f} ÷ {relation} = {calculated_buying:.2f}{Colors.RESET}")
                    # print(f"{Colors.CYAN}  Shipping: {parent_costs.shipping_cost:.2f} ÷ {relation} = {calculated_shipping:.2f}{Colors.RESET}")
                    # print(f"{Colors.CYAN}  Handling: {parent_costs.handling_cost:.2f} ÷ {relation} = {calculated_handling:.2f}{Colors.RESET}")
                    
                    # ✅ FIXED: Override current data with calculated defaults
                    updated_current_data = current_data.copy() if current_data else {}
                    updated_current_data['buying_price'] = calculated_buying
                    updated_current_data['shipping_cost'] = calculated_shipping
                    updated_current_data['handling_cost'] = calculated_handling
                    
                    parent_unit_data = {
                        'relation': relation,
                        'buying_price': calculated_buying,
                        'shipping_cost': calculated_shipping,
                        'handling_cost': calculated_handling
                    }
                else:
                    # fallback
                    updated_current_data = current_data
                    parent_unit_data = {
                        'relation': relation,
                        'buying_price': (current_data.get('buying_price', 0) / relation) if current_data else 0,
                        'shipping_cost': (current_data.get('shipping_cost', 0) / relation) if current_data else 0,
                        'handling_cost': (current_data.get('handling_cost', 0) / relation) if current_data else 0
                    }
                
                # ✅ FIXED: Pass the updated current data with calculated defaults
                costs = self.product_service.get_comprehensive_product_costs(
                    unit_id, unit_name, 
                    is_largest_unit=False, 
                    parent_unit_data=parent_unit_data,
                    current_data=updated_current_data  # ✅ Use updated data with calculated defaults
                )
            
            if not costs:
                return False
            
            # ✅ 5. GET PRODUCT CODE FROM DATABASE
            product_code_result = self.db_manager.execute_query(
                'inventory',
                "SELECT product_code FROM products WHERE id = ?",
                (unit_id,),
                fetch=True
            )
            product_code = product_code_result[0][0] if product_code_result else f"PROD_{unit_id}"
            
            batch_data.append({
                'product_id': unit_id,
                'product_code': product_code,
                'product_name': unit_name,
                'quantity': quantity,
                'costs': costs,
                'current_stock': current_stocks.get(unit_id, 0),
                'relation': relation,
                'is_parent': is_parent
            })
        
        # ✅ 6. CREATE BATCHES FOR ALL UNITS
        success_count = 0
        for unit_data in batch_data:
            batch_id = self.product_service.create_stock_batch(
                unit_data['product_id'], unit_data['product_code'], self.current_store, 
                unit_data['costs'], unit_data['quantity'], None
            )
            
            if batch_id:
                # Update product stock
                new_stock = unit_data['current_stock'] + unit_data['quantity']
                update_result = self.db_manager.execute_query(
                    'inventory',
                    "UPDATE products SET stock_quantity = ? WHERE id = ?",
                    (new_stock, unit_data['product_id'])
                )
                
                if update_result is not None:
                    success_count += 1
                    unit_type = "LARGEST" if unit_data['is_parent'] else "UNIT"
                    print(f"{Colors.GREEN}✓ Added to batch: {unit_data['quantity']} {unit_data['product_name']} ({unit_type}) (Total: {new_stock}){Colors.RESET}")
                    
                    # Update prices in store_product_prices
                    price_update = self.db_manager.execute_query(
                        'inventory',
                        """UPDATE store_product_prices SET 
                            retail_price = ?, 
                            wholesale_price = ?, 
                            wholesale_threshold = ?,
                            synced = 0
                        WHERE product_id = ? AND store_id = ?""",
                        (unit_data['costs'].retail_price, unit_data['costs'].wholesale_price, 
                        unit_data['costs'].wholesale_threshold, unit_data['product_id'], self.current_store.id)
                    )
                else:
                    print(f"{Colors.RED}❌ Failed to update stock for {unit_data['product_name']}{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Failed to create batch for {unit_data['product_name']}{Colors.RESET}")
        
        if success_count == len(batch_data):
            print(f"\n{Colors.GREEN}🎉 All units added to batch successfully!{Colors.RESET}")
            return True
        else:
            print(f"\n{Colors.YELLOW}⚠ Some units failed to be added to batch{Colors.RESET}")
            return False
        
    def update_existing_product(self, existing_product: Tuple, product_name: str) -> None:
        """
        Enhanced update existing product information with batch management
        """
        product_id, existing_name, current_stock, current_threshold, current_image = existing_product
        
        print(f"\n{Colors.BLUE}=== UPDATE PRODUCT INFORMATION ==={Colors.RESET}")
        print(f"Product: {product_name}")
        
        # CHECK EXISTING BATCHES
        batches = self.db_manager.execute_query(
            'inventory',
            """SELECT id, batch_number, quantity, buying_price, expiry_date, is_active
               FROM stock_batches 
               WHERE product_id = ? 
               ORDER BY received_date ASC""",
            (product_id,),
            fetch=True
        )
        
        active_batches = [batch for batch in batches if batch[5] == 1]  # Filter active batches
        
        if active_batches:
            print(f"\n{Colors.CYAN}📦 EXISTING STOCK BATCHES:{Colors.RESET}")
            for i, (batch_id, batch_number, quantity, buying_price, expiry_date, is_active) in enumerate(active_batches, 1):
                expiry_display = expiry_date if expiry_date else "No expiry"
                status = "ACTIVE" if is_active == 1 else "INACTIVE"
                print(f"{i}. {batch_number}: {quantity} units - Buying: {buying_price:.2f} - Expiry: {expiry_display} - {status}")
        
        # UPDATE OPTIONS
        print(f"\n{Colors.BLUE}Update Options:{Colors.RESET}")
        print("1. 📊 Update Basic Product Information")
        print("2. 🏷️  Update Specific Stock Batch")
        print("3. 🔄 Update All Information (Comprehensive)")
        print("4. ❌ Cancel")
        
        try:
            option = int(input(f"{Colors.BLUE}Select update option (1-4): {Colors.RESET}").strip())
            
            if option == 1:
                self.update_basic_product_info(product_id, product_name, current_stock, current_threshold, current_image)
            elif option == 2:
                self.update_specific_batch(active_batches, product_id, product_name)
            elif option == 3:
                self.update_all_product_info(product_id, product_name, current_stock, current_threshold, current_image, active_batches)
            elif option == 4:
                print(f"{Colors.YELLOW}Update cancelled{Colors.RESET}")
            else:
                print(f"{Colors.RED}Invalid option{Colors.RESET}")
                
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number{Colors.RESET}")
    
    def update_basic_product_info(self, product_id: int, product_name: str, current_stock: int, 
                                current_threshold: int, current_image: str) -> None:
        """Update basic product information with batch-specific data"""
        print(f"\n{Colors.BLUE}=== UPDATE BASIC PRODUCT INFO ==={Colors.RESET}")
        print(f"Product: {product_name}")
        
        try:
            # 1. KWANZA: CHAGUA BATCH KUFANYIA UPDATE
            batches = self.db_manager.execute_query(
                'inventory',
                """SELECT id, batch_number, quantity, buying_price, expiry_date, is_active
                   FROM stock_batches 
                   WHERE product_id = ? AND is_active = 1
                   ORDER BY received_date ASC""",
                (product_id,),
                fetch=True
            )
            
            if not batches:
                print(f"{Colors.RED}❌ No active batches found for this product{Colors.RESET}")
                return
            
            print(f"\n{Colors.CYAN}📦 SELECT BATCH TO UPDATE:{Colors.RESET}")
            for i, (batch_id, batch_number, batch_quantity, batch_buying_price, batch_expiry, is_active) in enumerate(batches, 1):
                expiry_display = batch_expiry if batch_expiry else "No expiry"
                print(f"{i}. {batch_number}: {batch_quantity} units - Buying: {batch_buying_price:.2f} - Expiry: {expiry_display}")
            
            batch_choice = int(input(f"{Colors.BLUE}Select batch (1-{len(batches)}): {Colors.RESET}").strip())
            if not (1 <= batch_choice <= len(batches)):
                print(f"{Colors.RED}❌ Invalid batch selection{Colors.RESET}")
                return
            
            batch_id, batch_number, batch_quantity, batch_buying_price, batch_expiry, is_active = batches[batch_choice - 1]
            
            # 2. PATA DATA YA CURRENT BATCH NA PRODUCT
            current_data = self.product_service.get_current_product_data(product_id, self.current_store.id)
            if not current_data:
                print(f"{Colors.RED}❌ Could not retrieve current product data{Colors.RESET}")
                return
            
            # 3. ONYESHA CURRENT INFORMATION YA BATCH HUSIKA
            print(f"\n{Colors.CYAN}🔄 CURRENT BATCH INFORMATION:{Colors.RESET}")
            print(f"Selected Batch: {batch_number}")
            print(f"Batch Stock Quantity: {batch_quantity}")
            print(f"Batch Buying Price: {batch_buying_price:.2f}")
            print(f"Batch Expiry Date: {batch_expiry or 'None'}")
            print(f"Product Retail Price: {current_data['retail_price']:.2f}")
            print(f"Product Wholesale Price: {current_data['wholesale_price']:.2f}")
            print(f"Product Wholesale Threshold: {current_data['wholesale_threshold']}")
            print(f"Product Low Stock Threshold: {current_threshold}")
            print(f"Product Image: {current_image or 'None'}")
            
            # 4. MUULIZE USER VALUES ZA KUSASISHA (KUTUMIA BATCH DATA KAMA DEFAULTS)
            print(f"\n{Colors.CYAN}📝 ENTER NEW VALUES (press Enter to keep current):{Colors.RESET}")
            
            # Batch-specific updates
            new_batch_quantity = self.validation_service.update_with_validation_int(
                f"Enter new batch quantity for {batch_number} (current: {batch_quantity})",
                batch_quantity,
                min_value=0
            )

            new_batch_buying_price = self.validation_service.update_with_validation_float(
                f"Enter new batch buying price for {batch_number} (current: {batch_buying_price:.2f})",
                batch_buying_price,
                min_value=0
            )

            # ✅ FIXED: Use validate_expiry_date function for expiry date
            new_batch_expiry = batch_expiry  # Default to current expiry
            while True:
                expiry_input = input(f"{Colors.BLUE}Enter new expiry date for {batch_number} (YYYY-MM-DD, current: {batch_expiry or 'None'}): {Colors.RESET}").strip()
                
                if not expiry_input:  # User pressed Enter, keep current
                    new_batch_expiry = batch_expiry
                    break
                    
                # Validate the expiry date
                validation_result = self.validation_service.validate_expiry_date(expiry_input, batch_expiry)
                
                if not validation_result.is_valid:
                    print(f"{Colors.RED}❌ {validation_result.message}{Colors.RESET}")
                    continue
                
                if validation_result.message and "WARNING" in validation_result.message:
                    print(f"{Colors.YELLOW}⚠️  {validation_result.message}{Colors.RESET}")
                    confirm = input(f"{Colors.YELLOW}Are you sure you want to use this date? (yes/no): {Colors.RESET}").strip().lower()
                    if confirm != 'yes':
                        continue
                
                new_batch_expiry = validation_result.value
                print(f"{Colors.GREEN}✓ Date accepted: {new_batch_expiry}{Colors.RESET}")
                break

            # Product price updates (using current product data as defaults)
            new_retail_price = self.validation_service.update_with_validation_float(
                f"Enter new retail price (current: {current_data['retail_price']:.2f})",
                current_data['retail_price'],
                min_value=0
            )

            new_wholesale_price = self.validation_service.update_with_validation_float(
                f"Enter new wholesale price (current: {current_data['wholesale_price']:.2f})",
                current_data['wholesale_price'],
                min_value=0
            )

            # Validate wholesale vs retail price
            if new_wholesale_price > new_retail_price:
                print(f"{Colors.YELLOW}⚠️  WARNING: Wholesale price is higher than retail price{Colors.RESET}")
                confirm = input(f"{Colors.YELLOW}Are you sure? (yes/no): {Colors.RESET}").strip().lower()
                if confirm != 'yes':
                    print(f"{Colors.RED}Update cancelled{Colors.RESET}")
                    return

            new_wholesale_threshold = self.validation_service.update_with_validation_int(
                f"Enter new wholesale threshold (current: {current_data['wholesale_threshold']})",
                current_data['wholesale_threshold'],
                min_value=1
            )

            new_low_stock_threshold = self.validation_service.update_with_validation_int(
                f"Enter new low stock threshold (current: {current_threshold})",
                current_threshold,
                min_value=1
            )

            # Optional fields
            new_image_input = ask_image_file_dialog(product_name, "images")#input(f"{Colors.BLUE}Enter new image path (current: {current_image or 'None'}): {Colors.RESET}").strip()
            new_image =  new_image_input if new_image_input else current_image

            #sanitize_input(new_image_input) if new_image_input else current_image
            # 5. CALCULATE MARGINS FOR THE BATCH
            margin_data = self.cost_calculation_service.calculate_expected_margin(
                retail_price=new_retail_price,
                wholesale_price=new_wholesale_price,
                landed_cost=new_batch_buying_price,
                product_id=product_id
            )
            
            if margin_data:
                expected_margin = margin_data.expected_margin
                total_expected_profit = expected_margin * new_batch_quantity
            else:
                expected_margin = 0
                total_expected_profit = 0
            
            # 6. PERFORM ALL DATABASE UPDATES
            print(f"\n{Colors.CYAN}--- APPLYING CHANGES TO ALL TABLES ---{Colors.RESET}")
            
            # Calculate new total stock for products table
            total_stock_other_batches = sum(batch[2] for batch in batches if batch[0] != batch_id)
            new_total_stock = total_stock_other_batches + new_batch_quantity
            
            # UPDATE 1: stock_batches table
            print(f"{Colors.BLUE}Updating stock_batches table...{Colors.RESET}")
            batch_update = self.db_manager.execute_query(
                'inventory',
                """UPDATE stock_batches SET 
                    quantity = ?, 
                    buying_price = ?, 
                    expiry_date = ?,
                    expected_margin = ?, 
                    total_expected_profit = ?,
                    original_quantity = ?,
                    synced = 0
                   WHERE id = ?""",
                (new_batch_quantity, new_batch_buying_price, new_batch_expiry,
                 expected_margin, total_expected_profit,new_batch_quantity, batch_id)
            )
            
            if batch_update is None:
                print(f"{Colors.RED}❌ Failed to update stock_batches table{Colors.RESET}")
                return
            
            # UPDATE 2: products table
            print(f"{Colors.BLUE}Updating products table...{Colors.RESET}")
            product_update = self.db_manager.execute_query(
                'inventory',
                """UPDATE products SET 
                    stock_quantity = ?, 
                    low_stock_threshold = ?, 
                    image = ?, 
                    updated_at = datetime('now'),
                    synced = 0
                   WHERE id = ?""",
                (new_total_stock, new_low_stock_threshold, new_image, product_id)
            )
            
            if product_update is None:
                print(f"{Colors.RED}❌ Failed to update products table{Colors.RESET}")
                return
            
            # UPDATE 3: store_product_prices table
            print(f"{Colors.BLUE}Updating store_product_prices table...{Colors.RESET}")
            price_update = self.db_manager.execute_query(
                'inventory',
                """UPDATE store_product_prices SET 
                    retail_price = ?, 
                    wholesale_price = ?, 
                    wholesale_threshold = ?,
                    synced = 0
                   WHERE product_id = ? AND store_id = ?""",
                (new_retail_price, new_wholesale_price, new_wholesale_threshold, product_id, self.current_store.id)
            )
            
            if price_update is None:
                print(f"{Colors.RED}❌ Failed to update store_product_prices table{Colors.RESET}")
                return
            
            # 7. VERIFY ALL UPDATES WERE SUCCESSFUL
            if batch_update is not None and product_update is not None and price_update is not None:
                print(f"{Colors.GREEN}🎉 ALL UPDATES COMPLETED SUCCESSFULLY!{Colors.RESET}")
                
                print(f"\n{Colors.GREEN}📦 BATCH UPDATES:{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Batch: {batch_number}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ New Quantity: {new_batch_quantity}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ New Buying Price: {new_batch_buying_price:.2f}{Colors.RESET}")
                if new_batch_expiry:
                    print(f"{Colors.GREEN}  ✅ New Expiry Date: {new_batch_expiry}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Expected Margin: {expected_margin:.2f} per unit{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Total Expected Profit: {total_expected_profit:.2f}{Colors.RESET}")
                
                print(f"\n{Colors.GREEN}📊 PRODUCT UPDATES:{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Total Stock Quantity: {new_total_stock}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Low Stock Threshold: {new_low_stock_threshold}{Colors.RESET}")
                if new_image:
                    print(f"{Colors.GREEN}  ✅ Image: {new_image}{Colors.RESET}")
                
                print(f"\n{Colors.GREEN}💰 PRICE UPDATES:{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Retail Price: {new_retail_price:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Wholesale Price: {new_wholesale_price:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Wholesale Threshold: {new_wholesale_threshold}{Colors.RESET}")
                
                print(f"\n{Colors.GREEN}📈 STOCK CALCULATION:{Colors.RESET}")
                print(f"{Colors.GREEN}  • Previous batch quantity: {batch_quantity}{Colors.RESET}")
                print(f"{Colors.GREEN}  • New batch quantity: {new_batch_quantity}{Colors.RESET}")
                print(f"{Colors.GREEN}  • Other batches total: {total_stock_other_batches}{Colors.RESET}")
                print(f"{Colors.GREEN}  • New total stock: {new_total_stock}{Colors.RESET}")
            
            else:
                print(f"{Colors.RED}❌ Error: Some updates failed{Colors.RESET}")
                
        except ValueError as e:
            print(f"{Colors.RED}❌ Invalid input: {e}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}❌ Error during update: {e}{Colors.RESET}")
    
    def update_specific_batch(self, batches: List[Tuple], product_id: int, product_name: str) -> None:
        """Update specific stock batch with margin recalculation"""
        if not batches:
            print(f"{Colors.RED}❌ No active batches found for this product{Colors.RESET}")
            return
        
        print(f"\n{Colors.BLUE}=== UPDATE SPECIFIC STOCK BATCH ==={Colors.RESET}")
        print(f"Product: {product_name}")
        
        # Get current product prices for margin calculation
        current_prices = self.db_manager.execute_query(
            'inventory',
            "SELECT retail_price, wholesale_price, wholesale_threshold FROM store_product_prices WHERE product_id = ? AND store_id = ?",
            (product_id, self.current_store.id),
            fetch=True
        )
        
        if not current_prices:
            print(f"{Colors.RED}❌ Error: Price information not found{Colors.RESET}")
            return
        
        retail_price, wholesale_price, wholesale_threshold = current_prices[0]
        
        # Select batch to update
        print(f"{Colors.BLUE}Select batch to update:{Colors.RESET}")
        for i, (batch_id, batch_number, quantity, buying_price, expiry_date, is_active) in enumerate(batches, 1):
            expiry_display = expiry_date if expiry_date else "No expiry"
            print(f"{i}. {batch_number}: {quantity} units - Buying: {buying_price:.2f} - Expiry: {expiry_display}")
        
        try:
            batch_choice = int(input(f"{Colors.BLUE}Select batch (1-{len(batches)}): {Colors.RESET}").strip())
            if 1 <= batch_choice <= len(batches):
                batch_id, batch_number, current_quantity, current_buying, current_expiry, is_active = batches[batch_choice - 1]
                
                print(f"\n{Colors.CYAN}Updating Batch: {batch_number}{Colors.RESET}")
                print(f"{Colors.CYAN}Current: {current_quantity} units, Buying: {current_buying:.2f}, Expiry: {current_expiry or 'None'}{Colors.RESET}")
                print(f"{Colors.CYAN}Current Prices - Retail: {retail_price:.2f}, Wholesale: {wholesale_price:.2f}, Threshold: {wholesale_threshold}{Colors.RESET}")
                
                # Ask user what to update
                print(f"\n{Colors.BLUE}What would you like to update?{Colors.RESET}")
                print("1. Update quantity only")
                print("2. Update buying price only")
                print("3. Update expiry date only")
                print("4. Update retail and wholesale prices")
                
                update_option = int(input(f"{Colors.BLUE}Select option (1-4): {Colors.RESET}").strip())
                
                if update_option == 1:
                    # Update quantity only
                    new_quantity = self.validation_service.update_with_validation_int(
                        f"Enter new quantity for {batch_number} (current: {current_quantity})",
                        current_quantity,
                        min_value=0
                    )
                    new_buying_price = current_buying
                    new_expiry = current_expiry
                    new_retail_price = retail_price
                    new_wholesale_price = wholesale_price
                    new_wholesale_threshold = wholesale_threshold
                    
                elif update_option == 2:
                    # Update buying price only
                    new_quantity = current_quantity
                    new_buying_price = self.validation_service.update_with_validation_float(
                        f"Enter new buying price for {batch_number} (current: {current_buying})",
                        current_buying,
                        min_value=0
                    )
                    new_expiry = current_expiry
                    new_retail_price = retail_price
                    new_wholesale_price = wholesale_price
                    new_wholesale_threshold = wholesale_threshold
                    
                elif update_option == 3:
                    # ✅ FIXED: Update expiry date only using validate_expiry_date
                    new_quantity = current_quantity
                    new_buying_price = current_buying
                    
                    # Use validate_expiry_date function
                    new_expiry = current_expiry  # Default to current expiry
                    while True:
                        expiry_input = input(f"{Colors.BLUE}Enter new expiry date (YYYY-MM-DD, current: {current_expiry or 'None'}): {Colors.RESET}").strip()
                        
                        if not expiry_input:  # User pressed Enter, keep current
                            new_expiry = current_expiry
                            break
                            
                        # Validate the expiry date
                        validation_result = self.validation_service.validate_expiry_date(expiry_input, current_expiry)
                        
                        if not validation_result.is_valid:
                            print(f"{Colors.RED}❌ {validation_result.message}{Colors.RESET}")
                            continue
                        
                        if validation_result.message and "WARNING" in validation_result.message:
                            print(f"{Colors.YELLOW}⚠️  {validation_result.message}{Colors.RESET}")
                            confirm = input(f"{Colors.YELLOW}Are you sure you want to use this date? (yes/no): {Colors.RESET}").strip().lower()
                            if confirm != 'yes':
                                continue
                        
                        new_expiry = validation_result.value
                        print(f"{Colors.GREEN}✓ Date accepted: {new_expiry}{Colors.RESET}")
                        break
                    
                    new_retail_price = retail_price
                    new_wholesale_price = wholesale_price
                    new_wholesale_threshold = wholesale_threshold
                    
                elif update_option == 4:
                    # Update retail and wholesale prices only
                    new_quantity = current_quantity
                    new_buying_price = current_buying
                    new_expiry = current_expiry
                    new_retail_price = self.validation_service.update_with_validation_float(
                        f"Enter new retail price (current: {retail_price:.2f})",
                        retail_price,
                        min_value=0
                    )
                    new_wholesale_price = self.validation_service.update_with_validation_float(
                        f"Enter new wholesale price (current: {wholesale_price:.2f})",
                        wholesale_price,
                        min_value=0
                    )
                    new_wholesale_threshold = self.validation_service.update_with_validation_int(
                        f"Enter new wholesale threshold (current: {wholesale_threshold})",
                        wholesale_threshold,
                        min_value=1
                    )
                    
                    # Validate wholesale vs retail price
                    if new_wholesale_price > new_retail_price:
                        print(f"{Colors.YELLOW}⚠️  WARNING: Wholesale price is higher than retail price{Colors.RESET}")
                        confirm = input(f"{Colors.YELLOW}Are you sure? (yes/no): {Colors.RESET}").strip().lower()
                        if confirm != 'yes':
                            print(f"{Colors.RED}Update cancelled{Colors.RESET}")
                            return
                    
                else:
                    print(f"{Colors.RED}Invalid update option{Colors.RESET}")
                    return
                
                # RECALCULATE MARGINS with new buying price
                margin_data = self.cost_calculation_service.calculate_expected_margin(
                    retail_price=new_retail_price,
                    wholesale_price=new_wholesale_price,
                    landed_cost=new_buying_price,
                    product_id=product_id
                )
                
                if margin_data:
                    expected_margin = margin_data.expected_margin
                    total_expected_profit = expected_margin * new_quantity
                else:
                    expected_margin = 0
                    total_expected_profit = 0
                
                # Update batch with new margin data
                update_result = self.db_manager.execute_query(
                    'inventory',
                    """UPDATE stock_batches SET 
                        quantity = ?, buying_price = ?, expiry_date = ?,
                        expected_margin = ?, total_expected_profit = ?,original_quantity= ?,synced = 0
                       WHERE id = ?""",
                    (new_quantity, new_buying_price, new_expiry,
                     expected_margin, total_expected_profit,new_quantity, batch_id)
                )
                
                if update_result is not None:
                    print(f"{Colors.GREEN}✅ Batch '{batch_number}' updated successfully!{Colors.RESET}")
                    print(f"{Colors.GREEN}  ✅ New Quantity: {new_quantity}{Colors.RESET}")
                    print(f"{Colors.GREEN}  ✅ New Buying Price: {new_buying_price:.2f}{Colors.RESET}")
                    if new_expiry:
                        print(f"{Colors.GREEN}  ✅ New Expiry Date: {new_expiry}{Colors.RESET}")
                    print(f"{Colors.GREEN}  ✅ New Expected Margin: {expected_margin:.2f} per unit{Colors.RESET}")
                    print(f"{Colors.GREEN}  ✅ Total Expected Profit: {total_expected_profit:.2f}{Colors.RESET}")
                    
                    # Recalculate total stock and update products table
                    total_stock = sum(batch[2] for batch in batches if batch[0] != batch_id) + new_quantity
                    stock_update = self.db_manager.execute_query(
                        'inventory',
                        """UPDATE products SET 
                            stock_quantity = ?,
                            synced = 0
                           WHERE id = ?""",
                        (total_stock, product_id)
                    )
                    
                    if stock_update is not None:
                        print(f"{Colors.GREEN}  ✅ Total stock updated to: {total_stock}{Colors.RESET}")
                    else:
                        print(f"{Colors.YELLOW}⚠ Warning: Could not update total stock quantity{Colors.RESET}")
                    
                    # Update store_product_prices table if prices changed
                    if update_option == 4:
                        price_update = self.db_manager.execute_query(
                            'inventory',
                            """UPDATE store_product_prices SET 
                                retail_price = ?, 
                                wholesale_price = ?, 
                                wholesale_threshold = ?,
                                synced = 0
                               WHERE product_id = ? AND store_id = ?""",
                            (new_retail_price, new_wholesale_price, new_wholesale_threshold, product_id, self.current_store.id)
                        )
                        
                        if price_update is not None:
                            print(f"{Colors.GREEN}  ✅ Retail Price updated to: {new_retail_price:.2f}{Colors.RESET}")
                            print(f"{Colors.GREEN}  ✅ Wholesale Price updated to: {new_wholesale_price:.2f}{Colors.RESET}")
                            print(f"{Colors.GREEN}  ✅ Wholesale Threshold updated to: {new_wholesale_threshold}{Colors.RESET}")
                        else:
                            print(f"{Colors.YELLOW}⚠ Warning: Could not update price information{Colors.RESET}")
                    
                else:
                    print(f"{Colors.RED}❌ Error: Failed to update batch{Colors.RESET}")
                    
            else:
                print(f"{Colors.RED}❌ Invalid batch selection{Colors.RESET}")
                
        except ValueError:
            print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")
    
    
    def update_all_product_info(self, product_id: int, product_name: str, current_stock: int, 
                          current_threshold: int, current_image: str, batches: List[Tuple]) -> None:
        """
        Complete product overhaul with batch management ONLY - NO BASIC PRODUCT INFO
        ✅ SASA: Inatumia DATA YA BATCH ILIYOCHAGULIWA kwa kila kitu
        """
        print(f"\n{Colors.BLUE}=== COMPLETE BATCH OVERHAUL ==={Colors.RESET}")
        print(f"Product: {product_name}")
        
        try:
            # 1. BATCH SELECTION - IWE KWANZA KABISA!
            print(f"\n{Colors.CYAN}--- SELECT BATCH TO UPDATE ---{Colors.RESET}")
            
            if not batches:
                print(f"{Colors.YELLOW}No active batches found. Creating new batch...{Colors.RESET}")
                self.create_new_batch_for_product(product_id, product_name, current_stock)
                return
            
            print(f"{Colors.YELLOW}Found {len(batches)} active batches{Colors.RESET}")
            
            # KUULIZA MOJA KWA MOJA: NI BATCH GANI UNATAKA KUTUMIA?
            print(f"{Colors.BLUE}Available batches:{Colors.RESET}")
            for i, (batch_id, batch_number, quantity, buying_price, expiry_date, is_active) in enumerate(batches, 1):
                expiry_display = expiry_date if expiry_date else "No expiry"
                print(f"{i}. {batch_number}: {quantity} units - Buying: {buying_price:.2f} - Expiry: {expiry_display}")
            
            batch_choice = int(input(f"{Colors.BLUE}Select batch to update (1-{len(batches)}): {Colors.RESET}").strip())
            if not (1 <= batch_choice <= len(batches)):
                print(f"{Colors.RED}❌ Invalid batch selection{Colors.RESET}")
                return
            
            batch_id, batch_number, current_quantity, current_buying, current_expiry, is_active = batches[batch_choice - 1]
            
            # ✅ 2. GET CURRENT DATA WITH SELECTED BATCH
            current_data = self.product_service.get_current_product_data(
                product_id, self.current_store.id, batch_id  # ✅ Tumia batch_id iliyochaguliwa
            )
            
            if not current_data:
                print(f"{Colors.RED}❌ Could not retrieve current product data for selected batch{Colors.RESET}")
                return

            print(f"\n{Colors.CYAN}=== COMPLETE UPDATE FOR BATCH: {batch_number} ==={Colors.RESET}")
            print(f"{Colors.CYAN}Current: {current_quantity} units, Buying: {current_buying:.2f}, Expiry: {current_expiry or 'None'}{Colors.RESET}")
            
            # ✅ 3. UPDATE ALL BATCH INFORMATION - KILA KITU!
            print(f"\n{Colors.BLUE}--- ENTER NEW BATCH DETAILS ---{Colors.RESET}")
            
            # Quantity
            new_quantity = self.validation_service.update_with_validation_int(
                f"Enter new quantity for {batch_number} (current: {current_quantity})",
                current_quantity,
                min_value=0
            )
            
            # # Buying Price
            # new_buying_price = self.validation_service.update_with_validation_float(
            #     f"Enter new buying price for {batch_number} (current: {current_buying:.2f})",
            #     current_buying,
            #     min_value=0
            # )
            
            # Expiry Date
            new_expiry = current_expiry  # Default to current expiry
            while True:
                expiry_input = input(f"{Colors.BLUE}Enter new expiry date (YYYY-MM-DD, current: {current_expiry or 'None'}): {Colors.RESET}").strip()
                
                if not expiry_input:  # User pressed Enter, keep current
                    new_expiry = current_expiry
                    break
                    
                # Validate the expiry date
                validation_result = self.validation_service.validate_expiry_date(expiry_input, current_expiry)
                
                if not validation_result.is_valid:
                    print(f"{Colors.RED}❌ {validation_result.message}{Colors.RESET}")
                    continue
                
                if validation_result.message and "WARNING" in validation_result.message:
                    print(f"{Colors.YELLOW}⚠️  {validation_result.message}{Colors.RESET}")
                    confirm = input(f"{Colors.YELLOW}Are you sure you want to use this date? (yes/no): {Colors.RESET}").strip().lower()
                    if confirm != 'yes':
                        continue
                
                new_expiry = validation_result.value
                print(f"{Colors.GREEN}✓ Date accepted: {new_expiry}{Colors.RESET}")
                break
            
            # ✅ 4. UPDATE PRODUCT PRICES & COSTS - WITH SELECTED BATCH DATA
            print(f"\n{Colors.CYAN}--- UPDATE PRODUCT PRICES & COSTS ---{Colors.RESET}")
            
            # Get comprehensive new costs WITH SELECTED BATCH DATA
            costs = self.product_service.get_comprehensive_product_costs(
                product_id, product_name, 
                is_largest_unit=True, 
                current_data=current_data,  # ✅ Hii data ina selected batch info
                selected_batch_id=batch_id   # ✅ Tumia batch iliyochaguliwa
            )
            if not costs:
                return
            
            # ✅ 5. CALCULATE EXPECTED MARGIN WITH NEW DATA
            expected_margin = costs.expected_margin
            total_expected_profit = expected_margin * new_quantity
            new_buying_price = costs.buying_price 
            
            # ✅ 6. PERFORM ALL DATABASE UPDATES
            print(f"\n{Colors.CYAN}--- APPLYING ALL CHANGES ---{Colors.RESET}")
            
            # Update batch in database
            update_result = self.db_manager.execute_query(
                'inventory',
                """UPDATE stock_batches SET 
                    quantity = ?, buying_price = ?, expiry_date = ?,
                    expected_margin = ?, total_expected_profit = ?,
                    shipping_cost = ?, handling_cost = ?,
                    received_date = datetime('now'),
                    original_quantity= ?,
                    synced = 0
                WHERE id = ?""",
                (new_quantity, new_buying_price, new_expiry,
                expected_margin, total_expected_profit,
                costs.shipping_cost, costs.handling_cost,new_quantity,
                batch_id)
            )
            
            if update_result is not None:
                print(f"{Colors.GREEN}✓ Batch '{batch_number}' updated successfully!{Colors.RESET}")
                
                # ✅ 7. UPDATE TOTAL STOCK QUANTITY
                total_stock = self.calculate_total_stock_with_selected_batch(
                    product_id, batch_id, new_quantity
                )
                
                stock_update = self.db_manager.execute_query(
                    'inventory',
                    """UPDATE products SET 
                        stock_quantity = ?, 
                        low_stock_threshold = ?,
                        updated_at = datetime('now'),
                        synced = 0  -- Mark as not synced
                    WHERE id = ?""",
                    (total_stock, current_threshold, product_id)
                )
                
                if stock_update is not None:
                    print(f"{Colors.GREEN}✓ Total stock updated to: {total_stock}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}⚠ Warning: Could not update total stock quantity{Colors.RESET}")
                
                # ✅ 8. UPDATE STORE PRODUCT PRICES
                price_update = self.db_manager.execute_query(
                    'inventory',
                    """UPDATE store_product_prices SET 
                        retail_price = ?, 
                        wholesale_price = ?, 
                        wholesale_threshold = ?,
                        synced = 0  -- Mark as not synced
                    WHERE product_id = ? AND store_id = ?""",
                    (costs.retail_price, costs.wholesale_price, costs.wholesale_threshold, 
                    product_id, self.current_store.id)
                )
                
                if price_update is not None:
                    print(f"{Colors.GREEN}✓ Retail price updated to: {costs.retail_price:.2f}{Colors.RESET}")
                    print(f"{Colors.GREEN}✓ Wholesale price updated to: {costs.wholesale_price:.2f}{Colors.RESET}")
                    print(f"{Colors.GREEN}✓ Wholesale threshold updated to: {costs.wholesale_threshold}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}⚠ Warning: Could not update price information{Colors.RESET}")
                
                # ✅ 9. UPDATE PRODUCT IMAGE IF PROVIDED
                if current_image: 
                    new_image_input = ask_image_file_dialog(product_name, "images")#input(f"{Colors.BLUE}Enter new image path (current: {current_image}): {Colors.RESET}").strip()
                    if new_image_input:
                        new_image = new_image_input
                        image_update = self.db_manager.execute_query(
                            'inventory',
                            "UPDATE products SET image = ? WHERE id = ?",
                            (new_image, product_id)
                        )
                        if image_update is not None:
                            print(f"{Colors.GREEN}✓ Image updated to: {new_image}{Colors.RESET}")
                
                # ✅ 10. FINAL SUMMARY
                print(f"\n{Colors.GREEN}🎉 COMPLETE BATCH OVERHAUL SUCCESSFUL!{Colors.RESET}")
                
                print(f"\n{Colors.GREEN}📦 BATCH UPDATES:{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Batch: {batch_number}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ New Quantity: {new_quantity}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ New Buying Price: {new_buying_price:.2f}{Colors.RESET}")
                if new_expiry:
                    print(f"{Colors.GREEN}  ✅ New Expiry Date: {new_expiry}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Shipping Cost: {costs.shipping_cost:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Handling Cost: {costs.handling_cost:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Landed Cost: {costs.landed_cost:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Expected Margin: {expected_margin:.2f} per unit{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Total Expected Profit: {total_expected_profit:.2f}{Colors.RESET}")
                
                print(f"\n{Colors.GREEN}💰 PRICE UPDATES:{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Retail Price: {costs.retail_price:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Wholesale Price: {costs.wholesale_price:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Wholesale Threshold: {costs.wholesale_threshold}{Colors.RESET}")
                
                print(f"\n{Colors.GREEN}📊 STOCK SUMMARY:{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Total Product Stock: {total_stock}{Colors.RESET}")
                print(f"{Colors.GREEN}  ✅ Low Stock Threshold: {current_threshold}{Colors.RESET}")
                
            else:
                print(f"{Colors.RED}❌ Error updating batch '{batch_number}'{Colors.RESET}")
                return
                    
        except ValueError:
            print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")
            return
        except Exception as e:
            print(f"{Colors.RED}❌ Error during complete update: {e}{Colors.RESET}")

    def calculate_total_stock_with_selected_batch(self, product_id: int, selected_batch_id: int, new_quantity: int) -> int:
        """
        Calculate total stock by summing all batches except selected one + new quantity
        ✅ SASA: Inahesabu stock total kwa kujumlisha batches zote isipokuwa ile iliyochaguliwa
        """
        try:
            # Get sum of all other active batches
            other_batches = self.db_manager.execute_query(
                'inventory',
                "SELECT SUM(quantity) FROM stock_batches WHERE product_id = ? AND id != ? AND is_active = 1",
                (product_id, selected_batch_id),
                fetch=True
            )
            
            other_batches_total = other_batches[0][0] if other_batches and other_batches[0][0] is not None else 0
            total_stock = other_batches_total + new_quantity
            
            print(f"{Colors.CYAN}📊 Stock Calculation: {other_batches_total} (other batches) + {new_quantity} (selected batch) = {total_stock}{Colors.RESET}")
            
            return total_stock
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Warning calculating total stock: {e}{Colors.RESET}")
            return new_quantity

    def create_new_batch_for_product(self, product_id: int, product_name: str, current_stock: int) -> None:
        """
        Create new batch when no active batches exist
        ✅ SASA: Inatengeneza batch mpya kwa bidhaa
        """
        try:
            # Get product code
            product_code_result = self.db_manager.execute_query(
                'inventory',
                "SELECT product_code FROM products WHERE id = ?",
                (product_id,),
                fetch=True
            )
            product_code = product_code_result[0][0] if product_code_result else f"PROD_{product_id}"
            
            # Get current data for defaults
            current_data = self.product_service.get_current_product_data(product_id, self.current_store.id)
            
            # Get costs for new batch
            costs = self.product_service.get_comprehensive_product_costs(
                product_id, product_name, is_largest_unit=True, current_data=current_data
            )
            if not costs:
                return
                
            batch_id = self.product_service.create_stock_batch(
                product_id, product_code, self.current_store, costs, current_stock, None
            )
            
            if batch_id:
                print(f"{Colors.GREEN}✓ New batch created successfully!{Colors.RESET}")
                print(f"{Colors.GREEN}  Initial Stock: {current_stock} units{Colors.RESET}")
                print(f"{Colors.GREEN}  Buying Price: {costs.buying_price:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}  Retail Price: {costs.retail_price:.2f}{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Failed to create new batch{Colors.RESET}")
                
        except Exception as e:
            print(f"{Colors.RED}❌ Error creating new batch: {e}{Colors.RESET}")
    
    def insert_single_product(self) -> None:
        """
        Enhanced single product insertion with better validation
        """
        print(f"\n{Colors.BLUE}=== ADD SINGLE PRODUCT ==={Colors.RESET}")
        
        # Get product name with validation
        while True:
            base_name = input(f"{Colors.BLUE}Enter product name: {Colors.RESET}").strip()
            if not base_name:
                print(f"{Colors.RED}❌ Product name cannot be empty{Colors.RESET}")
                continue
            break
        
        # Select unit type
        unit_type = self.product_service.select_unit_type()
        product_name = f"{base_name}({unit_type})"
        
        # Check if product exists
        existing_product = self.product_service.check_product_exists(product_name, self.current_store.id)
        if existing_product:
            self.handle_existing_product_flow(
                (existing_product.id, existing_product.name, existing_product.stock_quantity, 
                 existing_product.low_stock_threshold, existing_product.image),
                product_name
            )
            return
        
        print(f"\n{Colors.GREEN}✓ New product detected: {product_name}{Colors.RESET}")
        
        # Get comprehensive cost data
        costs = self.product_service.get_comprehensive_product_costs(None, product_name, is_largest_unit=True)
        if not costs:
            return
        
        # Get additional details with validation
        stock_quantity = self.validation_service.validate_stock_quantity(
            "Enter stock quantity (default 0)",
            0
        )

        low_stock_threshold = self.validation_service.validate_low_stock_threshold(
            "Enter low stock threshold (default 5)",
            5,
            stock_quantity
        )

        image = ask_image_file_dialog(base_name, "images")#sanitize_input(input(f"{Colors.BLUE}Enter image path (optional): {Colors.RESET}").strip()) or None
        
        # Generate product code
        sequence_number = self.product_service.get_next_sequence_number(self.current_store.store_code)
        product_code = self.product_service.generate_product_code(self.current_store.store_code, sequence_number)
        
        print(f"{Colors.BLUE}Generated product code: {product_code}{Colors.RESET}")
        
        # Insert product
        product_id = self.db_manager.execute_query(
            'inventory',
            """INSERT INTO products (
                product_code, name, store_id, store_code, sequence_number, 
                stock_quantity, image, low_stock_threshold, 
                parent_product_id, relation_to_parent, unit, big_unit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)""",
            (product_code, product_name, self.current_store.id, self.current_store.store_code, sequence_number,
             stock_quantity, image, low_stock_threshold, unit_type, unit_type)
        )
        
        if not product_id:
            print(f"{Colors.RED}Error: Failed to insert product{Colors.RESET}")
            return
        
        # Create stock batch with expiry date
        batch_id = self.product_service.create_stock_batch(product_id, product_code, self.current_store, costs, stock_quantity, None)
        
        # Insert price information
        price_id = self.db_manager.execute_query(
            'inventory',
            """INSERT INTO store_product_prices (
                store_id, product_id, product_code, retail_price, 
                wholesale_price, wholesale_threshold
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            (self.current_store.id, product_id, product_code, costs.retail_price, 
             costs.wholesale_price, costs.wholesale_threshold)
        )

        if price_id and batch_id:
            print(f"{Colors.GREEN}✓ Product '{product_name}' added successfully with FIFO tracking!{Colors.RESET}")
            print(f"{Colors.GREEN}  Product Code: {product_code}{Colors.RESET}")
            print(f"{Colors.GREEN}  Stock: {stock_quantity}, Low Stock Threshold: {low_stock_threshold}{Colors.RESET}")
            print(f"{Colors.GREEN}  Retail Price: {costs.retail_price}, Wholesale Price: {costs.wholesale_price}{Colors.RESET}")
            print(f"{Colors.GREEN}  Buying Price: {costs.buying_price}, Landed Cost: {costs.landed_cost:.2f}{Colors.RESET}")
            print(f"{Colors.GREEN}  Expected Margin: {costs.expected_margin:.2f} per unit{Colors.RESET}")
            
            # Check and warn if stock is below threshold
            if stock_quantity < low_stock_threshold:
                print(f"{Colors.YELLOW}⚠ Warning: Product stock is below low stock threshold!{Colors.RESET}")
        else:
            print(f"{Colors.RED}Error: Failed to add complete product information{Colors.RESET}")
    
    def insert_multi_unit_product(self) -> None:
        """
        INSERT MULTI-UNIT PRODUCT WITH BATCH SYSTEM
        - Start with largest unit (e.g., Carton)
        - Add smaller units using relationships  
        - Calculate stock for smaller units based on relationship with largest unit
        - Insert each unit into database as separate product
        - Create stock batch for each unit
        - Set prices in store_product_prices
        """
        print(f"\n{Colors.BLUE}=== ADD MULTI-UNIT PRODUCT ==={Colors.RESET}")
        
        # Get base product name
        base_name = input(f"{Colors.BLUE}Enter base product name (e.g., Sugar): {Colors.RESET}").strip()
        if not base_name:
            print(f"{Colors.RED}Error: Base product name cannot be empty{Colors.RESET}")
            return
        
        # Check if product exists
        existing_units = self.db_manager.execute_query(
            'inventory',
            "SELECT id, name, stock_quantity FROM products WHERE LOWER(name) LIKE LOWER(?) AND store_id = ?",
            (f"%{base_name}%", self.current_store.id),
            fetch=True
        )
        
        if existing_units:
            print(f"{Colors.YELLOW}Found existing units for {base_name}{Colors.RESET}")
            self.update_multi_unit_product(base_name, existing_units)
            return
        
        print(f"\n{Colors.GREEN}✓ New multi-unit product: {base_name}{Colors.RESET}")
        
        # ✅ STEP 1: START WITH LARGEST UNIT
        units = []
        relations = []
        
        print(f"\n{Colors.BLUE}Let's configure the units for this product.{Colors.RESET}")
        
        try:
            # Configure the largest unit (e.g., Carton)
            largest_unit_name = input(f"{Colors.BLUE}Enter the name of the LARGEST unit (e.g., Carton): {Colors.RESET}").strip()
            if not largest_unit_name:
                print(f"{Colors.RED}Error: Unit name cannot be empty{Colors.RESET}")
                return
            
            # Get comprehensive costs for the largest unit
            print(f"\n{Colors.CYAN}Cost data for {largest_unit_name}:{Colors.RESET}")
            costs = self.product_service.get_comprehensive_product_costs(None, largest_unit_name, is_largest_unit=True)
            if not costs:
                return

            # ✅ LOOP FOR STOCK QUANTITY VALIDATION
            stock_quantity = 0
            while True:
                try:
                    stock_input = input(f"{Colors.BLUE}Enter stock quantity for '{largest_unit_name}': {Colors.RESET}").strip()
                    
                    if not stock_input:
                        print(f"{Colors.RED}❌ Stock quantity cannot be empty{Colors.RESET}")
                        continue
                        
                    stock_quantity = int(stock_input)
                    
                    if stock_quantity < 0:
                        print(f"{Colors.RED}❌ Stock quantity cannot be negative{Colors.RESET}")
                        continue
                        
                    if stock_quantity == 0:
                        confirm = input(f"{Colors.YELLOW}⚠️  Stock quantity is 0. Are you sure? (yes/no): {Colors.RESET}").strip().lower()
                        if confirm != 'yes':
                            print(f"{Colors.BLUE}Please enter stock quantity again{Colors.RESET}")
                            continue
                    
                    break  # Exit loop if input is valid
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")

            product_name = f"{base_name}({largest_unit_name})"
            image = ask_image_file_dialog(product_name, "images")#sanitize_input(input(f"{Colors.BLUE}Enter image path (optional): {Colors.RESET}").strip()) or None
            
            # Add largest unit to the units list
            units.append({
                "name": f"{base_name}({largest_unit_name})",
                "unit_name": largest_unit_name,
                "retail_price": costs.retail_price,
                "wholesale_price": costs.wholesale_price,
                "wholesale_threshold": costs.wholesale_threshold,
                "buying_price": costs.buying_price,
                "shipping_cost": costs.shipping_cost,
                "handling_cost": costs.handling_cost,
                "landed_cost": costs.landed_cost,
                "expected_margin": costs.expected_margin,
                "stock_quantity": stock_quantity,
                "image": image,
                "parent_id": None,
                "relation": None
            })
            
            print(f"{Colors.GREEN}✓ Added largest unit: {largest_unit_name}{Colors.RESET}")
            
        except ValueError as e:
            print(f"{Colors.RED}Invalid input: Please enter valid numbers. Error: {e}{Colors.RESET}")
            return
        
        # ✅ STEP 2: ADD SMALLER UNITS WITH RELATIONSHIPS
        current_unit_index = 0
        while True:
            add_more = input(f"\n{Colors.BLUE}Add smaller unit than '{units[current_unit_index]['unit_name']}'? (yes/no): {Colors.RESET}").strip().lower()
            if add_more != 'yes':
                break
                
            try:
                smaller_unit_name = input(f"{Colors.BLUE}Enter smaller unit name: {Colors.RESET}").strip()
                if not smaller_unit_name:
                    print(f"{Colors.RED}❌ Unit name cannot be empty{Colors.RESET}")
                    continue
                
                # Get relationship
                relation = int(input(f"{Colors.BLUE}How many '{smaller_unit_name}' in 1 '{units[current_unit_index]['unit_name']}'? {Colors.RESET}").strip())
                if relation <= 0:
                    print(f"{Colors.RED}❌ Relation must be positive{Colors.RESET}")
                    continue
                
                # Prepare parent data for cost calculation
                parent_data = {
                    'relation': relation,
                    'shipping_cost': units[current_unit_index]["shipping_cost"],
                    'handling_cost': units[current_unit_index]["handling_cost"],
                    'buying_price': units[current_unit_index]["buying_price"]
                }
                
                # Get costs for smaller unit
                print(f"\n{Colors.CYAN}Cost data for {smaller_unit_name}:{Colors.RESET}")
                smaller_costs = self.product_service.get_comprehensive_product_costs(None, smaller_unit_name, is_largest_unit=False, parent_unit_data=parent_data)
                if not smaller_costs:
                    continue
                    
                # Validate inputs for smaller unit
                if smaller_costs.retail_price <= 0 or smaller_costs.wholesale_price <= 0 or smaller_costs.wholesale_threshold <= 0:
                    print(f"{Colors.RED}Error: Prices and threshold must be positive numbers{Colors.RESET}")
                    continue
                    
                if smaller_costs.retail_price < smaller_costs.wholesale_price:
                    print(f"{Colors.RED}Error: Retail price cannot be less than wholesale price{Colors.RESET}")
                    continue
                
                # Add smaller unit to the units list
                units.append({
                    "name": f"{base_name}({smaller_unit_name})",
                    "unit_name": smaller_unit_name,
                    "retail_price": smaller_costs.retail_price,
                    "wholesale_price": smaller_costs.wholesale_price,
                    "wholesale_threshold": smaller_costs.wholesale_threshold,
                    "buying_price": smaller_costs.buying_price,
                    "shipping_cost": smaller_costs.shipping_cost,
                    "handling_cost": smaller_costs.handling_cost,
                    "landed_cost": smaller_costs.landed_cost,
                    "expected_margin": smaller_costs.expected_margin,
                    "stock_quantity": None,  # Will be calculated based on parent unit
                    "image": None,
                    "parent_id": None,  # Will be set during insertion
                    "relation": relation
                })
                relations.append(relation)
                
                print(f"{Colors.GREEN}✓ Added unit: {smaller_unit_name} (1 {units[current_unit_index]['unit_name']} = {relation} {smaller_unit_name}){Colors.RESET}")
                current_unit_index += 1
                
            except ValueError as e:
                print(f"{Colors.RED}Invalid input: Please enter valid numbers. Error: {e}{Colors.RESET}")
                continue
        
        # Display final structure
        print(f"\n{Colors.CYAN}📦 FINAL UNITS STRUCTURE:{Colors.RESET}")
        for i, unit in enumerate(units):
            if i == 0:
                print(f"{Colors.CYAN}  • {unit['unit_name']} (Largest unit){Colors.RESET}")
            else:
                parent_unit = units[i-1]['unit_name']
                print(f"{Colors.CYAN}  • {unit['unit_name']} (1 {parent_unit} = {relations[i-1]} {unit['unit_name']}){Colors.RESET}")
        
        # ✅ STEP 3: GET LOW STOCK THRESHOLD FOR LARGEST UNIT WITH SMART VALIDATION
        current_stock = units[0]["stock_quantity"]

        low_stock_threshold = 0
        while True:
            try:
                threshold_input = input(f"{Colors.BLUE}Enter low stock threshold for largest unit '{units[0]['name']}' (current stock: {current_stock}, default 5): {Colors.RESET}").strip()
                
                if not threshold_input:
                    low_stock_threshold = 5  # Default value
                else:
                    low_stock_threshold = int(threshold_input)
                
                # ✅ VALIDATION 1: Cannot be negative or zero
                if low_stock_threshold <= 0:
                    print(f"{Colors.RED}❌ Low stock threshold must be greater than 0{Colors.RESET}")
                    continue
                
                # ✅ VALIDATION 2: Cannot be greater than current stock
                if low_stock_threshold > current_stock:
                    print(f"{Colors.RED}❌ WARNING: Low stock threshold ({low_stock_threshold}) is GREATER than current stock ({current_stock}){Colors.RESET}")
                    print(f"{Colors.RED}   This means the product will always be considered 'low stock'{Colors.RESET}")
                    
                    confirm = input(f"{Colors.YELLOW}Are you sure you want to continue? (yes/no): {Colors.RESET}").strip().lower()
                    if confirm != 'yes':
                        print(f"{Colors.BLUE}Please enter a new low stock threshold{Colors.RESET}")
                        continue
                
                # ✅ VALIDATION 3: Warning if threshold is too high relative to stock
                if low_stock_threshold > (current_stock * 0.8):  # More than 80% of stock
                    print(f"{Colors.YELLOW}⚠️  NOTE: Low stock threshold is very high ({low_stock_threshold}/{current_stock} = {low_stock_threshold/current_stock*100:.1f}% of total stock){Colors.RESET}")
                    confirm = input(f"{Colors.YELLOW}Continue with this threshold? (yes/no): {Colors.RESET}").strip().lower()
                    if confirm != 'yes':
                        print(f"{Colors.BLUE}Please enter a new low stock threshold{Colors.RESET}")
                        continue
                
                # ✅ VALIDATION 4: Warning if threshold is too low
                if low_stock_threshold < (current_stock * 0.1) and current_stock > 10:  # Less than 10% of stock
                    print(f"{Colors.YELLOW}⚠️  NOTE: Low stock threshold is very low ({low_stock_threshold}/{current_stock} = {low_stock_threshold/current_stock*100:.1f}% of total stock){Colors.RESET}")
                    print(f"{Colors.YELLOW}   You might run out of stock without warning{Colors.RESET}")
                    confirm = input(f"{Colors.YELLOW}Continue with this threshold? (yes/no): {Colors.RESET}").strip().lower()
                    if confirm != 'yes':
                        print(f"{Colors.BLUE}Please enter a new low stock threshold{Colors.RESET}")
                        continue
                
                break  # Exit loop if all validations pass
                
            except ValueError:
                print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.RED}❌ Error: {e}{Colors.RESET}")

        print(f"{Colors.GREEN}✓ Low stock threshold set to: {low_stock_threshold}{Colors.RESET}")

        # ✅ STEP 4: CALCULATE STOCK QUANTITIES FOR SMALLER UNITS
        current_stock = units[0]["stock_quantity"]
        
        for i in range(1, len(units)):
            current_stock = current_stock * relations[i-1]
            units[i]["stock_quantity"] = current_stock
        
        # ✅ STEP 5: CREATE PRODUCTS AND THEIR RELATIONSHIPS IN DATABASE
        product_ids = {}
        sequence_numbers = []  # ✅ Hifadhi sequence numbers zote
        current_threshold = low_stock_threshold
        
        print(f"\n{Colors.BLUE}=== CREATING PRODUCT ENTRIES ==={Colors.RESET}")
        
        for i, unit in enumerate(units):
            # Generate product code
            sequence_number = self.product_service.get_next_sequence_number(self.current_store.store_code)
            product_code = self.product_service.generate_product_code(self.current_store.store_code, sequence_number)
            
            sequence_numbers.append(sequence_number)  # ✅ Hifadhi kwa matumizi baadaye
            
            # Determine parent product ID and relation
            parent_id = None
            relation_to_parent = None
            if i > 0:
                parent_unit_name = units[i-1]["unit_name"]
                parent_id = product_ids.get(parent_unit_name)
                relation_to_parent = relations[i-1]
            
            # Determine big_unit (always the largest unit)
            big_unit = units[0]["unit_name"]
            
            # Insert product
            product_id = self.db_manager.execute_query(
                'inventory',
                """INSERT INTO products (
                    product_code, name, store_id, store_code, sequence_number,
                    stock_quantity, low_stock_threshold, parent_product_id, relation_to_parent,
                    unit, big_unit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (product_code, unit["name"], self.current_store.id, self.current_store.store_code, sequence_number,
                 unit["stock_quantity"], current_threshold, parent_id, relation_to_parent,
                 unit["unit_name"], big_unit)
            )
            
            if not product_id:
                print(f"{Colors.RED}❌ Failed to create product: {unit['name']}{Colors.RESET}")
                return None
            
            product_ids[unit["unit_name"]] = product_id
            print(f"{Colors.GREEN}✓ Created product: {unit['name']} (ID: {product_id}, Code: {product_code}){Colors.RESET}")
            
            # Set default prices
            self.db_manager.execute_query(
                'inventory',
                """INSERT INTO store_product_prices (
                    store_id, product_id, product_code, retail_price, 
                    wholesale_price, wholesale_threshold
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (self.current_store.id, product_id, product_code, unit["retail_price"], 
                 unit["wholesale_price"], unit["wholesale_threshold"])
            )
            
            # Calculate low stock threshold for next smaller unit
            if i < len(units) - 1:
                current_threshold = current_threshold * relations[i]
        
        # ✅ STEP 6: CREATE BATCHES FOR ALL UNITS (FIXED VERSION)
        print(f"\n{Colors.BLUE}=== CREATING STOCK BATCHES ==={Colors.RESET}")
        
        batch_count = 0
        for i, unit in enumerate(units):
            product_id = product_ids[unit["unit_name"]]
            
            # ✅ TUMA SEQUENCE NUMBER YA UNIT HUSIKA (SIO YA MWISHO TU)
            product_code = self.product_service.generate_product_code(self.current_store.store_code, sequence_numbers[i])
            
            print(f"{Colors.CYAN}Creating batch for: {unit['name']} (ID: {product_id}, Code: {product_code}){Colors.RESET}")
            
            # Prepare batch data
            batch_data = ProductCosts(
                buying_price=unit["buying_price"],
                retail_price=unit["retail_price"],
                wholesale_price=unit["wholesale_price"],
                wholesale_threshold=unit["wholesale_threshold"],
                shipping_cost=unit["shipping_cost"],
                handling_cost=unit["handling_cost"],
                expected_margin=unit["expected_margin"]
            )
            
            batch_id = self.product_service.create_stock_batch(
                product_id, 
                product_code,
                self.current_store, 
                batch_data, 
                unit["stock_quantity"], 
                None
            )
            
            if batch_id:
                batch_count += 1
                print(f"{Colors.GREEN}✓ Created batch for: {unit['name']} ({unit['stock_quantity']} units){Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ Failed to create batch for: {unit['name']}{Colors.RESET}")
        
        # ✅ FINAL SUMMARY
        if batch_count == len(units):
            print(f"\n{Colors.GREEN}🎉 Multi-unit product '{base_name}' created successfully!{Colors.RESET}")
            print(f"{Colors.GREEN}   Units: {[unit['unit_name'] for unit in units]}{Colors.RESET}")
            print(f"{Colors.GREEN}   Total batches created: {batch_count}{Colors.RESET}")
            
            # Display hierarchical summary
            print(f"\n{Colors.CYAN}📦 PRODUCT HIERARCHY SUMMARY:{Colors.RESET}")
            for i, unit in enumerate(units):
                if i == 0:
                    print(f"{Colors.CYAN}  • {unit['name']} (Stock: {unit['stock_quantity']}, Threshold: {low_stock_threshold}){Colors.RESET}")
                else:
                    print(f"{Colors.CYAN}  • {unit['name']} (1 {units[i-1]['name']} = {relations[i-1]} {unit['unit_name']}, Stock: {unit['stock_quantity']}){Colors.RESET}")
            
            return True
        else:
            print(f"\n{Colors.YELLOW}⚠ Some batches failed to create{Colors.RESET}")
            print(f"{Colors.YELLOW}   Created {batch_count} out of {len(units)} batches{Colors.RESET}")
            return False
    
    def update_multi_unit_product(self, base_name: str, existing_units: List[Tuple]) -> None:
        """
        Handle update of multi-unit product with batch management
        """
        print(f"\n{Colors.BLUE}=== UPDATE MULTI-UNIT PRODUCT ==={Colors.RESET}")
        print(f"Product: {base_name}")
        print(f"Found {len(existing_units)} existing units")
        
        # Show hierarchy information
        hierarchy = self.product_service.get_product_hierarchy(base_name, self.current_store.id)
  
        def print_hierarchy(node, level=0):
            indent = "  " * level

     
            relation = f" (Relation: {node.get('relation')})" if node.get('relation') else ""

          
            print(f"{Colors.CYAN}{indent}└── {node['name']}{relation}{Colors.RESET}")

          
            child_indent_base = "  " * (level + 2)  

            for child in node.get('children', []):
            
                next_level = level + 1 if level == 0 else level + 2
                print_hierarchy(child, next_level)

        if hierarchy:
            print(f"\n{Colors.CYAN}📦 PRODUCT HIERARCHY:{Colors.RESET}")
            print(f"{Colors.CYAN}{hierarchy['name']}{Colors.RESET}")  # root bila alama
            for child in hierarchy.get('children', []):
                print_hierarchy(child, level=1)


        
        print(f"\n{Colors.BLUE}Update Options:{Colors.RESET}")
        print("1. 🔄 Add New Batch (All Units)")
        print("2. ➕ Add New Unit to Structure") 
        print("3. 📊 Update All Information (Stock, Prices, Costs)")
        print("4. ❌ Cancel")
        
        try:
            choice = int(input(f"{Colors.BLUE}Select option (1-4): {Colors.RESET}").strip())
            
            if choice == 1:
                # Add new batch to all units - FIX: Handle variable tuple size
                formatted_units = []
                for unit in existing_units:
                    unit_id = unit[0]
                    unit_name = unit[1]
                    # Get additional data if needed
                    relation_result = self.db_manager.execute_query(
                        'inventory',
                        "SELECT relation_to_parent FROM products WHERE id = ?",
                        (unit_id,),
                        fetch=True
                    )
                    relation = relation_result[0][0] if relation_result and relation_result[0][0] is not None else 1
                    formatted_units.append((unit_id, unit_name, relation))
                
                self.add_multi_unit_batch(existing_units[0][0], base_name, formatted_units)
            elif choice == 2:
                self.add_unit_to_existing_structure(existing_units, base_name)
            elif choice == 3:
                self.update_all_multi_units_comprehensive(existing_units, base_name)
            elif choice == 4:
                print(f"{Colors.YELLOW}Update cancelled{Colors.RESET}")
            else:
                print(f"{Colors.RED}Invalid option{Colors.RESET}")
                
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number{Colors.RESET}")
    
    def add_unit_to_existing_structure(self, existing_units: List[Tuple], base_name: str) -> None:
        """Add new unit (either smaller or larger) to existing product structure with validation, cost logic, and transactions."""
        print(f"\n{Colors.BLUE}Adding new unit to {base_name}{Colors.RESET}")
        
        try:
            # ✅ Start transaction
            self.db_manager.begin('inventory')

            # 0️⃣ Check existing units
            if not existing_units:
                print(f"{Colors.RED}❌ No existing units found for {base_name}{Colors.RESET}")
                self.db_manager.rollback('inventory')
                return

            # 1️⃣ NEW UNIT NAME
            while True:
                new_unit_name = input(f"{Colors.BLUE}Enter name for new unit: {Colors.RESET}").strip()
                if not new_unit_name:
                    print(f"{Colors.RED}❌ Unit name cannot be empty{Colors.RESET}")
                    continue

                duplicate = self.db_manager.execute_query(
                    'inventory',
                    "SELECT id FROM products WHERE LOWER(name)=LOWER(?) AND store_id=?",
                    (f"{base_name}({new_unit_name})", self.current_store.id),
                    fetch=True
                )
                if duplicate:
                    print(f"{Colors.RED}❌ '{new_unit_name}' already exists under {base_name}{Colors.RESET}")
                    continue
                break

            # 2️⃣ SHOW EXISTING UNITS
            print(f"\n{Colors.CYAN}Existing units:{Colors.RESET}")
            for i, unit in enumerate(existing_units, 1):
                print(f"{i}. {unit[1]} (Stock: {unit[2] if len(unit) > 2 else 0})")

            # 3️⃣ SELECT RELATED UNIT
            while True:
                try:
                    choice = int(input(f"{Colors.BLUE}Select related unit (1-{len(existing_units)}): {Colors.RESET}").strip())
                    if 1 <= choice <= len(existing_units):
                        break
                    print(f"{Colors.RED}❌ Invalid selection{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Enter a valid number{Colors.RESET}")

            related_id, related_name, related_stock = existing_units[choice - 1][:3]

            # 4️⃣ RELATION TYPE
            print(f"\n{Colors.CYAN}1. Smaller (child)\n2. Larger (parent){Colors.RESET}")
            while True:
                try:
                    rel_type = int(input(f"{Colors.BLUE}Select type (1/2): {Colors.RESET}").strip())
                    if rel_type in [1, 2]:
                        break
                    print(f"{Colors.RED}❌ Must be 1 or 2{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Invalid input{Colors.RESET}")

            # 5️⃣ RELATION VALUE
            while True:
                try:
                    if rel_type == 1:
                        relation = int(input(f"{Colors.BLUE}How many '{new_unit_name}' in 1 '{related_name}'? {Colors.RESET}"))
                        relation_desc = f"1 {related_name} = {relation} {new_unit_name}"
                    else:
                        relation = int(input(f"{Colors.BLUE}How many '{related_name}' in 1 '{new_unit_name}'? {Colors.RESET}"))
                        relation_desc = f"1 {new_unit_name} = {relation} {related_name}"
                    if relation > 0:
                        break
                    print(f"{Colors.RED}❌ Must be positive{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Invalid number{Colors.RESET}")

            # 6️⃣ STOCK INPUT
            while True:
                raw_stock = input(f"{Colors.BLUE}Enter stock quantity for {new_unit_name} (Enter=0): {Colors.RESET}").strip()
                if not raw_stock:
                    new_stock = 0
                    break
                try:
                    new_stock = int(raw_stock)
                    if new_stock >= 0:
                        break
                    print(f"{Colors.RED}❌ Stock cannot be negative{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")

            # 7️⃣ LOW STOCK THRESHOLD
            while True:
                raw_threshold = input(f"{Colors.BLUE}Enter low stock threshold for {new_unit_name} (Enter=10): {Colors.RESET}").strip()
                if not raw_threshold:
                    low_stock_threshold = 10
                    break
                try:
                    low_stock_threshold = int(raw_threshold)
                    if low_stock_threshold >= 0:
                        break
                    print(f"{Colors.RED}❌ Threshold cannot be negative{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")

            # 8️⃣ COST INPUTS
            print(f"\n{Colors.CYAN}--- Cost Details for {new_unit_name} ---{Colors.RESET}")
            
            # Buying Price
            while True:
                try:
                    buying_input = input(f"{Colors.BLUE}Enter buying price for {base_name}({new_unit_name}): {Colors.RESET}").strip()
                    if not buying_input:
                        print(f"{Colors.RED}❌ Buying price is required{Colors.RESET}")
                        continue
                    buying = float(buying_input)
                    if buying >= 0:
                        break
                    print(f"{Colors.RED}❌ Buying price cannot be negative{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid amount{Colors.RESET}")

            # Retail Price
            while True:
                try:
                    retail_input = input(f"{Colors.BLUE}Enter retail price for {base_name}({new_unit_name}): {Colors.RESET}").strip()
                    if not retail_input:
                        print(f"{Colors.RED}❌ Retail price is required{Colors.RESET}")
                        continue
                    retail = float(retail_input)
                    if retail >= 0:
                        break
                    print(f"{Colors.RED}❌ Retail price cannot be negative{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid amount{Colors.RESET}")

            # Wholesale Price
            while True:
                try:
                    wholesale_input = input(f"{Colors.BLUE}Enter wholesale price for {base_name}({new_unit_name}): {Colors.RESET}").strip()
                    if not wholesale_input:
                        print(f"{Colors.RED}❌ Wholesale price is required{Colors.RESET}")
                        continue
                    wholesale = float(wholesale_input)
                    if wholesale >= 0:
                        break
                    print(f"{Colors.RED}❌ Wholesale price cannot be negative{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid amount{Colors.RESET}")

            # Wholesale Threshold
            while True:
                try:
                    threshold_input = input(f"{Colors.BLUE}Enter wholesale quantity threshold for {base_name}({new_unit_name}) (Enter=3): {Colors.RESET}").strip()
                    if not threshold_input:
                        wholesale_threshold = 3
                        break
                    wholesale_threshold = int(threshold_input)
                    if wholesale_threshold > 0:
                        break
                    print(f"{Colors.RED}❌ Threshold must be positive{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")

            # Shipping Cost
            while True:
                try:
                    shipping_input = input(f"{Colors.BLUE}Enter shipping cost for {base_name}({new_unit_name}) (Enter=0): {Colors.RESET}").strip()
                    if not shipping_input:
                        shipping = 0.0
                        break
                    shipping = float(shipping_input)
                    if shipping >= 0:
                        break
                    print(f"{Colors.RED}❌ Shipping cost cannot be negative{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid amount{Colors.RESET}")

            # Handling Cost
            while True:
                try:
                    handling_input = input(f"{Colors.BLUE}Enter handling cost for {base_name}({new_unit_name}) (Enter=0): {Colors.RESET}").strip()
                    if not handling_input:
                        handling = 0.0
                        break
                    handling = float(handling_input)
                    if handling >= 0:
                        break
                    print(f"{Colors.RED}❌ Handling cost cannot be negative{Colors.RESET}")
                except ValueError:
                    print(f"{Colors.RED}❌ Please enter a valid amount{Colors.RESET}")

            # 9️⃣ EXPIRY DATE (Optional)
            expiry_date = None
            while True:
                expiry_input = input(f"{Colors.BLUE}Enter expiry date for {base_name}({new_unit_name}) (YYYY-MM-DD or Enter for none): {Colors.RESET}").strip()
                if not expiry_input:
                    break
                try:
                    # Validate date format
                    datetime.datetime.strptime(expiry_input, '%Y-%m-%d')
                    expiry_date = expiry_input
                    break
                except ValueError:
                    print(f"{Colors.RED}❌ Invalid date format. Use YYYY-MM-DD{Colors.RESET}")

            # 🔟 PRODUCT CODE
            seq = self.product_service.get_next_sequence_number(self.current_store.store_code)
            pcode = self.product_service.generate_product_code(self.current_store.store_code, seq)
            full_name = f"{base_name}({new_unit_name})"

            # 1️⃣1️⃣ INSERT PRODUCT
            parent_id = related_id if rel_type == 1 else None
            relation_to_parent = relation if rel_type == 1 else None

            cursor = self.db_manager.execute_query(
                'inventory',
                """INSERT INTO products (
                    product_code, name, store_id, store_code, sequence_number,
                    stock_quantity, low_stock_threshold, parent_product_id, relation_to_parent,
                    unit, big_unit, created_at, updated_at     
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
                (pcode, full_name, self.current_store.id, self.current_store.store_code, seq,
                new_stock, low_stock_threshold, parent_id, relation_to_parent,
                new_unit_name, base_name)
            )

            new_unit_id = getattr(cursor, "lastrowid", None)
            if not new_unit_id:
                result = self.db_manager.execute_query(
                    'inventory',
                    "SELECT id FROM products WHERE product_code = ? AND store_id = ?",
                    (pcode, self.current_store.id),
                    fetch=True
                )
                new_unit_id = result[0][0] if result else None

            if not new_unit_id:
                raise Exception("Failed to insert new unit - could not retrieve ID")

            if rel_type == 2:  # update related if new is parent
                self.db_manager.execute_query(
                    'inventory',
                    "UPDATE products SET parent_product_id=?, relation_to_parent=? WHERE id=?",
                    (new_unit_id, relation, related_id)
                )

            # 1️⃣2️⃣ ADD PRICE + STOCK
            self.db_manager.execute_query(
                'inventory',
                """INSERT INTO store_product_prices (
                    store_id, product_id, product_code, retail_price, wholesale_price, wholesale_threshold, synced
                ) VALUES (?, ?, ?, ?, ?, ?, 0)""",
                (self.current_store.id, new_unit_id, pcode, retail, wholesale, wholesale_threshold)
            )

            if new_stock > 0:
                landed = round(buying + shipping + handling, 2)
                margin = round(retail - landed, 2)
                total_profit = margin * new_stock

                now = datetime.now()

                batch_num = f"BATCH_{now.strftime('%Y%m%d_%H%M%S')}"

                self.db_manager.execute_query(
                    'inventory',
                    """INSERT INTO stock_batches (
                        product_id, product_code, store_id, store_code, batch_number, quantity, 
                        buying_price, shipping_cost, handling_cost, expected_margin, 
                        total_expected_profit, received_date, expiry_date,original_quantity, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?,?, 1)""",
                    (new_unit_id, pcode, self.current_store.id, self.current_store.store_code, 
                    batch_num, new_stock, buying, shipping, handling,
                    margin, total_profit, expiry_date, new_stock)
                )

            # ✅ COMMIT TRANSACTION
            self.db_manager.commit('inventory')

            print(f"\n{Colors.GREEN}✅ Added {full_name}{Colors.RESET}")
            print(f"{Colors.GREEN}  Code: {pcode}{Colors.RESET}")
            print(f"{Colors.GREEN}  Relation: {relation_desc}{Colors.RESET}")
            print(f"{Colors.GREEN}  Stock: {new_stock}{Colors.RESET}")
            print(f"{Colors.GREEN}  Low Stock Threshold: {low_stock_threshold}{Colors.RESET}")
            print(f"{Colors.GREEN}  Costs → Buying: {buying:.2f}, Shipping: {shipping:.2f}, Handling: {handling:.2f}{Colors.RESET}")
            print(f"{Colors.GREEN}  Prices → Retail: {retail:.2f}, Wholesale: {wholesale:.2f}{Colors.RESET}")
            if expiry_date:
                print(f"{Colors.GREEN}  Expiry Date: {expiry_date}{Colors.RESET}")

        except Exception as e:
            try:
                self.db_manager.rollback('inventory')
            except Exception as rollback_error:
                print(f"{Colors.YELLOW}⚠️ Rollback warning: {rollback_error}{Colors.RESET}")
            print(f"{Colors.RED}❌ Error adding unit: {e}{Colors.RESET}")

    def update_all_multi_units_comprehensive(self, existing_units: List[Tuple], base_name: str) -> None:
        """
        COMPREHENSIVE UPDATE FOR ALL UNITS - BATCH-DRIVEN DEFAULTS ✅
        Supports:
        - Root batch selection
        - Default propagation to children (buying, shipping, handling, expiry)
        - Manual input overrides
        - Per-unit stock updates
        - Sync to products, store_product_prices, and stock_batches
        """
        print(f"\n{Colors.BLUE}=== COMPREHENSIVE UPDATE FOR ALL UNITS ==={Colors.RESET}")
        print(f"Product: {base_name}")

        try:
            # ✅ 1. START TRANSACTION
            self.db_manager.begin('inventory')

            # ✅ 2. GET PRODUCT HIERARCHY
            hierarchy = self.product_service.get_product_hierarchy(base_name, self.current_store.id)
            if not hierarchy:
                print(f"{Colors.RED}❌ Could not retrieve product hierarchy{Colors.RESET}")
                self.db_manager.rollback('inventory')
                return

            # ✅ 3. FLATTEN HIERARCHY INTO ORDERED LIST
            def get_units_in_order(node, units_list=None, level=0):
                if units_list is None:
                    units_list = []
                units_list.append({
                    'id': node['id'],
                    'name': node['name'],
                    'unit': node.get('unit', ''),
                    'relation': node.get('relation', 1),
                    'parent_id': node.get('parent_id'),
                    'level': level
                })
                for child in node.get('children', []):
                    get_units_in_order(child, units_list, level + 1)
                return units_list

            ordered_units = get_units_in_order(hierarchy)

            # ✅ 4. DISPLAY HIERARCHY CLEARLY
            print(f"\n{Colors.CYAN}📦 PRODUCT HIERARCHY:{Colors.RESET}")
            def print_hierarchy(node, level=0):
                indent = "    " * level
                rel = f" [1:{node.get('relation', 1)}]" if level > 0 else ""
                print(f"{Colors.CYAN}{indent}{'└──' if level>0 else '🏠'} {node['name']} ({node.get('unit','unit')}){rel}{Colors.RESET}")
                for child in node.get('children', []):
                    print_hierarchy(child, level + 1)
            print_hierarchy(hierarchy)

            # ✅ 5. ROOT UNIT & BATCH SELECTION
            root_unit = ordered_units[0]
            root_unit_id, root_unit_name = root_unit['id'], root_unit['name']

            root_batches = self.db_manager.execute_query(
                'inventory',
                """SELECT id, batch_number, quantity, buying_price, shipping_cost, handling_cost,
                        expiry_date, landed_cost, expected_margin
                FROM stock_batches WHERE product_id=? AND is_active=1
                ORDER BY received_date ASC""",
                (root_unit_id,), fetch=True
            )

            selected_root_batch = None
            if root_batches:
                print(f"\n{Colors.YELLOW}--- SELECT ROOT BATCH FOR {root_unit_name} ---{Colors.RESET}")
                for i, b in enumerate(root_batches, 1):
                    expiry_display = b[6] if b[6] else "No expiry"
                    print(f"{i}. {b[1]} | Stock: {b[2]} | Cost: {b[3]:.2f} | Expires: {expiry_display}")
                
                try:
                    choice = input(f"{Colors.BLUE}Select batch (1-{len(root_batches)}): {Colors.RESET}").strip()
                    if choice:
                        batch_index = int(choice)
                        if 1 <= batch_index <= len(root_batches):
                            selected_root_batch = root_batches[batch_index - 1]
                            print(f"{Colors.GREEN}✓ Selected: {selected_root_batch[1]}{Colors.RESET}")
                        else:
                            selected_root_batch = root_batches[0]
                            print(f"{Colors.YELLOW}⚠ Invalid choice, using first batch{Colors.RESET}")
                    else:
                        selected_root_batch = root_batches[0]
                        print(f"{Colors.YELLOW}⚠ No selection, using first batch{Colors.RESET}")
                except ValueError:
                    selected_root_batch = root_batches[0]
                    print(f"{Colors.YELLOW}⚠ Invalid input, using first batch{Colors.RESET}")
            else:
                print(f"{Colors.RED}❌ No active batches found for {root_unit_name}{Colors.RESET}")
                self.db_manager.rollback('inventory')
                return

            # ✅ 6. PREPARE BATCH DEFAULTS
            batch_id, batch_number, batch_qty, batch_buying, batch_shipping, batch_handling, batch_expiry, batch_landed, batch_margin = selected_root_batch
            
            root_defaults = {
                'batch_id': batch_id,
                'batch_number': batch_number,
                'buying_price': batch_buying,
                'shipping_cost': batch_shipping,
                'handling_cost': batch_handling,
                'quantity': batch_qty,
                'expiry_date': batch_expiry,
                'landed_cost': batch_landed,
                'expected_margin': batch_margin
            }

            # ✅ 7. PROPAGATE DEFAULTS TO CHILDREN (WITH BETTER LOGIC)
            unit_defaults = {root_unit_id: root_defaults}
            
            for unit in ordered_units[1:]:
                parent_id = unit.get('parent_id')
                relation = unit.get('relation', 1)
                
                if parent_id and parent_id in unit_defaults:
                    parent_defaults = unit_defaults[parent_id]
                    
                    # ✅ FIXED: Calculate child defaults based on parent relation
                    unit_defaults[unit['id']] = {
                        'batch_id': None,  # Children have their own batches
                        'batch_number': f"CHILD_{unit['id']}",
                        'buying_price': parent_defaults['buying_price'] / relation,
                        'shipping_cost': parent_defaults['shipping_cost'] / relation,
                        'handling_cost': parent_defaults['handling_cost'] / relation,
                        'quantity': parent_defaults['quantity'] * relation,  # This might need adjustment
                        'expiry_date': parent_defaults['expiry_date'],
                        'landed_cost': (parent_defaults['buying_price'] + parent_defaults['shipping_cost'] + parent_defaults['handling_cost']) / relation,
                        'expected_margin': 0  # Will be calculated later
                    }

            # ✅ 8. UPDATE EACH UNIT
            success_count = 0
            for unit in ordered_units:
                unit_id, unit_name = unit['id'], unit['name']
                is_root_unit = (unit_id == root_unit_id)
                
                print(f"\n{Colors.YELLOW}--- UPDATING: {unit_name} ({'ROOT UNIT' if is_root_unit else 'CHILD UNIT'}) ---{Colors.RESET}")

                # ✅ GET CURRENT DATA FOR COMPARISON
                current_data = self.product_service.get_current_product_data(unit_id, self.current_store.id)
                if not current_data:
                    print(f"{Colors.RED}❌ Failed to get current data for {unit_name}{Colors.RESET}")
                    continue

                # ✅ DISPLAY CURRENT VS DEFAULT
                defaults = unit_defaults.get(unit_id, {})
                current_stock = current_data['stock_quantity']
                default_stock = defaults.get('quantity', current_stock)
                
                print(f"{Colors.CYAN}📊 CURRENT DATA:{Colors.RESET}")
                print(f"{Colors.CYAN}  Stock: {current_stock} | Retail: {current_data['retail_price']:.2f} | Wholesale: {current_data['wholesale_price']:.2f}{Colors.RESET}")
                
                if defaults:
                    print(f"{Colors.CYAN}💡 BATCH DEFAULTS: Stock={defaults.get('quantity')}, Buy={defaults.get('buying_price', 0):.2f}, Ship={defaults.get('shipping_cost', 0):.2f}{Colors.RESET}")

                # ✅ STOCK INPUT WITH VALIDATION
                while True:
                    stock_input = input(f"{Colors.BLUE}Enter stock for {unit_name} (default: {default_stock}): {Colors.RESET}").strip()
                    if not stock_input:
                        new_stock = default_stock
                        break
                    try:
                        new_stock = int(stock_input)
                        if new_stock >= 0:
                            break
                        else:
                            print(f"{Colors.RED}❌ Stock cannot be negative{Colors.RESET}")
                    except ValueError:
                        print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")

                # ✅ LOW STOCK THRESHOLD
                new_threshold = self.validation_service.update_with_validation_int(
                    f"Enter low stock threshold (current: {current_data['low_stock_threshold']})",
                    current_data['low_stock_threshold'], 
                    min_value=1
                )

                # ✅ IMAGE (optional)
                clean_name = f"{base_name}({unit_name})"
                new_image_input = ask_image_file_dialog(clean_name, "images")#input(f"{Colors.BLUE}Image path (current: {current_data['image'] or 'None'}): {Colors.RESET}").strip()
                new_image = new_image_input if new_image_input else current_data['image']

                # ✅ COST CALCULATION WITH BATCH DEFAULTS
                costs = self.product_service.get_comprehensive_product_costs(
                    product_id=unit_id,
                    unit_name=unit_name,
                    is_largest_unit=is_root_unit,
                    current_data=current_data,
                    selected_batch_id=selected_root_batch[0] if is_root_unit else None,
                    batch_defaults=defaults
                )

                if not costs:
                    print(f"{Colors.RED}❌ Cost calculation failed for {unit_name}{Colors.RESET}")
                    continue

                # ✅ EXPIRY DATE (Root unit only)
                new_expiry = defaults.get('expiry_date')
                if is_root_unit:
                    expiry_input = input(f"{Colors.BLUE}Expiry date (YYYY-MM-DD, default: {new_expiry or 'None'}): {Colors.RESET}").strip()
                    if expiry_input:
                        validation_result = self.validation_service.validate_expiry_date(expiry_input, new_expiry)
                        if validation_result.is_valid:
                            new_expiry = validation_result.value
                            print(f"{Colors.GREEN}✓ Expiry updated: {new_expiry}{Colors.RESET}")
                        else:
                            print(f"{Colors.RED}❌ {validation_result.message}{Colors.RESET}")
                    # If no input, keep the default expiry

                # === DATABASE UPDATES ===
                try:
                    # 🔄 UPDATE 1: Products table (REMOVE cost-related columns)
                    self.db_manager.execute_query(
                        'inventory',
                        """UPDATE products SET stock_quantity=?, low_stock_threshold=?, image=?, updated_at=datetime('now')
                        WHERE id=?""",
                        (new_stock, new_threshold, new_image, unit_id)  # Removed cost parameters
                    )

                    # 🔄 UPDATE 2: Prices table
                    self.db_manager.execute_query(
                        'inventory',
                        """UPDATE store_product_prices SET retail_price=?, wholesale_price=?, wholesale_threshold=?, synced=0
                        WHERE product_id=? AND store_id=?""",
                        (costs.retail_price, costs.wholesale_price, costs.wholesale_threshold, unit_id, self.current_store.id)
                    )

                    # 🔄 UPDATE 3: Stock batches table
                    # Calculate margin and profit
                    margin_data = self.cost_calculation_service.calculate_expected_margin(
                        retail_price=costs.retail_price,
                        wholesale_price=costs.wholesale_price,
                        landed_cost=costs.landed_cost,
                        product_id=unit_id
                    )
                    expected_margin = margin_data.expected_margin if margin_data else 0
                    total_expected_profit = expected_margin * new_stock

                    # Update or create batch for this unit
                    existing_batches = self.db_manager.execute_query(
                        'inventory',
                        "SELECT id FROM stock_batches WHERE product_id=? AND is_active=1",
                        (unit_id,), fetch=True
                    )

                    if existing_batches:
                        # Update existing batch
                        self.db_manager.execute_query(
                            'inventory',
                            """UPDATE stock_batches SET quantity=?, buying_price=?, shipping_cost=?, handling_cost=?,
                                expiry_date=?, expected_margin=?, total_expected_profit=?, received_date=datetime('now'),original_quantity=?
                            WHERE product_id=? AND is_active=1""",
                            (new_stock, costs.buying_price, costs.shipping_cost, costs.handling_cost,
                                new_expiry, expected_margin, total_expected_profit,new_stock, unit_id)
                        )
                    else:
                        # Create new batch if none exists
                        batch_num = f"BATCH_{unit_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        self.db_manager.execute_query(
                            'inventory',
                            """INSERT INTO stock_batches 
                            (product_id, product_code, store_id, store_code, batch_number, quantity, buying_price, shipping_cost, handling_cost,
                                expiry_date, expected_margin, total_expected_profit, received_date,original_quantity, is_active)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'),?, 1)""",
                            (unit_id, current_data['product_code'], self.current_store.id, self.current_store.store_code, 
                            batch_num, new_stock, costs.buying_price, costs.shipping_cost, costs.handling_cost,
                                new_expiry, expected_margin, total_expected_profit, new_stock)
                        )
                
                    print(f"{Colors.GREEN}✅ {unit_name} updated successfully!{Colors.RESET}")
                    if new_stock != current_stock:
                        print(f"{Colors.GREEN}  Stock: {current_stock} → {new_stock}{Colors.RESET}")
                    success_count += 1

                except Exception as e:
                    print(f"{Colors.RED}❌ Database error updating {unit_name}: {e}{Colors.RESET}")
                    continue

            # ✅ 9. COMMIT TRANSACTION
            self.db_manager.commit('inventory')

            # ✅ 10. SUMMARY
            print(f"\n{Colors.CYAN}=== UPDATE COMPLETE ==={Colors.RESET}")
            if success_count == len(ordered_units):
                print(f"{Colors.GREEN}🎉 SUCCESS: All {success_count} units updated successfully{Colors.RESET}")
                print(f"{Colors.GREEN}📊 All tables (products, prices, batches) are now synchronized{Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}⚠ PARTIAL: {success_count}/{len(ordered_units)} units updated{Colors.RESET}")

        except Exception as e:
            print(f"{Colors.RED}❌ Transaction failed: {e}{Colors.RESET}")
            self.db_manager.rollback('inventory')
            
    def run(self) -> None:
        """Main application loop"""
        print(f"{Colors.BLUE}=== ENHANCED MANUAL DATA INSERTION TOOL ==={Colors.RESET}")
        print(f"{Colors.BLUE}This tool helps you insert products into existing stores{Colors.RESET}")
        print(f"{Colors.BLUE}With comprehensive cost tracking and FIFO management{Colors.RESET}")
        print(f"{Colors.BLUE}Using consolidated inventory.db database{Colors.RESET}")
        
        if not self.initialize_services():
            print(f"{Colors.RED}Cannot continue without database connection{Colors.RESET}")
            return
        
        if not self.check_database_health():
            print(f"{Colors.RED}Database health check failed. Please check your data{Colors.RESET}")
            return
        
        while True:
            print(f"\n{Colors.BLUE}=== MAIN MENU ==={Colors.RESET}")
            if self.current_store:
                print(f"{Colors.GREEN}Current Store: {self.current_store.name} ({self.current_store.store_code}){Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}No store selected{Colors.RESET}")
            
            print("1. Select Store")
            print("2. Add Single Product")
            print("3. Add Multi-Unit Product")
            print("4. Exit")
            
            choice = input(f"\n{Colors.BLUE}Select option (1-4): {Colors.RESET}").strip()
            
            if choice == '1':
                store = self.store_service.select_store()
                if store:
                    self.current_store = store
            
            elif choice == '2':
                if not self.current_store:
                    print(f"{Colors.RED}Error: Please select a store first{Colors.RESET}")
                    continue
                self.insert_single_product()

            elif choice == '3':
                if not self.current_store:
                    print(f"{Colors.RED}Error: Please select a store first{Colors.RESET}")
                    continue
                self.insert_multi_unit_product()
            
            elif choice == '4':
                print(f"{Colors.GREEN}Thank you for using the Enhanced Manual Data Insertion Tool!{Colors.RESET}")
                break
            else:
                print(f"{Colors.RESET}Invalid option. Please choose between 1 and 4{Colors.RESET}")
        
        self.db_manager.close_all()

def main():
    """Main function - Entry point of the application"""
    app = DataInsertionApp()
    app.run()

if __name__ == "__main__":
    main()