# main.py
# Main module to run the POS system boss menu

import sys
from pathlib import Path

# Ensure POS_SYSTEM package root is on sys.path
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    from sellers import add_user_by_boss, view_sellers, delete_user_by_boss
    from debts import pay_debt, view_debts
    from store import create_store, switch_store
    from delete import delete_data
    from views import view_stock, view_sales, view_tables, view_reports, view_sales_by_seller
    from register_user_for_login import Colors
except Exception:
    from sellers import add_user_by_boss, view_sellers, delete_user_by_boss
    from POS_SYSTEM.Core_business_logic.debts import pay_debt, view_debts
    from POS_SYSTEM.Core_business_logic.store import create_store, switch_store
    from POS_SYSTEM.Core_business_logic.delete import delete_data
    from POS_SYSTEM.Core_business_logic.views import view_stock, view_sales, view_tables, view_reports, view_sales_by_seller
    from POS_SYSTEM.Core_business_logic.register_user_for_login import Colors

def boss_menu(current_user):
    """Display boss menu and handle choices"""
    while True:
        print(f"\n{Colors.BLUE}=== BOSS MENU ==={Colors.RESET}")
        print("1. View Stock")
        print("2. View Sales")
        print("3. View Reports")
        print("4. View Tables")
        print("5. View Sales by Seller")
        print("6. View Debts")
        print("7. Pay Debt")
        print("8. Add Seller")
        print("9. View Sellers")
        print("10. Delete Seller")
        print("11. Create Store")
        print("12. Switch Store")
        print("13. Delete Data")
        print("14. Logout")
        
        choice = input("Choose an option: ").strip()
        
        if choice == "1":
            view_stock(current_user)
        elif choice == "2":
            view_sales(current_user)
        elif choice == "3":
            view_reports(current_user)
        elif choice == "4":
            view_tables(current_user)
        elif choice == "5":
            view_sales_by_seller(current_user)
        elif choice == "6":
            view_debts(current_user)
        elif choice == "7":
            pay_debt(current_user)
        elif choice == "8":
            add_user_by_boss(current_user)
        elif choice == "9":
            view_sellers(current_user)
        elif choice == "10":
            delete_user_by_boss(current_user)
        elif choice == "11":
            create_store(current_user)
        elif choice == "12":
            switch_store(current_user)
        elif choice == "13":
            delete_data(current_user)
        elif choice == "14":
            print(f"{Colors.GREEN}Logging out...{Colors.RESET}")
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please try again.{Colors.RESET}")

if __name__ == "__main__":
    # Example usage - you would integrate this with your login system
    print("This module contains the business logic functions.")
    print("Import these functions in your main application.")
