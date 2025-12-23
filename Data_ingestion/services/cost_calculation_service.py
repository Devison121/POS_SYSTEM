# cost_calculation_service.py
# Service for cost calculations and margin analysis

import os
import sqlite3
from typing import Optional, Dict, Any
from dataclasses import dataclass
from models.product import ProductCosts, SalesStats
from utils.color_output import Colors
from utils.helpers import get_sales_db_path

@dataclass
class CostCalculationService:
    """Service for cost calculations and margin analysis"""
    
    @staticmethod
    def get_default_sales_stats() -> SalesStats:
        """Return default sales ratios for new products"""
        return SalesStats()
    
    @staticmethod
    
    #This get_sales_stats method fetches actual sales data for a given product from the sales database.
    # It calculates total sales, quantities sold in retail and wholesale, and their respective revenues.
    # But we need to change this method to insure that it use XGBoost / LightGBM or any other ML model to predict sales stats instead of fetching from DB.
    def get_sales_stats(product_id: int) -> SalesStats:
        """
        Fetch actual sales data for a product from sales database
        """
        try:
            if not product_id or product_id <= 0:
                return CostCalculationService.get_default_sales_stats()
                
            sales_db_path = get_sales_db_path()
            if not os.path.exists(sales_db_path):
                print(f"{Colors.YELLOW}⚠ Sales database not found at {sales_db_path}{Colors.RESET}")
                return CostCalculationService.get_default_sales_stats()
                
            conn = sqlite3.connect(sales_db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sale_items'")
            if not cursor.fetchone():
                print(f"{Colors.YELLOW}⚠ sale_items table not found in sales database{Colors.RESET}")
                conn.close()
                return CostCalculationService.get_default_sales_stats()

            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_sales,
                    SUM(quantity) AS total_quantity,
                    SUM(CASE WHEN is_wholesale = 1 THEN quantity ELSE 0 END) AS wholesale_quantity,
                    SUM(CASE WHEN is_wholesale = 0 THEN quantity ELSE 0 END) AS retail_quantity,
                    SUM(CASE WHEN is_wholesale = 1 THEN quantity * unit_price ELSE 0 END) AS wholesale_revenue,
                    SUM(CASE WHEN is_wholesale = 0 THEN quantity * unit_price ELSE 0 END) AS retail_revenue
                FROM sale_items
                WHERE product_id = ?
            """, (product_id,))

            data = cursor.fetchone()
            conn.close()

            if not data or data[0] is None:
                return CostCalculationService.get_default_sales_stats()

            total_sales = int(data[0] or 0)
            total_qty = float(data[1] or 0)
            wholesale_qty = float(data[2] or 0)
            retail_qty = float(data[3] or 0)
            wholesale_rev = float(data[4] or 0)
            retail_rev = float(data[5] or 0)

            if total_qty == 0:
                return CostCalculationService.get_default_sales_stats()

            retail_ratio = retail_qty / total_qty
            wholesale_ratio = wholesale_qty / total_qty

            print(f"\n{Colors.CYAN}📊 ACTUAL SALES DATA FOR PRODUCT {product_id}:{Colors.RESET}")
            print(f"{Colors.CYAN}  Total Quantity Sold: {total_qty}{Colors.RESET}")
            print(f"{Colors.CYAN}  Retail Sales: {retail_qty:.0f} units ({retail_ratio:.1%}){Colors.RESET}")
            print(f"{Colors.CYAN}  Wholesale Sales: {wholesale_qty:.0f} units ({wholesale_ratio:.1%}){Colors.RESET}")

            return SalesStats(
                total_sales=total_sales,
                total_quantity=total_qty,
                retail_ratio=retail_ratio,
                wholesale_ratio=wholesale_ratio,
                retail_revenue=retail_rev,
                wholesale_revenue=wholesale_rev
            )
            
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Warning: Could not fetch sales data: {e}{Colors.RESET}")
            return CostCalculationService.get_default_sales_stats()
    
    @staticmethod
    def calculate_expected_margin(retail_price: float, wholesale_price: float, landed_cost: float, 
                                product_id: Optional[int] = None, is_largest_unit: bool = True) -> Optional[ProductCosts]:
        """
        Inahesabu faida (retail, wholesale, na weighted gross margin)
        ikizingatia data halisi ya mauzo kutoka SALES_DB.
        """
        try:
            # Initialize with default ratios
            retail_ratio, wholesale_ratio = 0.7, 0.3
            use_actual_data = False
            
            #  stage 1: Take actual sales ratios if available and valid
            if product_id and product_id > 0:
                sales_stats = CostCalculationService.get_sales_stats(product_id)
                retail_ratio = sales_stats.retail_ratio
                wholesale_ratio = sales_stats.wholesale_ratio
                
                # Make sure we have some sales data
                total_quantity = sales_stats.total_quantity
                
                if total_quantity > 0:
                    use_actual_data = True
                    print(f"\n{Colors.GREEN}🎯 USING ACTUAL SALES RATIOS:{Colors.RESET}")
                    print(f"{Colors.GREEN}  → Retail: {retail_ratio:.1%} ({retail_ratio*100:.0f}%){Colors.RESET}")
                    print(f"{Colors.GREEN}  → Wholesale: {wholesale_ratio:.1%} ({wholesale_ratio*100:.0f}%){Colors.RESET}")
                    print(f"{Colors.GREEN}  → Based on {total_quantity} units sold{Colors.RESET}")
                else:
                    print(f"\n{Colors.YELLOW}📝 No sales data yet - Using default ratios{Colors.RESET}")
            else:
                # if new product use default ratios
                print(f"\n{Colors.YELLOW}📝 New product - Using default ratios (Retail=70%, Wholesale=30%){Colors.RESET}")

            # stage 2: Calculate profits
            retail_profit = retail_price - landed_cost
            wholesale_profit = wholesale_price - landed_cost

            # Weighted average margin kwa msingi wa data ya mauzo
            expected_margin = (retail_profit * retail_ratio) + (wholesale_profit * wholesale_ratio)

            # stage 3: Output results
            print(f"{Colors.GREEN}💰 PROFIT CALCULATION:{Colors.RESET}")
            print(f"{Colors.GREEN}  - Retail Profit: {retail_profit:.2f} (Price: {retail_price} - Cost: {landed_cost}){Colors.RESET}")
            print(f"{Colors.GREEN}  - Wholesale Profit: {wholesale_profit:.2f} (Price: {wholesale_price} - Cost: {landed_cost}){Colors.RESET}")
            print(f"{Colors.GREEN}  - Expected Weighted Margin: {expected_margin:.2f}{Colors.RESET}")

            return ProductCosts(
                retail_price=retail_price,
                wholesale_price=wholesale_price,
                buying_price=landed_cost,
                landed_cost=landed_cost,
                retail_profit=retail_profit,
                wholesale_profit=wholesale_profit,
                expected_margin=expected_margin,
                retail_ratio=retail_ratio,
                wholesale_ratio=wholesale_ratio,
                used_actual_data=use_actual_data
            )

        except Exception as e:
            print(f"{Colors.RED}❌ Error calculating expected margin: {e}{Colors.RESET}")
            return None