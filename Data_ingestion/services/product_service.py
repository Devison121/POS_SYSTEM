# product_service.py
# Product service for managing products

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from database.connection import DatabaseManager
from models.product import Product, ProductCosts, Store, StockBatch, UnitStructure, BatchData
from services.validation_service import ValidationService
from services.cost_calculation_service import CostCalculationService
from utils.color_output import Colors
from utils.helpers import sanitize_input


@dataclass
class ProductService:
    """Service for product-related operations"""
    db: DatabaseManager
    validation_service: ValidationService
    cost_calculation_service: CostCalculationService
    
    def get_next_sequence_number(self, store_code: str) -> int:
        """Get next sequence number for product in store"""
        try:
            result = self.db.execute_query(
                'inventory',
                "SELECT sequence_number FROM products WHERE store_code = ? ORDER BY sequence_number DESC LIMIT 1",
                (store_code,),
                fetch=True
            )
            return result[0][0] + 1 if result else 1
        except Exception as e:
            print(f"{Colors.YELLOW}Warning: Error getting sequence number, using default 1: {e}{Colors.RESET}")
            return 1
    
    def generate_product_code(self, store_code: str, sequence_number: int) -> str:
        """Generate product code in format: store_code_sequence with zero padding"""
        return f"{store_code}_{sequence_number:04d}"
    
    def check_product_exists(self, product_name: str, store_id: int) -> Optional[Product]:
        """Check if product already exists in store (case-insensitive)"""
        try:
            result = self.db.execute_query(
                'inventory',
                "SELECT id, name, stock_quantity, low_stock_threshold, image FROM products WHERE LOWER(name) = LOWER(?) AND store_id = ?",
                (product_name, store_id),
                fetch=True
            )
            
            if result:
                product_id, name, stock_quantity, low_stock_threshold, image = result[0]
                return Product(
                    id=product_id,
                    name=name,
                    stock_quantity=stock_quantity,
                    low_stock_threshold=low_stock_threshold,
                    image=image,
                    store_id=store_id
                )
            return None
        except Exception as e:
            print(f"{Colors.RED}Error checking product existence: {e}{Colors.RESET}")
            return None
    
    def get_current_product_data(self, product_id: int, store_id: int, selected_batch_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
            """
            Get current product data including prices and costs from database
            """
            try:
                # 1. GET BASIC PRODUCT INFO
                product_data = self.db.execute_query(
                    'inventory',
                    "SELECT name, stock_quantity, low_stock_threshold, image FROM products WHERE id = ?",
                    (product_id,),
                    fetch=True
                )
                
                if not product_data:
                    return None
                    
                name, stock_quantity, low_stock_threshold, image = product_data[0]
                
                # 2. GET CURRENT PRICES FROM store_product_prices
                price_data = self.db.execute_query(
                    'inventory',
                    "SELECT retail_price, wholesale_price, wholesale_threshold FROM store_product_prices WHERE product_id = ? AND store_id = ?",
                    (product_id, store_id),
                    fetch=True
                )
                
                retail_price, wholesale_price, wholesale_threshold = price_data[0] if price_data else (0, 0, 0)
                
                # 3. GET SELECTED BATCH DATA IF ANY
                if selected_batch_id:
                    batch_data = self.db.execute_query(
                        'inventory',
                        """SELECT buying_price, shipping_cost, handling_cost, quantity, batch_number, product_id
                        FROM stock_batches 
                        WHERE id = ? AND product_id = ? AND is_active = 1""",
                        (selected_batch_id, product_id),
                        fetch=True
                    )
                    # If not found for this product, the selected batch might belong to parent product.
                    # Try fetch by id only (allow parent batch to be used as source for child defaults).
                    if not batch_data:
                        batch_data = self.db.execute_query(
                            'inventory',
                            """SELECT buying_price, shipping_cost, handling_cost, quantity, batch_number, product_id
                            FROM stock_batches
                            WHERE id = ? AND is_active = 1""",
                            (selected_batch_id,),
                            fetch=True
                        )
                        if batch_data:
                            # mark that this batch comes from a different product (parent)
                            batch_from_parent = True
                        else:
                            batch_from_parent = False
                    else:
                        batch_from_parent = False
                else:

                    # If no batch selected, get latest active batch for this product
                    batch_data = self.db.execute_query(
                        'inventory',
                        """SELECT buying_price, shipping_cost, handling_cost, quantity, batch_number, product_id
                        FROM stock_batches 
                        WHERE product_id = ? AND is_active = 1 
                        ORDER BY received_date DESC LIMIT 1""",
                        (product_id,),
                        fetch=True
                    )
                    batch_from_parent = False

                if batch_data:
                    buying_price, shipping_cost, handling_cost, batch_quantity, batch_number, batch_product_id = batch_data[0]
                else:
                    buying_price, shipping_cost, handling_cost, batch_quantity, batch_number, batch_product_id = (0, 0, 0, 0, "N/A", None)

                # 4. CALCULATE LANDED COST
                landed_cost = (buying_price or 0) + (shipping_cost or 0) + (handling_cost or 0)
                
                return {
                    'name': name,
                    'stock_quantity': stock_quantity,
                    'low_stock_threshold': low_stock_threshold,
                    'image': image,
                    'retail_price': retail_price,
                    'wholesale_price': wholesale_price,
                    'wholesale_threshold': wholesale_threshold,
                    'buying_price': buying_price,
                    'shipping_cost': shipping_cost,
                    'handling_cost': handling_cost,
                    'landed_cost': landed_cost,
                    'batch_quantity': batch_quantity,
                    'batch_number': batch_number,
                    'selected_batch_id': selected_batch_id,
                    'batch_from_parent': batch_from_parent  # <-- added so flag is actually used / exported
                }
                
                
            except Exception as e:
                print(f"{Colors.YELLOW}⚠ Warning: Could not fetch current product data: {e}{Colors.RESET}")
                return None

    def get_product_batches(self, product_id: int) -> List[Tuple]:
            """
            Get ALL active batches for a product
            """
            try:
                batches = self.db.execute_query(
                    'inventory',
                    """SELECT id, batch_number, quantity, buying_price, shipping_cost, 
                            handling_cost, expiry_date, received_date
                    FROM stock_batches 
                    WHERE product_id = ? AND is_active = 1 
                    ORDER BY received_date ASC""",
                    (product_id,),
                    fetch=True
                )
                return batches or []
            except Exception as e:
                print(f"{Colors.YELLOW}⚠ Warning: Could not fetch product batches: {e}{Colors.RESET}")
                return []

    def select_batch_for_update(self, product_id: int, product_name: str) -> Optional[int]:
            """
            Let user select which batch to update
            """
            try:
                # Prefer batches of the largest unit (parent) if available
                target_product_id = product_id
                try:
                    hierarchy = self.get_product_hierarchy(product_name, self.current_store.id)
                    if hierarchy and hierarchy.get('id') and hierarchy.get('id') != product_id:
                        # Use parent product id so we show batches for the largest unit first
                        target_product_id = hierarchy['id']
                        product_name = hierarchy.get('name', product_name)
                        print(f"{Colors.CYAN}Showing batches for parent (largest) unit: {product_name}{Colors.RESET}")
                except Exception:
                    # If hierarchy lookup fails, fallback to given product_id
                    target_product_id = product_id

                batches = self.get_product_batches(target_product_id)
                
                
                if not batches:
                    print(f"{Colors.YELLOW}No active batches found for {product_name}{Colors.RESET}")
                    return None
                
                print(f"\n{Colors.CYAN}📦 SELECT BATCH TO UPDATE ==={Colors.RESET}")
                print(f"Product: {product_name}")
                print(f"Found {len(batches)} active batches:")
                
                for i, batch in enumerate(batches, 1):
                    batch_id, batch_number, quantity, buying_price, shipping_cost, handling_cost, expiry_date, received_date = batch
                    expiry_display = expiry_date if expiry_date else "No expiry"
                    print(f"{i}. {batch_number}: {quantity} units - Buying: {buying_price:.2f} - Expiry: {expiry_display}")
                
                while True:
                    try:
                        choice = input(f"\n{Colors.BLUE}Select batch to update (1-{len(batches)}): {Colors.RESET}").strip()
                        if not choice:
                            print(f"{Colors.YELLOW}Using the latest batch{Colors.RESET}")
                            return batches[-1][0]  # Return ID of latest batch
                        
                        choice_num = int(choice)
                        if 1 <= choice_num <= len(batches):
                            selected_batch_id = batches[choice_num - 1][0]
                            selected_batch_number = batches[choice_num - 1][1]
                            print(f"{Colors.GREEN}✓ Selected batch: {selected_batch_number}{Colors.RESET}")
                            return selected_batch_id
                        else:
                            print(f"{Colors.RED}Please select between 1 and {len(batches)}{Colors.RESET}")
                    except ValueError:
                        print(f"{Colors.RED}Please enter a valid number{Colors.RESET}")
                        
            except Exception as e:
                print(f"{Colors.RED}Error selecting batch: {e}{Colors.RESET}")
                return None
    
    def select_unit_type(self) -> str:
        """Let user select the unit type for the product"""
        print(f"\n{Colors.BLUE}=== SELECT UNIT TYPE ==={Colors.RESET}")
        print("1. Piece (e.g., 1 bottle, 1 item)")
        print("2. Kilogram (kg)")
        print("3. Gram (g)")
        print("4. Liter (L)")
        print("5. Milliliter (ml)")
        print("6. Pack")
        print("7. Carton")
        print("8. Other (custom)")
        
        unit_options = {
            '1': 'Piece',
            '2': 'Kilogram',
            '3': 'Gram', 
            '4': 'Liter',
            '5': 'Milliliter',
            '6': 'Pack',
            '7': 'Carton'
        }
        
        try:
            choice = input(f"\n{Colors.BLUE}Select unit type (1-8): {Colors.RESET}").strip()
            
            if choice in unit_options:
                return unit_options[choice]
            elif choice == '8':
                custom_unit = input(f"{Colors.BLUE}Enter custom unit name: {Colors.RESET}").strip()
                return custom_unit if custom_unit else 'Unit'
            else:
                print(f"{Colors.RED}Invalid selection. Using default 'Unit'{Colors.RESET}")
                return 'Unit'
                
        except Exception as e:
            print(f"{Colors.RED}Error selecting unit type: {e}{Colors.RESET}")
            return 'Unit'
            
    def get_comprehensive_product_costs(self, product_id: Optional[int] = None, unit_name: Optional[str] = None, 
                                is_largest_unit: bool = True, parent_unit_data: Optional[Dict] = None,
                                current_data: Optional[Dict] = None, selected_batch_id: Optional[int] = None,
                                batch_defaults: Optional[Dict] = None) -> Optional[ProductCosts]:  # ✅ ADDED batch_defaults
        
        def safe_value(value):
            """Ensure value is numeric (unwrap tuple if needed)."""
            if isinstance(value, tuple):
                return value[0] if value else 0
            return value or 0
        
        """
        Collect comprehensive cost information for a product with enhanced validation
        """
        if unit_name:
            print(f"\n{Colors.CYAN}=== COST DATA FOR {unit_name.upper()} ==={Colors.RESET}")
        
        # 1. GET CURRENT DATA WITH SELECTED BATCH
        if product_id and not current_data:
            current_data = self.get_current_product_data(product_id, self.current_store.id, selected_batch_id)
        
        # 2. DETERMINE SMART DEFAULTS - PRIORITIZE BATCH DEFAULTS IF PROVIDED
        smart_defaults = {}
        
        # FIRST PRIORITY: Use batch_defaults if provided
        if batch_defaults:
            smart_defaults = {
                'buying_price': batch_defaults.get('buying_price', 0),
                'retail_price': current_data.get('retail_price', 0) if current_data else 0,
                'wholesale_price': current_data.get('wholesale_price', 0) if current_data else 0,
                'wholesale_threshold': current_data.get('wholesale_threshold', 1) if current_data else 1,
                'shipping_cost': batch_defaults.get('shipping_cost', 0),
                'handling_cost': batch_defaults.get('handling_cost', 0)
            }
            print(f"{Colors.GREEN}💡 USING BATCH DEFAULTS:{Colors.RESET}")
            print(f"{Colors.GREEN}   Buying: {smart_defaults['buying_price']:.2f} | Shipping: {smart_defaults['shipping_cost']:.2f} | Handling: {smart_defaults['handling_cost']:.2f}{Colors.RESET}")
        
        elif is_largest_unit:
            # For parent unit, use current data as defaults
            smart_defaults = {
                'buying_price': current_data.get('buying_price', 0) if current_data else 0,
                'retail_price': current_data.get('retail_price', 0) if current_data else 0,
                'wholesale_price': current_data.get('wholesale_price', 0) if current_data else 0,
                'wholesale_threshold': current_data.get('wholesale_threshold', 1) if current_data else 1,
                'shipping_cost': current_data.get('shipping_cost', 0) if current_data else 0,
                'handling_cost': current_data.get('handling_cost', 0) if current_data else 0
            }
        else:
            # For child unit, USE PARENT DATA for smart defaults
            if parent_unit_data and parent_unit_data.get('relation', 0) > 0:
                relation = parent_unit_data['relation']
                
                smart_defaults = {
                    'buying_price': safe_value(parent_unit_data.get('buying_price', 0)) / relation,
                    'retail_price': current_data.get('retail_price', 0) if current_data else 0,
                    'wholesale_price': current_data.get('wholesale_price', 0) if current_data else 0,
                    'wholesale_threshold': current_data.get('wholesale_threshold', 1) if current_data else 1,
                    'shipping_cost': safe_value(parent_unit_data.get('shipping_cost', 0)) / relation,
                    'handling_cost': safe_value(parent_unit_data.get('handling_cost', 0)) / relation
                }
                
                print(f"{Colors.GREEN}💡 SMART DEFAULTS APPLIED:{Colors.RESET}")
                print(f"{Colors.GREEN}   Buying: {safe_value(parent_unit_data.get('buying_price', 0)):.2f} ÷ {relation} = {smart_defaults['buying_price']:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}   Shipping: {safe_value(parent_unit_data.get('shipping_cost', 0)):.2f} ÷ {relation} = {smart_defaults['shipping_cost']:.2f}{Colors.RESET}")
                print(f"{Colors.GREEN}   Handling: {safe_value(parent_unit_data.get('handling_cost', 0)):.2f} ÷ {relation} = {smart_defaults['handling_cost']:.2f}{Colors.RESET}")
            else:
                # Fallback to current data
                smart_defaults = {
                    'buying_price': current_data.get('buying_price', 0) if current_data else 0,
                    'retail_price': current_data.get('retail_price', 0) if current_data else 0,
                    'wholesale_price': current_data.get('wholesale_price', 0) if current_data else 0,
                    'wholesale_threshold': current_data.get('wholesale_threshold', 1) if current_data else 1,
                    'shipping_cost': current_data.get('shipping_cost', 0) if current_data else 0,
                    'handling_cost': current_data.get('handling_cost', 0) if current_data else 0
                }

        # INFINITE LOOP FOR DATA VALIDATION
        while True:
            try:
                # BASIC COSTS
                print(f"\n{Colors.BLUE}--- BASIC PRODUCT COSTS ---{Colors.RESET}")

                # 3. SHOW WHICH DATA IS BEING USED
                if batch_defaults and batch_defaults.get('batch_number'):
                    print(f"{Colors.CYAN}💡 Using batch: {batch_defaults['batch_number']}{Colors.RESET}")
                    if batch_defaults.get('quantity'):
                        print(f"{Colors.CYAN}   Batch Quantity: {batch_defaults['quantity']} units{Colors.RESET}")
                elif current_data and current_data.get('batch_number'):
                    print(f"{Colors.CYAN}💡 Using data from batch: {current_data['batch_number']}{Colors.RESET}")
                    if current_data.get('batch_quantity'):
                        print(f"{Colors.CYAN}   Batch Quantity: {current_data['batch_quantity']} units{Colors.RESET}")

                # 4. BUYING PRICE - WITH SMART DEFAULTS
                if batch_defaults and batch_defaults.get('buying_price'):
                    # Show batch default clearly
                    buying_price = self.validation_service.validate_positive_float(
                        f"Enter buying price for {unit_name} (batch default: {smart_defaults['buying_price']:.2f})", 
                        smart_defaults['buying_price'], 
                        0, 
                        "Buying price"
                    )
                elif is_largest_unit:
                    buying_price = self.validation_service.validate_positive_float(
                        f"Enter buying price for {unit_name} (current: {smart_defaults['buying_price']:.2f})", 
                        smart_defaults['buying_price'], 
                        0, 
                        "Buying price"
                    )
                else:
                    # For child units, show the calculated default clearly
                    calculated_default = smart_defaults['buying_price']
                    buying_price = self.validation_service.validate_positive_float(
                        f"Enter buying price for {unit_name} (calculated: {calculated_default:.2f})", 
                        calculated_default, 
                        0, 
                        "Buying price"
                    )

                #  5. RETAIL PRICE - WITH SMART DEFAULTS
                retail_price = self.validation_service.validate_positive_float(
                    f"Enter retail price for {unit_name} (current: {smart_defaults['retail_price']:.2f})", 
                    smart_defaults['retail_price'], 
                    0, 
                    "Retail price"
                )
                
                #  6. WARNING IF RETAIL PRICE IS LOWER THAN BUYING PRICE
                if retail_price < buying_price:
                    print(f"{Colors.YELLOW}⚠️  WARNING: Retail price ({retail_price:.2f}) is LOWER than buying price ({buying_price:.2f}){Colors.RESET}")
                    confirm = input(f"{Colors.YELLOW}Are you sure you want to sell at a loss? (yes/no): {Colors.RESET}").strip().lower()
                    if confirm != 'yes':
                        print(f"{Colors.BLUE}Let's enter the costs again...{Colors.RESET}")
                        continue

                # 7. WHOLESALE PRICE - WITH SMART DEFAULTS
                wholesale_price = self.validation_service.validate_positive_float(
                    f"Enter wholesale price for {unit_name} (current: {smart_defaults['wholesale_price']:.2f})", 
                    smart_defaults['wholesale_price'], 
                    0, 
                    "Wholesale price"
                )

                # 8. WARNING IF WHOLESALE PRICE IS LOWER THAN BUYING PRICE
                if wholesale_price < buying_price:
                    print(f"{Colors.YELLOW}⚠️  WARNING: Wholesale price ({wholesale_price:.2f}) is LOWER than buying price ({buying_price:.2f}){Colors.RESET}")
                    confirm = input(f"{Colors.YELLOW}Are you sure you want to sell at a loss? (yes/no): {Colors.RESET}").strip().lower()
                    if confirm != 'yes':
                        print(f"{Colors.BLUE}Let's enter the costs again...{Colors.RESET}")
                        continue

                # 9. WARNING IF WHOLESALE PRICE IS HIGHER THAN RETAIL
                if wholesale_price > retail_price:
                    print(f"{Colors.YELLOW}⚠️  WARNING: Wholesale price ({wholesale_price:.2f}) is HIGHER than retail price ({retail_price:.2f}){Colors.RESET}")
                    confirm = input(f"{Colors.YELLOW}Are you sure? (yes/no): {Colors.RESET}").strip().lower()
                    if confirm != 'yes':
                        print(f"{Colors.BLUE}Let's enter the costs again...{Colors.RESET}")
                        continue

                # 10. WHOLESALE THRESHOLD
                wholesale_threshold = self.validation_service.validate_positive_int(
                    f"Enter wholesale quantity threshold for {unit_name} (current: {smart_defaults['wholesale_threshold']})", 
                    smart_defaults['wholesale_threshold'], 
                    1, 
                    "Wholesale threshold"
                )

                # 11. SHIPPING COST - WITH SMART DEFAULTS
                if batch_defaults and batch_defaults.get('shipping_cost'):
                    shipping_cost = self.validation_service.validate_positive_float(
                        f"Enter shipping cost for {unit_name} (batch default: {smart_defaults['shipping_cost']:.2f})", 
                        smart_defaults['shipping_cost'], 
                        0, 
                        "Shipping cost"
                    )
                else:
                    shipping_cost = self.validation_service.validate_positive_float(
                        f"Enter shipping cost for {unit_name} (current: {smart_defaults['shipping_cost']:.2f})", 
                        smart_defaults['shipping_cost'], 
                        0, 
                        "Shipping cost"
                    )

                # 12. HANDLING COST - WITH SMART DEFAULTS
                if batch_defaults and batch_defaults.get('handling_cost'):
                    handling_cost = self.validation_service.validate_positive_float(
                        f"Enter handling cost for {unit_name} (batch default: {smart_defaults['handling_cost']:.2f})", 
                        smart_defaults['handling_cost'], 
                        0, 
                        "Handling cost"
                    )
                else:
                    handling_cost = self.validation_service.validate_positive_float(
                        f"Enter handling cost for {unit_name} (current: {smart_defaults['handling_cost']:.2f})", 
                        smart_defaults['handling_cost'], 
                        0, 
                        "Handling cost"
                    )

                # 13. CALCULATE LANDED COST
                landed_cost = buying_price + shipping_cost + handling_cost
                landed_cost_per_unit = landed_cost

                # 14. CALCULATE MARGINS WITH SMART DEFAULTS
                margin_data = self.cost_calculation_service.calculate_expected_margin(
                    retail_price=retail_price,
                    wholesale_price=wholesale_price,
                    landed_cost=landed_cost_per_unit,
                    product_id=product_id,
                    is_largest_unit=is_largest_unit
                )

                if margin_data:
                    product_costs = ProductCosts(
                        buying_price=buying_price,
                        retail_price=retail_price,
                        wholesale_price=wholesale_price,
                        wholesale_threshold=wholesale_threshold,
                        shipping_cost=shipping_cost,
                        handling_cost=handling_cost,
                        landed_cost=landed_cost,
                        landed_cost_per_unit=landed_cost_per_unit,
                        retail_profit=margin_data.retail_profit,
                        wholesale_profit=margin_data.wholesale_profit,
                        expected_margin=margin_data.expected_margin,
                        retail_ratio=margin_data.retail_ratio,
                        wholesale_ratio=margin_data.wholesale_ratio,
                        used_actual_data=margin_data.used_actual_data
                    )

                    # 15. CHECK FOR NEGATIVE MARGIN
                    if margin_data.expected_margin < 0:
                        print(f"{Colors.RED}🚨 CRITICAL WARNING: Expected margin is NEGATIVE ({margin_data.expected_margin:.2f}){Colors.RESET}")
                        print(f"{Colors.RED}   You will make a LOSS on this product!{Colors.RESET}")
                        confirm = input(f"{Colors.YELLOW}Do you want to continue with these prices? (yes/no): {Colors.RESET}").strip().lower()
                        if confirm != 'yes':
                            print(f"{Colors.BLUE}Let's enter the costs again...{Colors.RESET}")
                            continue
                    
                    break  # Exit the loop if everything is valid
                else:
                    print(f"{Colors.RED}❌ Error calculating margins. Let's try again.{Colors.RESET}")
                    continue

            except Exception as e:
                print(f"{Colors.RED}❌ Error: {e}. Let's try again.{Colors.RESET}")
                continue

        return product_costs

    def create_stock_batch(self, product_id: int, product_code: str, store: Store, 
                          costs: ProductCosts, quantity: int, expiry_date: Optional[str] = None) -> Optional[int]:
        """
        Create a new stock batch for FIFO management WITH MARGIN TRACKING AND EXPIRY DATE
        """
        try:
            # Generate batch number
            batch_number = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            #  CALCULATE EXPECTED MARGINS
            expected_margin = costs.expected_margin
            total_expected_profit = expected_margin * quantity
            
            # GET EXPIRY DATE USING VALIDATION FUNCTION
            if expiry_date is None:
                while True:
                    expiry_input = input(f"{Colors.BLUE}Enter expiry date for this batch (YYYY-MM-DD, optional - press Enter for none): {Colors.RESET}").strip()
                    
                    # Use the validation function
                    validation_result = self.validation_service.validate_expiry_date(expiry_input)
                    
                    if not validation_result.is_valid:
                        print(f"{Colors.RED}❌ {validation_result.message}{Colors.RESET}")
                        continue
                    
                    if validation_result.message and "WARNING" in validation_result.message:
                        print(f"{Colors.YELLOW}⚠️  {validation_result.message}{Colors.RESET}")
                        confirm = input(f"{Colors.YELLOW}Are you sure you want to use this date? (yes/no): {Colors.RESET}").strip().lower()
                        if confirm != 'yes':
                            print(f"{Colors.BLUE}Please enter a new expiry date{Colors.RESET}")
                            continue
                    
                    expiry_date = validation_result.value
                    if expiry_date:
                        print(f"{Colors.GREEN}✓ Date accepted: {expiry_date}{Colors.RESET}")
                    break
            
            #  VERIFY PRODUCT_CODE EXISTS IN PRODUCTS TABLE
            verify_product = self.db.execute_query(
                'inventory',
                "SELECT id FROM products WHERE product_code = ? AND id = ?",
                (product_code, product_id),
                fetch=True
            )
            
            if not verify_product:
                print(f"{Colors.RED}❌ ERROR: Product code '{product_code}' not found in products table{Colors.RESET}")
                print(f"{Colors.YELLOW}⚠️  Trying to get correct product code from database...{Colors.RESET}")
                
                # Get the correct product code from database
                correct_code_result = self.db.execute_query(
                    'inventory',
                    "SELECT product_code FROM products WHERE id = ?",
                    (product_id,),
                    fetch=True
                )
                
                if correct_code_result:
                    product_code = correct_code_result[0][0]
                    print(f"{Colors.GREEN}✓ Using correct product code: {product_code}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}❌ ERROR: Product ID {product_id} not found in database{Colors.RESET}")
                    return None
            
            # Create the batch in database
            batch_id = self.db.execute_query(
                'inventory',
                """INSERT INTO stock_batches (
                    product_id, product_code, store_id, store_code, batch_number, 
                    quantity, buying_price, shipping_cost, handling_cost, 
                    expected_margin, total_expected_profit,original_quantity,
                    received_date, expiry_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, datetime('now'), ?)""",
                (product_id, product_code, store.id, store.store_code, batch_number,
                 quantity, costs.buying_price, costs.shipping_cost, costs.handling_cost,
                 expected_margin, total_expected_profit,quantity, expiry_date)
            )
            
            if batch_id:
                print(f"{Colors.GREEN}✓ Stock batch created: {batch_number}{Colors.RESET}")
                print(f"{Colors.GREEN}  Expected Margin: {expected_margin:.2f} per unit{Colors.RESET}")
                print(f"{Colors.GREEN}  Total Expected Profit: {total_expected_profit:.2f}{Colors.RESET}")
                if expiry_date:
                    print(f"{Colors.GREEN}  Expiry Date: {expiry_date}{Colors.RESET}")
                return batch_id
            else:
                print(f"{Colors.RED}Error: Failed to create stock batch{Colors.RESET}")
                return None
                
        except Exception as e:
            print(f"{Colors.RED}Error creating stock batch: {e}{Colors.RESET}")
            return None
    
    def show_fifo_summary(self, product_id: int) -> None:
        """
        Display FIFO summary for a product WITH MARGIN INFORMATION
        """
        batches = self.db.execute_query(
            'inventory',
            """SELECT batch_number, quantity, buying_price, shipping_cost, handling_cost, 
                      landed_cost, expected_margin, total_expected_profit, received_date 
               FROM stock_batches 
               WHERE product_id = ? AND is_active = 1 
               ORDER BY received_date ASC""",
            (product_id,),
            fetch=True
        )
        
        if batches:
            print(f"\n{Colors.CYAN}=== FIFO STOCK SUMMARY ==={Colors.RESET}")
            print(f"{Colors.CYAN}Stock will be sold in this order:{Colors.RESET}")
            for i, batch in enumerate(batches, 1):
                (batch_number, quantity, buying_price, shipping_cost, handling_cost, 
                 landed_cost, expected_margin, total_expected_profit, received_date) = batch
                
                print(f"{i}. {batch_number}: {quantity} units")
                print(f"   Cost: {buying_price:.2f} + {shipping_cost:.2f} + {handling_cost:.2f} = {landed_cost:.2f}")
                print(f"   Expected Margin: {expected_margin:.2f} per unit | Total: {total_expected_profit:.2f}")
                print(f"   Received: {received_date}")
                print()
            
            print(f"{Colors.GREEN}✓ FIFO System Active - Oldest stock sells first{Colors.RESET}")
    
    # def get_product_hierarchy(self, base_name: str, store_id: int) -> Optional[Dict[str, Any]]:
    #     """
    #     Pata hierarchy yote ya product na relationships
    #     Returns: dict with parent-child relationships
    #     """
    #     try:
    #         # Get all units of this product
    #         all_units = self.db.execute_query(
    #             'inventory',
    #             """SELECT id, name, stock_quantity, low_stock_threshold, 
    #                       parent_product_id, relation_to_parent, unit, big_unit
    #                FROM products 
    #                WHERE LOWER(name) LIKE LOWER(?) AND store_id = ?
    #                ORDER BY 
    #                  CASE 
    #                    WHEN parent_product_id IS NULL THEN 0 
    #                    ELSE 1 
    #                  END,
    #                  relation_to_parent ASC""",
    #                 (f"%{base_name}%", store_id),
    #             fetch=True
    #         )
            
    #         if not all_units:
    #             return None
            
    #         # Build hierarchy
    #         hierarchy = {}
    #         parent_units = []
    #         child_units = []
            
    #         for unit in all_units:
    #             unit_id, name, stock, threshold, parent_id, relation, unit_name, big_unit = unit
                
    #             if parent_id is None:
    #                 # This is a parent unit (biggest unit)
    #                 parent_units.append({
    #                     'id': unit_id,
    #                     'name': name,
    #                     'stock': stock,
    #                     'threshold': threshold,
    #                     'unit': unit_name,
    #                     'big_unit': big_unit,
    #                     'children': []
    #                 })
    #             else:
    #                 # This is a child unit
    #                 child_units.append({
    #                     'id': unit_id,
    #                     'name': name,
    #                     'stock': stock,
    #                     'threshold': threshold,
    #                     'parent_id': parent_id,
    #                     'relation': relation,
    #                     'unit': unit_name,
    #                     'big_unit': big_unit
    #                 })
            
    #         # Link children to parents
    #         for parent in parent_units:
    #             for child in child_units[:]:  # Use slice copy to avoid modification during iteration
    #                 if child['parent_id'] == parent['id']:
    #                     parent['children'].append(child)
    #                     child_units.remove(child)
            
    #         return parent_units[0] if parent_units else None  # Return the root parent
            
    #     except Exception as e:
    #         print(f"{Colors.RED}Error getting product hierarchy: {e}{Colors.RESET}")
    #         return None


    def get_product_hierarchy(self, base_name: str, store_id: int) -> Optional[Dict[str, Any]]:
            """
            Pata hierarchy yote ya product na relationships (recursive version)
            """
            try:
                all_units = self.db.execute_query(
                    'inventory',
                    """SELECT id, name, stock_quantity, low_stock_threshold, 
                            parent_product_id, relation_to_parent, unit, big_unit
                    FROM products 
                    WHERE LOWER(name) LIKE LOWER(?) AND store_id = ?
                    ORDER BY 
                        CASE 
                        WHEN parent_product_id IS NULL THEN 0 
                        ELSE 1 
                        END,
                        relation_to_parent ASC""",
                    (f"%{base_name}%", store_id),
                    fetch=True
                )

                if not all_units:
                    return None

                # Convert all results into a dict by id for quick access
                units = {}
                for u in all_units:
                    unit_id, name, stock, threshold, parent_id, relation, unit_name, big_unit = u
                    units[unit_id] = {
                        'id': unit_id,
                        'name': name,
                        'stock': stock,
                        'threshold': threshold,
                        'unit': unit_name,
                        'big_unit': big_unit,
                        'relation': relation,
                        'parent_id': parent_id,
                        'children': []
                    }

                # Recursive function to attach children
                def attach_children(parent):
                    for unit in units.values():
                        if unit['parent_id'] == parent['id']:
                            parent['children'].append(unit)
                            attach_children(unit)  # recursive call

                # Find root parent (yule ambaye hana parent_id)
                roots = [u for u in units.values() if u['parent_id'] is None]
                if not roots:
                    return None

                # Jenga hierarchy kuanzia kwa root
                root = roots[0]
                attach_children(root)
                return root

            except Exception as e:
                print(f"{Colors.RED}Error getting product hierarchy: {e}{Colors.RESET}")
                return None
