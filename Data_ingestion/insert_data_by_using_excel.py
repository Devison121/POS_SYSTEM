# insert_data_by_using_excel.py

"""
Enhanced Excel Data Import with Sequential Batch System
- Batch numbers based on entry order from stock_batches table
- Excel shows filter numbers (1,2,3) but stores actual batch names
- All columns highlighted in yellow as required
- Last entered batch determines selling price
- Automatic calculation of stock, shipping and handling costs using relation
"""

# Hii code ina fanya kazi kwa ufanisi ila ina changamoto kwenye insert data kwenye database.Inaanza na unity ndogo na kuendelea na unit kubwa. XXXXXXX
#Lakini now hii code ni safi na inaendana na mahitaji ya mteja.Lakini inapaswa maludio tena na malekebisho.

# make sure you put synced = 0 when updating stock quantities from excel import
from ask_for_image import ask_excel_file_dialog, ask_image_file_dialog
from pathlib import Path
import pandas as pd 
import sqlite3
import xlsxwriter
import os
import sys
import subprocess
from enum import Enum
import json
from datetime import datetime
import random
import string
from typing import Optional
from datetime import datetime as dt


class ValidationResult:
    """Result class for validation operations"""
    def __init__(self, is_valid: bool, value: Optional[str] = None, message: Optional[str] = None):
        self.is_valid = is_valid
        self.value = value
        self.message = message


class Colors:
    """Color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = "\033[96m" 
    BLUE = '\033[94m'
    RESET = '\033[0m'


class ProductColumns(Enum):
    """Enumeration for product column names"""
    BATCH_NUMBER = "BATCH_NUMBER"
    NAME = "NAME"
    STOCK_QUANTITY = "STOCK_QUANTITY"
    BUYING_PRICE = "BUYING_PRICE"
    SHIPPING_COST = "SHIPPING_COST"
    HANDLING_COST = "HANDLING_COST"
    WHOLESALE_PRICE = "WHOLESALE_PRICE"
    WHOLESALE_THRESHOLD = "WHOLESALE_THRESHOLD"
    RETAIL_PRICE = "RETAIL_PRICE"
    UNIT = "UNIT"
    BIG_UNIT = "BIG_UNIT"
    RELATION_OF_UNITY = "RELATION_OF_UNITY"
    LOW_STOCK_THRESHOLD = "LOW_STOCK_THRESHOLD"
    EXPIRY_DATE = "EXPIRY_DATE"


class ExcelProcessor:
    """
    Enhanced Excel Processor with Sequential Batch Filter System
    """
    
    def __init__(self):
        """Initialize the ExcelProcessor with default settings and paths"""
        self.STORE_ID = None
        self.current_store_code = None
        self.current_store_name = None
        self.current_store_id = None 
        self.databases_path = "../Databases"
        self.products_db = os.path.join(self.databases_path, "inventory.db")
        self.template_file = "product_templates.csv"
        
        # Establish database connection
        self.conn = sqlite3.connect(self.products_db)  
        self.cursor = self.conn.cursor()

        print(f"{Colors.BLUE}📁 Database paths:{Colors.RESET}")
        print(f"{Colors.BLUE}   - Products: {self.products_db}{Colors.RESET}")
        
        # Initialize required components
        self.check_database_files()
        self.initialize_template_csv()
    
    def check_database_files(self):
        """Check if required database files exist"""
        if not os.path.exists(self.products_db):
            print(f"{Colors.RED}❌ Products database not found: {self.products_db}{Colors.RESET}")
            return False
        
        print(f"{Colors.GREEN}✓ Database file found successfully{Colors.RESET}")
        return True
    
    def initialize_template_csv(self):
        """Initialize CSV template file with sample data if it doesn't exist"""
        if not os.path.exists(self.template_file):
            # Define template structure with sample data
            template_data = [
                ["BATCH_NUMBER", "NAME", "STOCK_QUANTITY", "BUYING_PRICE", "SHIPPING_COST", "HANDLING_COST", 
                 "WHOLESALE_PRICE", "WHOLESALE_THRESHOLD", "RETAIL_PRICE", "UNIT", "BIG_UNIT", 
                 "RELATION_OF_UNITY", "LOW_STOCK_THRESHOLD", "EXPIRY_DATE"],
                ["1", "Sugar", 50, 900.0, 200.0, 100.0, 1200.0, 10, 1500.0, "kg", "kg", 25, 5, "2024-12-31"],
                ["1", "Rice", 30, 1800.0, 100.0, 50.0, 2500.0, 6, 3000.0, "kg", "kg", 50, 3, "2024-12-31"],
                ["1", "Cooking Oil", 20, 2500.0, 150.0, 75.0, 3200.0, 5, 3500.0, "liter", "liter", 20, 2, "2024-12-31"]
            ]
            
            # Create DataFrame and save as CSV
            df = pd.DataFrame(template_data[1:], columns=template_data[0])
            df.to_csv(self.template_file, index=False, encoding='utf-8')
            print(f"{Colors.GREEN}✓ Template CSV file created: {self.template_file}{Colors.RESET}")

    def read_template_csv(self):
        """Read CSV template file and return data as list of lists"""
        try:
            if not os.path.exists(self.template_file):
                print(f"{Colors.RED}❌ Template file not found: {self.template_file}{Colors.RESET}")
                return None
            
            # Read CSV file
            df = pd.read_csv(self.template_file)
            
            # Convert DataFrame to list of lists
            data_list = []
            
            # Add headers first
            headers = df.columns.tolist()
            data_list.append(headers)
            
            # Add data rows
            for index, row in df.iterrows():
                row_data = []
                for col in headers:
                    value = row[col]
                    # Handle NaN values
                    if pd.isna(value):
                        row_data.append('')
                    else:
                        row_data.append(value)
                data_list.append(row_data)
            
            print(f"{Colors.GREEN}✓ Successfully read template CSV: {self.template_file}{Colors.RESET}")
            print(f"{Colors.BLUE}📊 Data shape: {len(data_list)-1} rows, {len(headers)} columns{Colors.RESET}")
            
            return data_list
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error reading template CSV: {e}{Colors.RESET}")
            return None


    def check_required_tables(self):
        """Check if all required database tables exist"""
        required_tables = ['products', 'store_product_prices', 'stores', 'user_stores', 'stock_batches']
        
        try:
            conn = sqlite3.connect(self.products_db)
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [table[0] for table in cursor.fetchall()]
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            conn.close()
            
            if missing_tables:
                print(f"{Colors.RED}❌ Missing required tables:{Colors.RESET}")
                for table in missing_tables:
                    print(f"{Colors.RED}   - {table}{Colors.RESET}")
                return False
            
            print(f"{Colors.GREEN}✓ All required tables found in database{Colors.RESET}")
            return True
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}❌ Database error while checking tables: {e}{Colors.RESET}")
            return False

    def select_store(self):
        """Allow user to select a store from available stores in database"""
        try:
            if not self.check_required_tables():
                return None
            
            conn = sqlite3.connect(self.products_db)
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, store_code, name, location FROM stores ORDER BY name")
            stores = cursor.fetchall()
            
            if not stores:
                print(f"{Colors.RED}❌ No stores found in database{Colors.RESET}")
                conn.close()
                return None
            
            print(f"\n{Colors.BLUE}=== SELECT STORE ==={Colors.RESET}")
            print(f"{Colors.BLUE}Available Stores:{Colors.RESET}")
            
            for i, store in enumerate(stores, 1):
                store_id, store_code, name, location = store
                location_display = location if location else "No location"
                print(f"{i}. {name} ({store_code}) - {location_display}")
            
            try:
                choice = int(input(f"\n{Colors.BLUE}Select store (1-{len(stores)}): {Colors.RESET}").strip())
                if 1 <= choice <= len(stores):
                    store_id, store_code, name, location = stores[choice - 1]
                    self.STORE_ID = store_id
                    self.current_store_code = store_code
                    self.current_store_id = store_id
                    self.current_store_name = name
                    print(f"{Colors.GREEN}✓ Selected store: {name} ({store_code}) - ID: {store_id}{Colors.RESET}")
                    return True
                else:
                    print(f"{Colors.RED}❌ Invalid selection{Colors.RESET}")
                    return False
            except ValueError:
                print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")
                return False
                
        except sqlite3.Error as e:
            print(f"{Colors.RED}❌ Error selecting store: {e}{Colors.RESET}")
            return False

    def get_existing_batches_for_product(self, product_name=None, limit=None):
        """Fetch filter numbers and batch_numbers for a specific product."""
        try:
            if not self.current_store_id:
                print(f"{Colors.YELLOW}⚠ fetch_sample_products: current_store_id is not set{Colors.RESET}")
                return None
            
            # ✅ Product name validation - not optional
            if not product_name:
                print(f"{Colors.RED}❌ Product name is required{Colors.RESET}")
                return None

            conn = sqlite3.connect(self.products_db)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # ✅ Check if product name exists in database
            check_sql = """
                SELECT id, name 
                FROM products 
                WHERE UPPER(name) = UPPER(?) AND store_id = ?
            """
            cur.execute(check_sql, (product_name, self.current_store_id))
            product_row = cur.fetchone()
            
            if not product_row:
                print(f"{Colors.RED}❌ Product '{product_name}' not found in this store{Colors.RESET}")
                conn.close()
                return None

            product_id = product_row['id']
            print(f"{Colors.GREEN}✅ Product found: {product_name} (ID: {product_id}){Colors.RESET}")

            sql = """
                SELECT
                    p.id AS id,
                    sb.batch_number
                FROM products p
                LEFT JOIN stock_batches sb
                    ON sb.product_id = p.id AND sb.store_id = ?
                WHERE p.store_id = ? AND p.name = ?
                ORDER BY p.name, sb.id ASC
            """

            params = [self.current_store_id, self.current_store_id, product_name]

            if isinstance(limit, int) and limit > 0:
                sql += " LIMIT ?"
                params.append(limit)

            cur.execute(sql, params)
            rows = cur.fetchall()
            conn.close()

            if not rows:
                print(f"{Colors.YELLOW}⚠ No batches found for product '{product_name}'{Colors.RESET}")
                return None

            sample = []
            cache_batches = {}

            for r in rows:
                current_product_id = r['id']
                batch_name = r['batch_number']
                filter_number = 1

                # 1️⃣ If batch list not in cache, fetch from DB
                if current_product_id not in cache_batches:
                    batches = self.execute_query(
                        """
                        SELECT batch_number
                        FROM stock_batches
                        WHERE product_id = ? AND store_id = ?
                        ORDER BY received_date ASC, id ASC
                        """,
                        (current_product_id, self.current_store_id),
                        fetch=True
                    )
                    cache_batches[current_product_id] = [b[0] for b in batches] if batches else []

                # 2️⃣ Find filter number (batch position)
                if batch_name and batch_name in cache_batches[current_product_id]:
                    filter_number = cache_batches[current_product_id].index(batch_name) + 1

                # 3️⃣ Return only (filter_number, batch_number)
                sample.append((filter_number, batch_name))
                print(f"{Colors.BLUE}   - Batch: {batch_name}, Filter Number: {filter_number}{Colors.RESET}")
            
            print(f"{Colors.GREEN}✅ Successfully fetched {len(sample)} batches for product '{product_name}'{Colors.RESET}")
            return sample

        except Exception as e:
            print(f"{Colors.RED}❌ fetch_sample_products error: {e}{Colors.RESET}")
            return None

    def find_parent_product_id(self, clean_name, big_unit):
        """Find parent product ID for child units"""
        try:
            conn = sqlite3.connect(self.products_db)
            cursor = conn.cursor()
            
            # Tafuta parent product kwa kutumia jina na big_unit
            cursor.execute(
                "SELECT id FROM products WHERE name LIKE ? AND store_id = ? AND unit = ? LIMIT 1",
                (f"%{clean_name}%", self.current_store_id, big_unit)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return result[0]
            return None
            
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Error finding parent product: {e}{Colors.RESET}")
            return None


    def get_next_sequence_number(self):
        """Get the next sequence number for products in current store"""
        try:
            if not self.current_store_code:
                return 1
                
            conn = sqlite3.connect(self.products_db)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT sequence_number FROM products WHERE store_code = ? ORDER BY sequence_number DESC LIMIT 1",
                (self.current_store_code,)
            )
            result = cursor.fetchone()
            conn.close()
            
            return result[0] + 1 if result else 1
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Warning: Error getting sequence number, using default 1: {e}{Colors.RESET}")
            return 1

    def generate_product_code(self, sequence_number):
        """Generate product code using store code and sequence number"""
        return f"{self.current_store_code}_{sequence_number:04d}"
        
    def check_product_exists(self, product_name):
        """Check if a product already exists in the current store"""
        try:
            conn = sqlite3.connect(self.products_db)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, stock_quantity, low_stock_threshold FROM products WHERE name = ? AND store_id = ?",
                (product_name, self.STORE_ID)
            )
            result = cursor.fetchone()
            
            if result:
                product_id = result[0]
                cursor.execute(
                    "SELECT id FROM store_product_prices WHERE product_id = ? AND store_id = ?",
                    (product_id, self.STORE_ID)
                )
                price_exists = cursor.fetchone() is not None
                conn.close()
                
                return result, price_exists
            
            conn.close()
            return None, False
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error checking product existence: {e}{Colors.RESET}")
            return None, False
        
    def check_and_calculate_relation_values(self, row_data, product_hierarchy=None):
        """
        Calculate values for any unit in multi-level hierarchy
        Supports: Carton → Bunda → Single (any depth)
        
        Args:
            row_data: Dictionary of current row data
            product_hierarchy: Pre-built hierarchy map {unit: {parent_data}}
            
        Returns: tuple (stock_quantity, buying_price, shipping_cost, handling_cost, low_stock_threshold, is_child_unit)
        """
        try:
            # Extract values with safe defaults
            stock_quantity = self.safe_float(row_data.get('STOCK_QUANTITY'))
            buying_price = self.safe_float(row_data.get('BUYING_PRICE')) 
            shipping_cost = self.safe_float(row_data.get('SHIPPING_COST'))
            handling_cost = self.safe_float(row_data.get('HANDLING_COST'))
            low_stock_threshold = self.safe_float(row_data.get('LOW_STOCK_THRESHOLD'))
            relation = self.safe_float(row_data.get('RELATION_OF_UNITY', 1))
            unit = str(row_data.get('UNIT', '')).strip()
            big_unit = str(row_data.get('BIG_UNIT', '')).strip()
            product_name = str(row_data.get('NAME', 'Unknown')).strip()

            print(f"{Colors.BLUE}🔍 Multi-level calculation for: {product_name}{Colors.RESET}")
            print(f"{Colors.BLUE}   Unit: '{unit}', Big Unit: '{big_unit}', Relation: {relation}{Colors.RESET}")

            # If no hierarchy provided or no unit, return original values
            if not product_hierarchy or not unit:
                final_stock = stock_quantity if stock_quantity is not None else 0
                final_buying = buying_price if buying_price is not None else 0
                final_shipping = shipping_cost if shipping_cost is not None else 0
                final_handling = handling_cost if handling_cost is not None else 0
                final_threshold = low_stock_threshold if low_stock_threshold is not None else 0
                return (final_stock, final_buying, final_shipping, final_handling, final_threshold, False)

            # Build hierarchy path from current unit to base
            hierarchy_path = self.build_hierarchy_path(unit, product_hierarchy)
            if not hierarchy_path:
                print(f"{Colors.YELLOW}⚠ No hierarchy path found for {unit}{Colors.RESET}")
                final_stock = stock_quantity if stock_quantity is not None else 0
                final_buying = buying_price if buying_price is not None else 0
                final_shipping = shipping_cost if shipping_cost is not None else 0
                final_handling = handling_cost if handling_cost is not None else 0
                final_threshold = low_stock_threshold if low_stock_threshold is not None else 0
                return (final_stock, final_buying, final_shipping, final_handling, final_threshold, False)

            # Determine base unit (last in hierarchy)
            base_unit = hierarchy_path[-1]['unit']
            print(f"{Colors.GREEN}✓ Hierarchy: {[f'{u['unit']}({u['relation']})' for u in hierarchy_path]} → Base: {base_unit}{Colors.RESET}")

            # Calculate cumulative relation from this unit to base unit
            cumulative_relation = self.calculate_cumulative_relation(hierarchy_path, unit)
            print(f"{Colors.GREEN}✓ Cumulative relation from {unit} → {base_unit}: {cumulative_relation}{Colors.RESET}")

            # Find nearest parent with actual values
            parent_data = self.find_parent_with_values_recursive(unit, product_hierarchy)
            if not parent_data:
                print(f"{Colors.YELLOW}⚠ No parent data found for {unit}, using provided values{Colors.RESET}")
                final_stock = stock_quantity if stock_quantity is not None else 0
                final_buying = buying_price if buying_price is not None else 0
                final_shipping = shipping_cost if shipping_cost is not None else 0
                final_handling = handling_cost if handling_cost is not None else 0
                final_threshold = low_stock_threshold if low_stock_threshold is not None else 0
                return (final_stock, final_buying, final_shipping, final_handling, final_threshold, False)

            # Calculate child values only for missing fields
            calculated_values = self.calculate_child_values(
                stock_quantity, buying_price, shipping_cost, handling_cost, low_stock_threshold,
                parent_data, cumulative_relation, unit, base_unit
            )

            return (*calculated_values, True)  # is_child_unit = True

        except Exception as e:
            print(f"{Colors.RED}❌ Error in multi-level calculation: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
            # Return safe defaults
            stock = stock_quantity if stock_quantity is not None else 0
            buying = buying_price if buying_price is not None else 0
            shipping = shipping_cost if shipping_cost is not None else 0
            handling = handling_cost if handling_cost is not None else 0
            threshold = low_stock_threshold if low_stock_threshold is not None else 0
            return (stock, buying, shipping, handling, threshold, False)

    def build_hierarchy_path(self, start_unit, product_hierarchy):
        """
        Build complete hierarchy path from start_unit to base_unit
        Returns: List of units in hierarchy order [current, parent, grandparent, ..., base]
        """
        hierarchy_path = []
        current_unit = start_unit
        visited_units = set()

        # Add starting unit
        if current_unit in product_hierarchy:
            hierarchy_path.append({
                'unit': current_unit,
                'relation': product_hierarchy[current_unit].get('relation', 1),
                'parent_unit': product_hierarchy[current_unit].get('big_unit')
            })
            visited_units.add(current_unit)

        # Follow parent chain
        while current_unit and current_unit in product_hierarchy:
            parent_unit = product_hierarchy[current_unit].get('big_unit')
            
            if not parent_unit or parent_unit in visited_units:
                break
                
            if parent_unit in product_hierarchy:
                hierarchy_path.append({
                    'unit': parent_unit,
                    'relation': product_hierarchy[parent_unit].get('relation', 1),
                    'parent_unit': product_hierarchy[parent_unit].get('big_unit')
                })
                visited_units.add(parent_unit)
                current_unit = parent_unit
            else:
                # Parent unit exists in hierarchy but no data - add it anyway
                hierarchy_path.append({
                    'unit': parent_unit,
                    'relation': 1,
                    'parent_unit': None
                })
                break

        return hierarchy_path

    def build_product_hierarchy(self, df):
        """
        Build complete product hierarchy map from Excel data
        Must be called BEFORE processing rows
        Returns: dict {unit: {big_unit, relation, has_values, stock_quantity, buying_price, etc.}}
        """
        product_hierarchy = {}
        
        print(f"{Colors.BLUE}🔨 Building product hierarchy from Excel data...{Colors.RESET}")
        
        for index, row in df.iterrows():
            try:
                # Skip empty rows
                if pd.isna(row.get('NAME')) or str(row.get('NAME', '')).strip() == '':
                    continue
                    
                unit = str(row.get('UNIT', '')).strip()
                big_unit = str(row.get('BIG_UNIT', '')).strip()
                relation_input = row.get('RELATION_OF_UNITY', 1)
                
                if not unit:
                    continue
                    
                # Safely convert relation to float
                relation = 1.0
                if not pd.isna(relation_input) and str(relation_input).strip() != '':
                    try:
                        relation = float(relation_input)
                        if relation <= 0:
                            relation = 1.0
                    except (ValueError, TypeError):
                        relation = 1.0
                
                # Check if this row has actual values (not empty/zero)
                has_values = False
                stock_qty = self.safe_float(row.get('STOCK_QUANTITY'))
                buying_prc = self.safe_float(row.get('BUYING_PRICE'))
                shipping_cst = self.safe_float(row.get('SHIPPING_COST'))
                handling_cst = self.safe_float(row.get('HANDLING_COST'))
                
                # Consider it has values if any field is provided and non-zero
                if (stock_qty is not None and stock_qty > 0) or \
                (buying_prc is not None and buying_prc > 0) or \
                (shipping_cst is not None and shipping_cst > 0) or \
                (handling_cst is not None and handling_cst > 0):
                    has_values = True
                
                # Store in hierarchy
                product_hierarchy[unit] = {
                    'big_unit': big_unit if big_unit else None,
                    'relation': relation,
                    'has_values': has_values,
                    'stock_quantity': stock_qty,
                    'buying_price': buying_prc,
                    'shipping_cost': shipping_cst,
                    'handling_cost': handling_cst,
                    'low_stock_threshold': self.safe_float(row.get('LOW_STOCK_THRESHOLD')),
                    'product_name': str(row.get('NAME', '')).strip()
                }
                
                print(f"{Colors.BLUE}   ➤ {unit} → {big_unit} (relation: {relation}) - Has values: {has_values}{Colors.RESET}")
                
            except Exception as e:
                print(f"{Colors.RED}❌ Error processing row {index} for hierarchy: {e}{Colors.RESET}")
                continue
        
        print(f"{Colors.GREEN}✅ Built hierarchy map with {len(product_hierarchy)} units{Colors.RESET}")
        
        # Debug: print hierarchy structure
        self.print_hierarchy_structure(product_hierarchy)
        
        return product_hierarchy
    
    def print_hierarchy_structure(self, hierarchy):
        """Print the hierarchy structure for debugging"""
        print(f"{Colors.CYAN}📊 HIERARCHY STRUCTURE:{Colors.RESET}")
        
        # Find base units (units with no parent)
        base_units = []
        for unit, data in hierarchy.items():
            if not data.get('big_unit') or data['big_unit'] not in hierarchy:
                base_units.append(unit)
        
        for base in base_units:
            print(f"{Colors.CYAN}  Base: {base}{Colors.RESET}")
            self.print_hierarchy_branch(base, hierarchy, level=1)

    def print_hierarchy_branch(self, unit, hierarchy, level=0):
        """Recursively print hierarchy branches"""
        indent = "    " * level
        children = [u for u, data in hierarchy.items() if data.get('big_unit') == unit]
        
        for child in children:
            relation = hierarchy[child].get('relation', 1)
            has_vals = hierarchy[child].get('has_values', False)
            values_indicator = " 📊" if has_vals else ""
            print(f"{Colors.CYAN}{indent}└── {child} (×{relation}){values_indicator}{Colors.RESET}")
            self.print_hierarchy_branch(child, hierarchy, level + 1)

    def calculate_cumulative_relation(self, hierarchy_path, target_unit):
        """
        Calculate total relation from target_unit to base_unit
        """
        if not hierarchy_path:
            return 1.0

        # Find the target unit in the path
        target_index = -1
        for i, unit_data in enumerate(hierarchy_path):
            if unit_data['unit'] == target_unit:
                target_index = i
                break
        
        if target_index == -1:
            return 1.0

        # Calculate product of relations from target to end
        cumulative = 1.0
        for i in range(target_index, len(hierarchy_path) - 1):
            cumulative *= hierarchy_path[i]['relation']

        return cumulative

    def find_parent_with_values_recursive(self, unit, product_hierarchy, visited=None):
        """
        Recursively find the nearest parent with actual values
        """
        if visited is None:
            visited = set()
        
        if unit in visited or unit not in product_hierarchy:
            return None
            
        visited.add(unit)
        
        data = product_hierarchy[unit]
        
        # Check if this unit has values
        if data.get('has_values', False):
            return data
        
        # Recursively check parent
        parent_unit = data.get('big_unit')
        if parent_unit:
            return self.find_parent_with_values_recursive(parent_unit, product_hierarchy, visited)
        
        return None

    def calculate_child_values(self, child_stock, child_buying, child_shipping, child_handling, child_threshold,
                            parent_data, cumulative_relation, child_unit, base_unit):
        """
        Calculate child values based on parent data and cumulative relation
        Only calculates fields that are empty in child
        """
        calculated = {
            'stock_quantity': child_stock,
            'buying_price': child_buying, 
            'shipping_cost': child_shipping,
            'handling_cost': child_handling,
            'low_stock_threshold': child_threshold
        }

        # Only calculate missing fields
        fields_to_calculate = []
        if calculated['stock_quantity'] is None: fields_to_calculate.append('stock_quantity')
        if calculated['buying_price'] is None: fields_to_calculate.append('buying_price')
        if calculated['shipping_cost'] is None: fields_to_calculate.append('shipping_cost') 
        if calculated['handling_cost'] is None: fields_to_calculate.append('handling_cost')
        if calculated['low_stock_threshold'] is None: fields_to_calculate.append('low_stock_threshold')

        if not fields_to_calculate:
            print(f"{Colors.BLUE}ℹ All fields provided for {child_unit}, no calculation needed{Colors.RESET}")
            return (calculated['stock_quantity'] or 0, calculated['buying_price'] or 0,
                    calculated['shipping_cost'] or 0, calculated['handling_cost'] or 0,
                    calculated['low_stock_threshold'] or 0)

        print(f"{Colors.YELLOW}⚠ Calculating missing fields for {child_unit}: {fields_to_calculate}{Colors.RESET}")

        # Calculate missing fields
        for field in fields_to_calculate:
            parent_value = parent_data.get(field, 0) or 0
            
            if field in ['buying_price', 'shipping_cost', 'handling_cost']:
                # Costs are divided (big unit has higher cost)
                calculated[field] = round(parent_value / cumulative_relation, 2)
                print(f"{Colors.GREEN}  ✓ {field}: {parent_value} / {cumulative_relation} = {calculated[field]}{Colors.RESET}")
            
            elif field in ['stock_quantity', 'low_stock_threshold']:
                # Quantities are multiplied (big unit has fewer items)
                calculated[field] = parent_value * cumulative_relation
                print(f"{Colors.GREEN}  ✓ {field}: {parent_value} × {cumulative_relation} = {calculated[field]}{Colors.RESET}")

        return (calculated['stock_quantity'] or 0, calculated['buying_price'] or 0,
                calculated['shipping_cost'] or 0, calculated['handling_cost'] or 0, 
                calculated['low_stock_threshold'] or 0)

    def safe_float(self, value, default=None):
        """Safely convert to float, return None if empty/invalid"""
        if value is None or pd.isna(value) or str(value).strip() == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
        

    def fetch_sample_products(self, limit=None):
        """Fetch sample products with batch info and assign filter numbers."""
        try:
            if not self.current_store_id:
                print(f"{Colors.YELLOW}⚠ fetch_sample_products: current_store_id is not set{Colors.RESET}")
                return None

            conn = sqlite3.connect(self.products_db)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            sql = """
                SELECT
                    p.id AS id,
                    p.name,
                    COALESCE(sb.quantity, 0) AS stock_quantity,
                    COALESCE(sb.buying_price, 0) AS buying_price,
                    COALESCE(sb.shipping_cost, 0) AS shipping_cost,
                    COALESCE(sb.handling_cost, 0) AS handling_cost,
                    COALESCE(spp.wholesale_price, 0) AS wholesale_price,
                    COALESCE(spp.wholesale_threshold, 1) AS wholesale_threshold,
                    COALESCE(spp.retail_price, 0) AS retail_price,
                    COALESCE(p.unit, '') AS unit,
                    COALESCE(p.big_unit, '') AS big_unit,
                    COALESCE(p.relation_to_parent, 0) AS relation_of_unity,
                    COALESCE(p.low_stock_threshold, 5) AS low_stock_threshold,
                    COALESCE(sb.expiry_date, '') AS expiry_date,
                    sb.batch_number
                FROM products p
                LEFT JOIN store_product_prices spp
                    ON spp.product_id = p.id AND spp.store_id = ?
                LEFT JOIN stock_batches sb
                    ON sb.product_id = p.id AND sb.store_id = ?
                WHERE p.store_id = ?
                ORDER BY p.name, sb.id ASC
            """

            params = [self.current_store_id, self.current_store_id, self.current_store_id]

            if isinstance(limit, int) and limit > 0:
                sql += " LIMIT ?"
                params.append(limit)

            cur.execute(sql, params)
            rows = cur.fetchall()
            conn.close()

            if not rows:
                return None

            sample = []
            cache_batches = {}  # cache ya batches kwa kila product_id

            for r in rows:
                product_id = r['id']
                product_name = r['name']
                batch_name = r['batch_number']
                filter_number = 1  # default

                # 🔹 fetch batches kama hazijahifadhiwa bado kwenye cache
                if product_id not in cache_batches:
                    batches = self.execute_query(
                        """
                        SELECT batch_number
                        FROM stock_batches
                        WHERE product_id = ? AND store_id = ?
                        ORDER BY received_date ASC, id ASC
                        """,
                        (product_id, self.current_store_id),
                        fetch=True
                    )
                    cache_batches[product_id] = [b[0] for b in batches] if batches else []

                # 🔹 tafuta namba ya batch (filter number)
                if batch_name and batch_name in cache_batches[product_id]:
                    filter_number = cache_batches[product_id].index(batch_name) + 1

                # 🔹 andaa sample ya bidhaa
                sample.append([
                    filter_number,
                    product_name or '',
                    int(r['stock_quantity']) if r['stock_quantity'] is not None else '',
                    float(r['buying_price']) if r['buying_price'] is not None else '',
                    float(r['shipping_cost']) if r['shipping_cost'] is not None else '',
                    float(r['handling_cost']) if r['handling_cost'] is not None else '',
                    float(r['wholesale_price']) if r['wholesale_price'] is not None else '',
                    int(r['wholesale_threshold']) if r['wholesale_threshold'] is not None else '',
                    float(r['retail_price']) if r['retail_price'] is not None else '',
                    r['unit'] or '',
                    r['big_unit'] or '',
                    int(r['relation_of_unity']) if r['relation_of_unity'] is not None else '',
                    int(r['low_stock_threshold']) if r['low_stock_threshold'] is not None else '',
                    r['expiry_date'] or ''
                ])

            return sample

        except Exception as e:
            print(f"{Colors.RED}❌ fetch_sample_products error: {e}{Colors.RESET}")
            return None


    def validate_expiry_date(self, date_input: str, current_expiry: Optional[str] = None) -> ValidationResult:
        """Validate expiry date input"""
        if not date_input or pd.isna(date_input) or str(date_input).strip() == '' or str(date_input).lower() == 'nan':
            return ValidationResult(is_valid=True, value=current_expiry)
        
        try:
            # Convert to string and clean
            date_str = str(date_input).strip()
            
            # Handle various date formats
            date_formats = [
                '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y', '%Y.%m.%d',
                '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'
            ]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = dt.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_date is None:
                return ValidationResult(is_valid=False, value=None, message="Invalid date format. Please use YYYY-MM-DD format")
            
            # Format to standard YYYY-MM-DD
            formatted_date = parsed_date.strftime('%Y-%m-%d')
            
            # Validate date range (current year to 10 years in future)
            current_year = dt.now().year
            min_year = current_year
            max_year = current_year + 10
            
            if parsed_date.year < min_year or parsed_date.year > max_year:
                return ValidationResult(is_valid=False, value=None, message=f"Invalid year. Please enter a year between {min_year} and {max_year}")
            
            # Check if date is in past (warning only)
            today = dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if parsed_date < today:
                return ValidationResult(is_valid=True, value=formatted_date, message="WARNING: This expiry date is in the past!")
            
            return ValidationResult(is_valid=True, value=formatted_date)
            
        except Exception as e:
            return ValidationResult(is_valid=False, value=None, message=f"Error validating date: {str(e)}")

    def export_or_create_template(self, mode='INSERT'):
        """Create Excel template for product data entry with batch filter system"""
        try:
            if not self.current_store_code:
                print(f"{Colors.RED}❌ Please select a store first{Colors.RESET}")
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"products_template_{self.current_store_code}_{timestamp}.xlsx"
            
            workbook = xlsxwriter.Workbook(filename, {'nan_inf_to_errors': True})
            worksheet = workbook.add_worksheet('Products')
            
            # DEFINE CELL FORMATS
            header_format = workbook.add_format({
                'bold': True, 
                'bg_color': '#366092', 
                'font_color': 'white',
                'border': 1, 
                'align': 'center'
            })
            
            # ALL COLUMNS ARE YELLOW (REQUIRED)
            yellow_format = workbook.add_format({
                'border': 1, 
                'bg_color': '#FFF2CC'  # YELLOW for ALL columns
            })
            
            batch_format = workbook.add_format({
                'border': 1, 
                'bg_color': '#E6F3FF'  # LIGHT BLUE for batch number
            })
            
            red_format = workbook.add_format({'bg_color': '#FFC7CE'})  # RED for errors
            yellow_warning_format = workbook.add_format({'bg_color': '#FFFFCC'})  # YELLOW for warnings
            
            # COLUMN HEADERS - ALL COLUMNS ARE REQUIRED
            headers = [
                'BATCH_NUMBER', 'NAME', 'STOCK_QUANTITY', 'BUYING_PRICE', 'SHIPPING_COST', 
                'HANDLING_COST', 'WHOLESALE_PRICE', 'WHOLESALE_THRESHOLD', 'RETAIL_PRICE', 
                'UNIT', 'BIG_UNIT', 'RELATION_OF_UNITY', 'LOW_STOCK_THRESHOLD', 'EXPIRY_DATE'
            ]
            
            # WRITE HEADERS
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # GET SAMPLE DATA
            sample_data = self.fetch_sample_products()
            if not sample_data:
                sample_data = self.read_template_csv() 
                
                print(f"{Colors.YELLOW}⚠ Using default sample data{Colors.RESET}")
            
            # ADD EXTRA ROWS
            NUM_EXTRA_ROWS = input("Enter number of extra rows (default 50): ").strip()
            if not NUM_EXTRA_ROWS:
                NUM_EXTRA_ROWS = 50
            else:
                NUM_EXTRA_ROWS = int(NUM_EXTRA_ROWS)
                
            empty_row = [''] * len(headers)
            sample_data.extend([empty_row] * NUM_EXTRA_ROWS)
            
            # WRITE SAMPLE DATA - ALL COLUMNS YELLOW
            for row, product_data in enumerate(sample_data, start=1):
                for col, value in enumerate(product_data):
                    worksheet.write(row, col, value, yellow_format)
            
            # SET COLUMN WIDTHS
            column_widths = [15, 25, 18, 15, 15, 15, 18, 22, 15, 12, 12, 18, 20, 15]
            for col, width in enumerate(column_widths):
                worksheet.set_column(col, col, width)
            
            # ADD DATA VALIDATION
            MAX_ROW = 5000
            
            # BATCH NUMBER validation (1-999) - NOW REPRESENTS FILTER NUMBER
            worksheet.data_validation(f'A2:A{MAX_ROW}', {
                'validate': 'integer', 'criteria': 'between', 'minimum': 1, 'maximum': 999,
                'input_title': 'Batch Filter Number', 'input_message': 'Enter filter number (1=first batch, 2=second batch, etc.)',
                'error_title': 'Invalid Filter', 'error_message': 'Filter must be between 1-999'
            })
            
            # STOCK QUANTITY validation (≥ 0)
            worksheet.data_validation(f'C2:C{MAX_ROW}', {
                'validate': 'decimal', 'criteria': '>=', 'value': 0,
                'input_title': 'Stock Quantity', 'input_message': 'Enter quantity (≥ 0)',
                'error_title': 'Invalid Quantity', 'error_message': 'Quantity must be ≥ 0'
            })
            
            # ALL PRICE VALIDATIONS (≥ 0)
            price_columns = ['D', 'E', 'F', 'G', 'I']  # BUYING, SHIPPING, HANDLING, WHOLESALE, RETAIL
            for col in price_columns:
                worksheet.data_validation(f'{col}2:{col}{MAX_ROW}', {
                    'validate': 'decimal', 'criteria': '>=', 'value': 0,
                    'input_title': 'Price Validation', 'input_message': 'Enter price (≥ 0)',
                    'error_title': 'Invalid Price', 'error_message': 'Price must be ≥ 0'
                })
            
            # THRESHOLD VALIDATIONS
            worksheet.data_validation(f'H2:H{MAX_ROW}', {
                'validate': 'integer', 'criteria': '>=', 'value': 1,
                'input_title': 'Wholesale Threshold', 'input_message': 'Enter minimum quantity (≥ 1)',
                'error_title': 'Invalid Threshold', 'error_message': 'Threshold must be ≥ 1'
            })
            
            worksheet.data_validation(f'M2:M{MAX_ROW}', {
                'validate': 'integer', 'criteria': '>=', 'value': 0,
                'input_title': 'Low Stock Threshold', 'input_message': 'Enter warning level (≥ 0)',
                'error_title': 'Invalid Threshold', 'error_message': 'Threshold must be ≥ 0'
            })
            
            # RELATION VALIDATION
            worksheet.data_validation(f'L2:L{MAX_ROW}', {
                'validate': 'integer', 'criteria': '>=', 'value': 1,
                'input_title': 'Relation', 'input_message': 'Enter conversion factor (≥ 1)',
                'error_title': 'Invalid Relation', 'error_message': 'Relation must be ≥ 1'
            })
            
            # CONDITIONAL FORMATTING - ENHANCED
            # 1. EMPTY REQUIRED FIELDS - RED if empty but row has data
            required_columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M']
            for col in required_columns:
                worksheet.conditional_format(f'{col}2:{col}{MAX_ROW}', {
                    'type': 'formula', 
                    'criteria': f'=AND(ISBLANK({col}2), COUNTA($A2:$N2)>0)', 
                    'format': red_format
                })
            
            # 2. BUSINESS LOGIC WARNINGS - RED FOR SERIOUS ISSUES
            # WHOLESALE_PRICE < BUYING_PRICE - RED
            worksheet.conditional_format(f'G2:G{MAX_ROW}', {
                'type': 'formula',
                'criteria': '=AND(NOT(ISBLANK(G2)), NOT(ISBLANK(D2)), G2<D2)',
                'format': red_format
            })
            
            # RETAIL_PRICE < WHOLESALE_PRICE - RED
            worksheet.conditional_format(f'I2:I{MAX_ROW}', {
                'type': 'formula',
                'criteria': '=AND(NOT(ISBLANK(I2)), NOT(ISBLANK(G2)), I2<G2)',
                'format': red_format
            })
            
            # RETAIL_PRICE < BUYING_PRICE (SERIOUS WARNING) - RED
            worksheet.conditional_format(f'I2:I{MAX_ROW}', {
                'type': 'formula',
                'criteria': '=AND(NOT(ISBLANK(I2)), NOT(ISBLANK(D2)), I2<D2)',
                'format': red_format
            })
            
            # 3. NEGATIVE VALUES - RED
            numeric_columns = ['C', 'D', 'E', 'F', 'G', 'I']
            for col in numeric_columns:
                worksheet.conditional_format(f'{col}2:{col}{MAX_ROW}', {
                    'type': 'formula', 
                    'criteria': f'=AND(NOT(ISBLANK({col}2)), {col}2<0)', 
                    'format': red_format
                })
            
            # 4. STOCK BELOW THRESHOLD - YELLOW WARNING
            worksheet.conditional_format(f'C2:C{MAX_ROW}', {
                'type': 'formula',
                'criteria': '=AND(NOT(ISBLANK(C2)), NOT(ISBLANK(M2)), C2<M2)',
                'format': yellow_warning_format
            })

            # Enhanced data validation for expiry date with strict checks
            worksheet.data_validation(f'N2:N{MAX_ROW}', {
                'validate': 'custom',
                'value': (
                    '=AND('
                    'NOT(ISBLANK(N2)),'                                # Not empty
                    'IF(ISNUMBER(N2), N2>=TODAY(), DATEVALUE(N2)>=TODAY()),'  # Accept number or text
                    'YEAR(IF(ISNUMBER(N2), N2, DATEVALUE(N2)))<=YEAR(TODAY())+10'  # Year within limit
                    ')'
                ),
                'input_title': 'Expiry Date',
                'input_message': (
                    'Enter expiry date (YYYY-MM-DD)\n'
                    '• Must be today or a future date\n'
                    '• Cannot exceed 10 years from now\n\n'
                    'COLOR GUIDE:\n'
                    '🟥 RED = Invalid date (error)\n'
                    '🟦 BLUE = Valid date (safe)\n'
                    '🟩 GREEN = Expiring soon (within 30 days)'
                ),
                'error_title': 'Invalid Date',
                'error_message': 'Date not recognized or outside acceptable range'
            })

            # Red format for invalid dates (errors)
            worksheet.conditional_format(f'N2:N{MAX_ROW}', {
                'type': 'formula',
                'criteria': (
                    '=OR('
                    'AND(NOT(ISBLANK(N2)), NOT(ISNUMBER(N2)), ISERROR(DATEVALUE(N2))),'  # text but invalid
                    'AND(NOT(ISBLANK(N2)), IF(ISNUMBER(N2), N2<TODAY(), DATEVALUE(N2)<TODAY())),'  # past date
                    'AND(NOT(ISBLANK(N2)), YEAR(IF(ISNUMBER(N2), N2, DATEVALUE(N2)))>YEAR(TODAY())+10)'  # too far future
                    ')'
                ),
                'format': red_format
            })

            # Yellow warning for dates very close to today (within next 30 days)
            worksheet.conditional_format(f'N2:N{MAX_ROW}', {
                'type': 'formula',
                'criteria': (
                    '=AND('
                    'NOT(ISBLANK(N2)),'
                    'NOT(ISERROR(IF(ISNUMBER(N2), N2, DATEVALUE(N2)))),'
                    'IF(ISNUMBER(N2), N2, DATEVALUE(N2))>=TODAY(),'
                    'IF(ISNUMBER(N2), N2, DATEVALUE(N2))<=TODAY()+30'
                    ')'
                ),
                'format': workbook.add_format({'bg_color': "#34EA2E"}) # yellow_warning_format
            })

            # Blue format for valid dates that are safe (more than 30 days away)
            worksheet.conditional_format(f'N2:N{MAX_ROW}', {
                'type': 'formula',
                'criteria': (
                    '=AND('
                    'NOT(ISBLANK(N2)),'
                    'NOT(ISERROR(IF(ISNUMBER(N2), N2, DATEVALUE(N2)))),'
                    'IF(ISNUMBER(N2), N2, DATEVALUE(N2))>TODAY()+30,'  # More than 30 days away
                    'YEAR(IF(ISNUMBER(N2), N2, DATEVALUE(N2)))<=YEAR(TODAY())+10'
                    ')'
                ),
                'format': workbook.add_format({'bg_color': "#0964D3"})  # Light blue
            })

            workbook.close()


            # DISPLAY INSTRUCTIONS
            print(f"\n{Colors.BLUE}=== EXCEL TEMPLATE CREATED ==={Colors.RESET}")
            print(f"{Colors.GREEN}✓ Template: {filename}{Colors.RESET}")
            print(f"{Colors.GREEN}✓ Store: {self.current_store_name} ({self.current_store_code}){Colors.RESET}")
            print(f"\n{Colors.BLUE}📋 BATCH FILTER SYSTEM:{Colors.RESET}")
            print(f"{Colors.BLUE}• BATCH_NUMBER: Enter filter number (1, 2, 3, ...){Colors.RESET}")
            print(f"{Colors.BLUE}• 1 = First batch ever entered{Colors.RESET}")
            print(f"{Colors.BLUE}• 2 = Second batch ever entered{Colors.RESET}")
            print(f"{Colors.BLUE}• New number = Create new batch{Colors.RESET}")
            print(f"{Colors.BLUE}• System converts filter to actual batch name automatically{Colors.RESET}")
            print(f"\n{Colors.BLUE}🧮 AUTOMATIC RELATION CALCULATIONS:{Colors.RESET}")
            print(f"{Colors.BLUE}• Checks UNIT and BIG_UNIT fields for relation calculation{Colors.RESET}")
            print(f"{Colors.BLUE}• If UNIT ≠ BIG_UNIT and RELATION > 1, calculates values automatically{Colors.RESET}")
            print(f"{Colors.BLUE}• Buying Price, Shipping Cost, Handling Cost: Divided by relation{Colors.RESET}")
            print(f"{Colors.BLUE}• Stock Quantity, Low Stock Threshold: Multiplied by relation{Colors.RESET}")
            
            self.open_excel_file(filename)
            return filename
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error creating Excel template: {e}{Colors.RESET}")
            return None

    def validate_product_row(self, index, name, unit, stock_quantity, buying_price, retail_price, wholesale_price):
        """Enhanced validation for product row"""
        if not name:
            print(f"{Colors.RED}❌ Row {index+2}: NAME is required{Colors.RESET}")
            return False
        
        if not unit:
            print(f"{Colors.RED}❌ Row {index+2}: UNIT is required for '{name}'{Colors.RESET}")
            return False
        
        if retail_price < 0:
            print(f"{Colors.RED}❌ Row {index+2}: RETAIL_PRICE cannot be negative for '{name}'{Colors.RESET}")
            return False
        
        # Business logic warnings - RED for serious issues
        if wholesale_price < buying_price:
            print(f"{Colors.RED}❌ Row {index+2}: Wholesale price < Buying price for '{name}' - THIS IS A LOSS!{Colors.RESET}")
        
        if retail_price < wholesale_price:
            print(f"{Colors.RED}❌ Row {index+2}: Retail price < Wholesale price for '{name}' - THIS IS A LOSS!{Colors.RESET}")
        
        if retail_price < buying_price:
            print(f"{Colors.RED}❌ Row {index+2}: Retail price < Buying price for '{name}' - THIS IS A LOSS!{Colors.RESET}")
        
        return True

    def validate_and_import_data(self, excel_file):
        """Validate and import product data with MULTI-LEVEL hierarchy support"""
        try:
            if not self.current_store_code:
                print(f"{Colors.RED}❌ Please select a store first{Colors.RESET}")
                return False

            df = pd.read_excel(excel_file)
            self._last_df = df

            # 🆕 STEP 1: BUILD HIERARCHY ONCE (BEFORE processing rows)
            print(f"{Colors.BLUE}🔨 BUILDING PRODUCT HIERARCHY...{Colors.RESET}")
            product_hierarchy = self.build_product_hierarchy(df)
            
            success_count = 0
            error_count = 0
            update_count = 0

            print(f"\n{Colors.BLUE}=== VALIDATING AND IMPORTING DATA ==={Colors.RESET}")
            print(f"{Colors.BLUE}Store: {self.current_store_name} ({self.current_store_code}){Colors.RESET}")

            # Use transaction for all operations
            conn = sqlite3.connect(self.products_db)
            conn.execute("PRAGMA foreign_keys = ON;")

            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row.get('NAME')) or str(row.get('NAME', '')).strip() == '':
                        continue

                    # Convert row to dict
                    row_data = {}
                    for col in df.columns:
                        row_data[col] = row[col]

                    # 🆕 STEP 2: USE MULTI-LEVEL CALCULATION WITH PRE-BUILT HIERARCHY
                    calculated_values = self.check_and_calculate_relation_values(row_data, product_hierarchy)
                    stock_quantity, buying_price, shipping_cost, handling_cost, low_stock_threshold, is_child_unit = calculated_values

                    # CONTINUE WITH YOUR EXISTING BATCH PROCESSING LOGIC...
                    name = str(row.get('NAME', '')).strip()
                    unit = str(row.get('UNIT', '')).strip()

                    clean_name = self.clean_product_name(name)

                    image_filename = None
                    try:
                        image_filename = ask_image_file_dialog(clean_name, "images")
                        if image_filename:
                            print(f"{Colors.GREEN}✓ Image selected for {clean_name}: {image_filename}{Colors.RESET}")
                        else:
                            print(f"{Colors.BLUE}ℹ No image selected for {clean_name}{Colors.RESET}")
                    except Exception as e:
                        print(f"{Colors.YELLOW}⚠ Could not get image for {clean_name}: {e}{Colors.RESET}")
                    
                    # Your existing batch processing logic here...
                    filter_number = str(row.get('BATCH_NUMBER', '')).strip()
                    
                    # Determine if this is an update or new batch
                    is_update = False
                    actual_batch_name = None
                    
                    name_with_formated = f"{clean_name}({unit})" if unit else clean_name
                    if filter_number and filter_number.isdigit():
                        filter_num = int(filter_number)
                        sample_data = self.get_existing_batches_for_product(product_name=name_with_formated)
                        
                        total_existing_batches = 0
                        if sample_data is not None:
                            total_existing_batches = max(row[0] for row in sample_data)

                        # Check if filter number corresponds to existing batch
                        if 1 <= filter_num <= total_existing_batches:
                          
                            # UPDATE existing batch
                            is_update = True
                            for filter_num_batch, batch_number in sample_data:
                                if filter_num_batch == filter_num:
                                    actual_batch_name = batch_number
                                    break

                            print(f"{Colors.BLUE}ℹ Updating existing batch {filter_num}{Colors.RESET}")

                        else:
                            # NEW batch - generate new batch name
                            actual_batch_name = self.generate_batch_name(clean_name)
                            print(f"{Colors.GREEN}✓ Creating new batch {filter_num}: {actual_batch_name}{Colors.RESET}")
                    else:
                        # Invalid filter number - generate new batch
                        actual_batch_name = self.generate_batch_name(clean_name)
                        print(f"{Colors.YELLOW}⚠ Invalid filter number, creating new batch: {actual_batch_name}{Colors.RESET}")

                    # EXTRACT OTHER VALUES
                    big_unit = str(row.get('BIG_UNIT', '')).strip()
                    relation_input = row.get('RELATION_OF_UNITY', 1)
                    relation = 1.0
                    if not pd.isna(relation_input):
                        try:
                            relation = float(relation_input)
                            if relation <= 0:
                                relation = 1.0
                        except (ValueError, TypeError):
                            relation = 1.0

                    wholesale_price_input = row.get('WHOLESALE_PRICE', 0)
                    wholesale_price = 0.0
                    if not pd.isna(wholesale_price_input) and str(wholesale_price_input).strip() != '':
                        try:
                            wholesale_price = float(wholesale_price_input)
                        except (ValueError, TypeError):
                            wholesale_price = 0.0

                    retail_price_input = row.get('RETAIL_PRICE', 0)
                    retail_price = 0.0
                    if not pd.isna(retail_price_input) and str(retail_price_input).strip() != '':
                        try:
                            retail_price = float(retail_price_input)
                        except (ValueError, TypeError):
                            retail_price = 0.0

                    wholesale_threshold_input = row.get('WHOLESALE_THRESHOLD', 1)
                    wholesale_threshold = 1
                    if not pd.isna(wholesale_threshold_input):
                        try:
                            wholesale_threshold = int(wholesale_threshold_input)
                            if wholesale_threshold <= 0:
                                wholesale_threshold = 1
                        except (ValueError, TypeError):
                            wholesale_threshold = 1

                    expiry_date_input = row.get('EXPIRY_DATE', '')
                    expiry_date = None
                    if expiry_date_input and not pd.isna(expiry_date_input) and str(expiry_date_input).strip() != '':
                        date_validation = self.validate_expiry_date(str(expiry_date_input))
                        if date_validation.is_valid:
                            expiry_date = date_validation.value
                            if date_validation.message:
                                print(f"{Colors.YELLOW}⚠ Row {index+2}: {date_validation.message}{Colors.RESET}")
                        else:
                            print(f"{Colors.RED}❌ Row {index+2}: {date_validation.message}{Colors.RESET}")
                            error_count += 1
                            continue

                    # Format product name for database
                    formatted_name = f"{clean_name}({unit})" if unit else clean_name

                    # VALIDATION
                    if not self.validate_product_row(index, clean_name, unit, stock_quantity,
                                                    buying_price, retail_price, wholesale_price):
                        error_count += 1
                        continue

                    # Check if product exists
                    existing_product, price_exists = self.check_product_exists(formatted_name)

                    product_id = None
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM products WHERE name = ? AND store_id = ? LIMIT 1", 
                        (formatted_name, self.current_store_id)
                    )
                    res = cursor.fetchone()
                    if res:
                        product_id = res[0]

                    # Prepare product data
                    product_data = {
                        'name': formatted_name,
                        'clean_name': clean_name,
                        'stock_quantity': stock_quantity,
                        'buying_price': buying_price,
                        'shipping_cost': shipping_cost,
                        'handling_cost': handling_cost,
                        'wholesale_price': wholesale_price,
                        'wholesale_threshold': wholesale_threshold,
                        'retail_price': retail_price,
                        'low_stock_threshold': low_stock_threshold,
                        'expiry_date': expiry_date,
                        'unit': unit,
                        'big_unit': big_unit if big_unit else None,
                        'relation': relation,
                        'batch_name': actual_batch_name,
                        'filter_number': filter_number,
                        'is_update': is_update,
                        'is_child_unit': is_child_unit,
                        'image_filename': image_filename
                    }

                    # Insert or update using batch system WITH TRANSACTION
                    try:
                        conn.execute("BEGIN TRANSACTION")

                        if existing_product:
                            # Product exists - update with batch
                            result = self.update_existing_product_with_batch_transactional(
                                conn, product_data, existing_product[0], price_exists, is_update
                            )
                            if result:
                                update_count += 1
                                print(f"{Colors.GREEN}✓ Updated: {formatted_name} (Batch: {actual_batch_name}){Colors.RESET}")
                            else:
                                error_count += 1
                                conn.execute("ROLLBACK")
                                continue
                        else:
                            # New product - insert with batch
                            product_id = self.insert_new_product_with_batch_transactional(conn, product_data)
                            if product_id:
                                success_count += 1
                                print(f"{Colors.GREEN}✓ Added: {formatted_name} (Batch: {actual_batch_name}){Colors.RESET}")
                            else:
                                error_count += 1
                                conn.execute("ROLLBACK")
                                continue

                        conn.execute("COMMIT")

                    except Exception as e:
                        conn.execute("ROLLBACK")
                        print(f"{Colors.RED}❌ Row {index+2}: Transaction failed for '{clean_name}': {str(e)}{Colors.RESET}")
                        error_count += 1
                        continue

                except Exception as e:
                    product_name = str(row.get('NAME', 'Unknown')).strip()
                    print(f"{Colors.RED}❌ Row {index+2}: Error processing '{product_name}': {str(e)}{Colors.RESET}")
                    error_count += 1
                    continue

            if success_count > 0:
                try:
                    conn.execute("BEGIN TRANSACTION")
                    self.update_parent_product_ids(conn)
                    conn.execute("COMMIT")
                    print(f"{Colors.GREEN}✓ Successfully updated parent-child relationships{Colors.RESET}")
                except Exception as e:
                    conn.execute("ROLLBACK")
                    print(f"{Colors.RED}❌ Error updating parent-child relationships: {e}{Colors.RESET}")

            conn.close()

            # DISPLAY IMPORT SUMMARY
            self.display_import_summary(success_count, update_count, error_count)

            if success_count + update_count > 0 and error_count == 0:
                self.cleanup_excel_file(excel_file)

            return success_count + update_count > 0

        except Exception as e:
            print(f"{Colors.RED}❌ Error importing data: {e}{Colors.RESET}")
            return False

    def check_stock_quantity_changes_from_product_data(self, product_data_dict):
        """
        Check if stock quantities have changed between existing data and new product data
        Uses the same product_data structure from validate_and_import_data
        
        Args:
            product_data_dict: Single product_data dictionary from validate_and_import_data
            
        Returns: True if stock quantity changed, False if no changes
        """
      
        
        # Validate the dictionary has required fields
        if not isinstance(product_data_dict, dict) or 'name' not in product_data_dict or 'stock_quantity' not in product_data_dict:
            print(f"{Colors.RED}❌ Invalid product data format{Colors.RESET}")
            return True  # On error, assume there are changes to be safe
        
        try:
            if not self.current_store_code:
                print(f"{Colors.RED}❌ Please select a store first{Colors.RESET}")
                return False

            print(f"\n{Colors.BLUE}=== CHECKING STOCK QUANTITY CHANGES FROM PRODUCT DATA ==={Colors.RESET}")
            
            # STEP 1: Fetch existing stock quantities from database
            print(f"{Colors.BLUE}📊 Fetching existing stock data...{Colors.RESET}")
            existing_data = self.fetch_sample_products(limit=None)  # Fetch all products
            
            if not existing_data:
                print(f"{Colors.YELLOW}⚠ No existing products found in database{Colors.RESET}")
                return True  # No existing data, so consider it as "changed"
            
            # Create dictionary of existing stock quantities {product_name: stock_quantity}
            existing_stocks = {}
            for row in existing_data:
                if len(row) >= 3:  # Ensure row has enough columns
                    product_name = row[1]  # NAME is at index 1
                    stock_quantity = row[2] if row[2] != '' else 0  # STOCK_QUANTITY at index 2
                    existing_stocks[product_name] = stock_quantity
                    print(f"{Colors.BLUE}   - {product_name}: {stock_quantity}{Colors.RESET}")
            
            print(f"{Colors.GREEN}✓ Found {len(existing_stocks)} existing products{Colors.RESET}")
            
            # STEP 2: Process single product_data_dict
            print(f"{Colors.BLUE}📊 Processing new product data...{Colors.RESET}")
            
            product_name = product_data_dict['name']
            new_stock_quantity = product_data_dict.get('stock_quantity', 0)
            
            print(f"{Colors.BLUE}   - {product_name}: {new_stock_quantity}{Colors.RESET}")
            
            # STEP 3: Compare with existing data
            changes_detected = False
            
            if product_name in existing_stocks:
                existing_qty = existing_stocks[product_name]
                if existing_qty != new_stock_quantity:
                    print(f"{Colors.YELLOW}🔄 CHANGE DETECTED: {product_name}{Colors.RESET}")
                    print(f"{Colors.YELLOW}   From: {existing_qty} → To: {new_stock_quantity}{Colors.RESET}")
                    changes_detected = True
                else:
                    print(f"{Colors.GREEN}✓ No change for {product_name}: {existing_qty}{Colors.RESET}")
            else:
                # New product - consider as change
                print(f"{Colors.GREEN}🆕 NEW PRODUCT: {product_name}{Colors.RESET}")
                changes_detected = True
            
            # STEP 4: Display summary
            print(f"\n{Colors.BLUE}=== STOCK CHANGE SUMMARY ==={Colors.RESET}")
            print(f"{Colors.BLUE}📊 Products in database: {len(existing_stocks)}{Colors.RESET}")
            print(f"{Colors.BLUE}📊 Product being checked: {product_name}{Colors.RESET}")
            
            if changes_detected:
                print(f"{Colors.GREEN}✅ Stock quantity changes detected: TRUE{Colors.RESET}")
                return True
            else:
                print(f"{Colors.BLUE}ℹ No stock quantity changes detected: FALSE{Colors.RESET}")
                return False
                
        except Exception as e:
            print(f"{Colors.RED}❌ Error checking stock quantity changes: {e}{Colors.RESET}")
            import traceback
            traceback.print_exc()
            return True  # On error, assume there are changes to be safe

    def clean_product_name(self, name):
        """Clean product name by removing unit information"""
        # Remove common unit patterns from name
        import re
        patterns = [
            r'\s*\([^)]*\)\s*$',  # Remove anything in parentheses at the end
            r'\s*\[[^\]]*\]\s*$',  # Remove anything in brackets at the end
            r'\s*-\s*[^-]*$',      # Remove anything after last dash
        ]
        
        clean_name = name
        for pattern in patterns:
            clean_name = re.sub(pattern, '', clean_name).strip()
        
        return clean_name

    def update_existing_product_with_batch_transactional(self, conn, product_data, existing_product_id, price_exists, is_update):
        """Update existing product with batch handling - TRANSACTIONAL VERSION"""
        try:
            # cursor = conn.cursor()
            # sequence_number = self.get_next_sequence_number()
            # product_code = self.generate_product_code(sequence_number)
                
            cursor = conn.cursor()
            
            # ✅ FIRST CHECK IF PRODUCT ALREADY EXISTS AND GET ITS CODE
            cursor.execute(
                "SELECT id, product_code FROM products WHERE name = ? AND store_id = ? LIMIT 1",
                (product_data['name'], self.current_store_id)
            )
            existing_product = cursor.fetchone()
            
            if existing_product:
                # ✅ PRODUCT EXISTS - USE EXISTING PRODUCT CODE
                product_id = existing_product[0]
                product_code = existing_product[1]
            else:
                # ✅ NEW PRODUCT - GENERATE NEW CODE
                sequence_number = self.get_next_sequence_number()
                product_code = self.generate_product_code(sequence_number)
                product_id = None


            if is_update:
                # UPDATE existing batch - update stock batch record
                print("Updating existing batch...")
                return self.update_existing_batch_transactional(cursor, product_data, existing_product_id, price_exists, product_code)
            else:
                # NEW batch for existing product - create new stock batch
                print("Creating new batch for existing product...")
                return self.create_new_batch_for_existing_product_transactional(cursor, product_data, existing_product_id, price_exists, product_code)
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error updating product with batch: {e}{Colors.RESET}")
            raise
                

    def update_existing_batch_transactional(self, cursor, product_data, existing_product_id, price_exists, product_code):
        """Update an existing batch - TRANSACTIONAL VERSION"""
        try:
            # Update stock batch
            batch_query = """
                UPDATE stock_batches 
                SET quantity = ?, buying_price = ?, shipping_cost = ?, handling_cost = ?,
                    expected_margin = ?, total_expected_profit = ?, expiry_date = ?, original_quantity = ?, synced = 0
                WHERE product_id = ? AND batch_number = ? AND store_id = ?
            """
            
            # Calculate landed cost and margin
            landed_cost = product_data['buying_price'] + product_data['shipping_cost'] + product_data['handling_cost']
            retail_profit = product_data['retail_price'] - landed_cost
            wholesale_profit = product_data['wholesale_price'] - landed_cost

            def calculate_expected_margin():
                retail_ratio, wholesale_ratio = 0.7, 0.3
                expected_margin = (retail_profit * retail_ratio) + (wholesale_profit * wholesale_ratio)
                return expected_margin
            
            expected_margin = calculate_expected_margin()
            original_quantity = self.check_stock_quantity_changes_from_product_data(product_data_dict=product_data)
            if original_quantity == False:
                batch_query = """
                    UPDATE stock_batches 
                    SET quantity = ?, buying_price = ?, shipping_cost = ?, handling_cost = ?,
                        expected_margin = ?, total_expected_profit = ?, expiry_date = ?, synced = 0
                    WHERE product_id = ? AND batch_number = ? AND store_id = ?
                """
                batch_params = (
                    product_data['stock_quantity'],
                    product_data['buying_price'],
                    product_data['shipping_cost'],
                    product_data['handling_cost'],
                    expected_margin,
                    expected_margin * product_data['stock_quantity'],
                    product_data['expiry_date'],
                    existing_product_id,
                    product_data['batch_name'],
                    self.current_store_id
                )
            else:
                batch_query = """
                UPDATE stock_batches 
                SET quantity = ?, buying_price = ?, shipping_cost = ?, handling_cost = ?,
                    expected_margin = ?, total_expected_profit = ?, expiry_date = ?, original_quantity = ?, synced = 0
                WHERE product_id = ? AND batch_number = ? AND store_id = ?
            """
                batch_params = (
                    product_data['stock_quantity'],
                    product_data['buying_price'],
                    product_data['shipping_cost'],
                    product_data['handling_cost'],
                    expected_margin,
                    expected_margin * product_data['stock_quantity'],
                    product_data['expiry_date'],
                    product_data['stock_quantity'],
                    existing_product_id,
                    product_data['batch_name'],
                    self.current_store_id
                )
            cursor.execute(batch_query, batch_params)
            
            if cursor.rowcount > 0:
                # Update product stock
                
                cursor.execute("""
                    SELECT COALESCE(SUM(quantity), 0)
                    FROM stock_batches
                    WHERE product_id = ? AND store_id = ?
                """, (existing_product_id, self.current_store_id))
                total_stock = cursor.fetchone()[0] or 0

                # Update product stock using total from batches
                product_query = """
                    UPDATE products 
                    SET stock_quantity = ?, 
                        low_stock_threshold = ?, 
                        updated_at = datetime('now'),
                        synced = 0
                    WHERE id = ?
                """
                product_params = (
                    total_stock,
                    product_data['low_stock_threshold'],
                    existing_product_id
                )
                cursor.execute(product_query, product_params)
                # Update prices to use LAST BATCH pricing
                if price_exists:
                    price_query = """
                        UPDATE store_product_prices 
                        SET retail_price = ?, wholesale_price = ?, wholesale_threshold = ?, synced = 0
                        WHERE product_id = ? AND store_id = ?
                    """
                    price_params = (
                        product_data['retail_price'],
                        product_data['wholesale_price'],
                        product_data['wholesale_threshold'],
                        existing_product_id,
                        self.current_store_id
                    )
                else:
                    price_query = """
                        INSERT INTO store_product_prices 
                        (store_id, product_id, product_code, retail_price, wholesale_price, wholesale_threshold)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    price_params = (
                        self.current_store_id,
                        existing_product_id,
                        product_code,
                        product_data['retail_price'],
                        product_data['wholesale_price'],
                        product_data['wholesale_threshold']
                    )
                
                cursor.execute(price_query, price_params)
                
                return True
                
            return False
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error updating existing batch: {e}{Colors.RESET}")
            raise

    def create_new_batch_for_existing_product_transactional(self, cursor, product_data, existing_product_id, price_exists, product_code):
        """Create new batch for existing product - TRANSACTIONAL VERSION"""
        try:
            # Update product stock (add to existing)
            product_query = """
                UPDATE products 
                SET stock_quantity = stock_quantity + ?, low_stock_threshold = ?,
                    updated_at = datetime('now'), synced = 0
                WHERE id = ?
            """
            product_params = (
                product_data['stock_quantity'], 
                product_data['low_stock_threshold'],
                existing_product_id
            )
            
            cursor.execute(product_query, product_params)
            
            if cursor.rowcount > 0:
                # Update prices to use LAST BATCH pricing
                if price_exists:
                    price_query = """
                        UPDATE store_product_prices 
                        SET retail_price = ?, wholesale_price = ?, wholesale_threshold = ?, synced = 0
                        WHERE product_id = ? AND store_id = ?
                    """
                    price_params = (
                        product_data['retail_price'],
                        product_data['wholesale_price'],
                        product_data['wholesale_threshold'],
                        existing_product_id,
                        self.current_store_id
                    )
                else:
                    price_query = """
                        INSERT INTO store_product_prices 
                        (store_id, product_id, product_code, retail_price, wholesale_price, wholesale_threshold)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """
                    price_params = (
                        self.current_store_id,
                        existing_product_id,
                        product_code,
                        product_data['retail_price'],
                        product_data['wholesale_price'],
                        product_data['wholesale_threshold']
                    )
                
                cursor.execute(price_query, price_params)
                
                # Create new stock batch
                batch_result = self.create_stock_batch_transactional(cursor, existing_product_id, product_code, product_data)
                return batch_result
                
            return False
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error creating new batch for existing product: {e}{Colors.RESET}")
            raise

    def insert_new_product_with_batch_transactional(self, conn, product_data):
        try:
            cursor = conn.cursor()
            sequence_number = self.get_next_sequence_number()
            product_code = self.generate_product_code(sequence_number)
            
            # Insert into products table
            query = """
                INSERT INTO products (
                    product_code, name, store_id, store_code, sequence_number,
                    stock_quantity, low_stock_threshold,
                    relation_to_parent, unit, big_unit,image, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?, datetime('now'))
            """
            
            params = (
                product_code, 
                product_data['name'], 
                self.current_store_id,
                self.current_store_code, 
                sequence_number, 
                product_data['stock_quantity'],
                product_data['low_stock_threshold'], 
                product_data['relation'],  # relation_to_parent
                product_data['unit'],
                product_data['big_unit'],
                product_data.get('image_filename')
            )
            
            cursor.execute(query, params)
            product_id = cursor.lastrowid
            
            if product_id:
                # Insert prices using last batch pricing
                price_query = """
                    INSERT INTO store_product_prices (
                        store_id, product_id, product_code, retail_price,
                        wholesale_price, wholesale_threshold
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """
                price_params = (
                    self.current_store_id, 
                    product_id, 
                    product_code,
                    product_data['retail_price'],
                    product_data['wholesale_price'],
                    product_data['wholesale_threshold']
                )
                cursor.execute(price_query, price_params)
                
                # Create stock batch
                batch_result = self.create_stock_batch_transactional(cursor, product_id, product_code, product_data)
                if batch_result:
                    return product_id
                else:
                    # This will trigger rollback in calling function
                    raise Exception("Failed to create stock batch")
                
            return False
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error inserting new product with batch: {e}{Colors.RESET}")
            raise

    def update_parent_product_ids(self, conn):
        """Update parent_product_id for all child products after all inserts are done"""
        try:
            cursor = conn.cursor()
            
            # Find all child products that need parent_product_id
            cursor.execute("""
                SELECT id, name, big_unit, relation_to_parent 
                FROM products 
                WHERE store_id = ? AND big_unit IS NOT NULL AND big_unit != '' AND parent_product_id IS NULL
            """, (self.current_store_id,))
            
            child_products = cursor.fetchall()
            updated_count = 0
            
            for child_id, child_name, big_unit, relation in child_products:
                # Extract clean name from formatted name (remove unit part)
                clean_name = child_name.split('(')[0].strip() if '(' in child_name else child_name
                
                # Find parent product ID
                parent_id = self.find_parent_product_id(clean_name, big_unit)
                if parent_id and child_id != parent_id:
                    # Update child product with parent_product_id
                    cursor.execute("""
                        UPDATE products 
                        SET parent_product_id = ? 
                        WHERE id = ? AND store_id = ?
                    """, (parent_id, child_id, self.current_store_id))
                    
                    print(f"{Colors.GREEN}✓ Updated parent_product_id: {parent_id} for child: {child_name}{Colors.RESET}")
                    updated_count += 1

            print(f"{Colors.BLUE}ℹ Updated {updated_count} child products with parent IDs{Colors.RESET}")
            print(f"Updated count: {updated_count}")
            return updated_count
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error updating parent product IDs: {e}{Colors.RESET}")
            raise

    def generate_batch_name(self, product_name):
        """Generate unique batch name with product abbreviation, date and nanoseconds"""
        # Get current time with nanoseconds
        import time
        timestamp_ns = str(time.time_ns())[-9:]  # Last 9 digits for nanoseconds
        
        # Get date in YYYYMMDD format
        date_str = datetime.now().strftime("%Y%m%d")
        
        return f"BTCH_{date_str}_{timestamp_ns}"

    def create_stock_batch_transactional(self, cursor, product_id, product_code, product_data):
        """Create stock batch with unique name for each product - TRANSACTIONAL VERSION"""
        try:
            # Calculate landed cost and margin
            cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
            product_exists = cursor.fetchone()
            if not product_exists:
                print(f"{Colors.RED}❌ CRITICAL: Product ID {product_id} not found in database{Colors.RESET}")
                return False
            landed_cost = product_data['buying_price'] + product_data['shipping_cost'] + product_data['handling_cost']
            expected_margin = product_data['retail_price'] - landed_cost
            
            query = """
                INSERT INTO stock_batches (
                    product_id, product_code, store_id, store_code, batch_number,
                    quantity, buying_price, shipping_cost, handling_cost,
                    expected_margin, total_expected_profit, received_date, expiry_date, original_quantity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)
            """
            params = (
                product_id, product_code, self.current_store_id, self.current_store_code, product_data['batch_name'],
                product_data['stock_quantity'], product_data['buying_price'],
                product_data['shipping_cost'], product_data['handling_cost'],
                expected_margin, expected_margin * product_data['stock_quantity'],
                product_data['expiry_date'],
                product_data['stock_quantity']

            )
            
            cursor.execute(query, params)
            if cursor.rowcount > 0:
                print(f"{Colors.GREEN}✓ Created stock batch for {product_data['clean_name']}: {product_data['batch_name']}{Colors.RESET}")
                return True
            return False
            
        except Exception as e:
            print(f"{Colors.RED}❌ Error creating stock batch: {e}{Colors.RESET}")
            raise

    def execute_query(self, query, params=(), fetch=False):
        """Execute SQL query on database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
                self.conn.commit()
                return result
            else:
                self.conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            print(f"{Colors.RED}❌ Database error: {str(e)}{Colors.RESET}")
            return None

    def display_import_summary(self, success_count, update_count, error_count):
        """Display import summary with statistics"""
        print(f"\n{Colors.BLUE}=== IMPORT SUMMARY ==={Colors.RESET}")
        print(f"{Colors.GREEN}✓ Successfully added: {success_count}{Colors.RESET}")
        print(f"{Colors.BLUE}✓ Updated: {update_count}{Colors.RESET}")
        print(f"{Colors.RED}❌ Errors: {error_count}{Colors.RESET}")
        
        total = success_count + update_count + error_count
        print(f"{Colors.BLUE}📊 Total processed: {total}{Colors.RESET}")
        
        if success_count + update_count > 0:
            print(f"{Colors.GREEN}🎉 Import completed with batch filter system!{Colors.RESET}")

    def cleanup_excel_file(self, excel_file):
        """Delete Excel file after successful import"""
        try:
            os.remove(excel_file)
            print(f"{Colors.GREEN}✓ Excel file deleted for security{Colors.RESET}")
        except:
            print(f"{Colors.YELLOW}⚠ Could not delete Excel file{Colors.RESET}")

    def open_excel_file(self, file_path):
        """Open Excel file using appropriate method"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            else:  # Linux/macOS
                subprocess.call(['open', file_path] if sys.platform == 'darwin' else ['xdg-open', file_path])
            print(f"{Colors.GREEN}✓ File opened: {file_path}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}❌ Error opening file: {e}{Colors.RESET}")

    def view_existing_data(self):
        """View existing products in the current store with batch information"""
        try:
            if not self.current_store_code:
                print(f"{Colors.RED}❌ Please select a store first{Colors.RESET}")
                return
            
            conn = sqlite3.connect(self.products_db)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT p.product_code, p.name, p.stock_quantity, p.low_stock_threshold,
                       spp.retail_price, spp.wholesale_price, spp.wholesale_threshold,
                       sb.batch_number, sb.buying_price, sb.shipping_cost, sb.handling_cost,
                       sb.received_date
                FROM products p
                JOIN store_product_prices spp ON p.id = spp.product_id
                LEFT JOIN stock_batches sb ON p.id = sb.product_id
                WHERE p.store_id = ?
                ORDER BY p.name, sb.received_date ASC
            ''', (self.STORE_ID,))
            
            products = cursor.fetchall()
            conn.close()
            
            print(f"\n{Colors.BLUE}=== EXISTING PRODUCTS IN {self.current_store_name} ==={Colors.RESET}")
            
            if not products:
                print(f"{Colors.YELLOW}No products found in this store{Colors.RESET}")
                return
            
            current_product = None
            filter_counter = 0
            
            for product in products:
                code, name, stock, low_threshold, retail, wholesale, w_threshold, batch, buying, shipping, handling, received_date = product
                
                if name != current_product:
                    if current_product is not None:
                        print()
                    current_product = name
                    filter_counter = 1
                    print(f"{Colors.BLUE}{name} ({code}){Colors.RESET}")
                    print(f"  Stock: {stock} (Threshold: {low_threshold})")
                    print(f"  Current Retail: {retail:,} | Current Wholesale: {wholesale:,} (Threshold: {w_threshold})")
                else:
                    filter_counter += 1
                
                landed_cost = (buying or 0) + (shipping or 0) + (handling or 0)
                received = received_date[:10] if received_date else "Unknown"
                print(f"  Filter {filter_counter}: Batch '{batch}' | Buying {buying or 0:,} | Landed Cost: {landed_cost:,.2f} | Received: {received}")
                
        except Exception as e:
            print(f"{Colors.RED}❌ Error viewing data: {e}{Colors.RESET}")

    def main_menu(self):
        """Display main menu and handle user interactions"""
        print(f"\n{Colors.BLUE}=== ENHANCED EXCEL IMPORT WITH BATCH FILTER SYSTEM ==={Colors.RESET}")
        
        if not self.check_required_tables():
            return
        
        while True:
            print(f"\n{Colors.BLUE}=== MAIN MENU ==={Colors.RESET}")
            if self.current_store_name:
                print(f"{Colors.GREEN}Current Store: {self.current_store_name} ({self.current_store_code}){Colors.RESET}")
            else:
                print(f"{Colors.YELLOW}No store selected{Colors.RESET}")
            
            print("1. Select Store")
            print("2. Create Excel Template")
            print("3. Import Data from Excel")
            print("4. View Existing Products")
            print("5. Exit")
            
            choice = input(f"\n{Colors.BLUE}Select option (1-5): {Colors.RESET}").strip()
            
            if choice == '1':
                self.select_store()
            
            elif choice == '2':
                if not self.current_store_code:
                    print(f"{Colors.RED}❌ Please select a store first{Colors.RESET}")
                    continue
                self.export_or_create_template()
            
            elif choice == '3':
                if not self.current_store_code:
                    print(f"{Colors.RED}❌ Please select a store first{Colors.RESET}")
                    continue
                excel_file = ask_excel_file_dialog()
                if not excel_file:
                    print(f"{Colors.YELLOW}⚠ No file selected{Colors.RESET}")
                    continue
                if os.path.exists(excel_file):
                    self.validate_and_import_data(excel_file)
                else:
                    print(f"{Colors.RED}❌ File does not exist: {excel_file}{Colors.RESET}")

            elif choice == '4':
                self.view_existing_data()
            
            elif choice == '5':
                print(f"{Colors.GREEN}Thank you for using the Enhanced Excel Import System!{Colors.RESET}")
                break
            
            else:
                print(f"{Colors.RED}❌ Invalid option{Colors.RESET}")

if __name__ == "__main__":
    try:
        processor = ExcelProcessor()
        processor.main_menu()
    except Exception as e:
        print(f"{Colors.RED}❌ Program encountered an error: {e}{Colors.RESET}")
        input("Press Enter to close...")