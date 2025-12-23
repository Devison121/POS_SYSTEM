# debts.py
"""
Module to manage debts in the POS system
"""

import sys
from pathlib import Path
import sqlite3
from datetime import datetime

# Add the parent directory to path for imports
CURRENT_DIR = Path(__file__).parent
PARENT_DIR = CURRENT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

try:
    from Databases.database_connection import get_db_connection, DEBTS_DB, SALES_DB, INVENTORY_DB
    from Core_busness_logic.register_user_for_login import Colors
except ImportError as e:
    print(f"Import error: {e}")
    # Define Colors class if import fails
    class Colors:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        RESET = '\033[0m'

# Function to pay debt for a debtor
def pay_debt(current_user):
    conn_debts = get_db_connection(DEBTS_DB)
    conn_inventory = get_db_connection(INVENTORY_DB)
    
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can manage debt payments.{Colors.RESET}")
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
        
        print(f"\n=== Pay Debt for Store: {store['name']} ===")
        
        # Aggregate debts by debtor
        cursor = conn_debts.execute("""
            SELECT debtor_name, debtor_phone, SUM(amount_owed) as total_amount_owed
            FROM debts 
            WHERE store_id = ?
            GROUP BY debtor_name, debtor_phone
        """, (store_id,))
        
        debtor_summary = cursor.fetchall()
        
        if not debtor_summary:
            print(f"{Colors.RED}No debts available to pay.{Colors.RESET}")
            return
        
        # Display debtor summary
        print("\nAvailable Debtors:")
        for i, debtor in enumerate(debtor_summary):
            print(f"{i+1}. {debtor['debtor_name']} ({debtor['debtor_phone']}) - Total: {debtor['total_amount_owed']}")
        
        # Prompt for debtor selection
        choice = input("\nEnter debtor ID, full/partial name, or 'q' to quit: ").strip()
        if choice.lower() == 'q':
            return
        
        selected_debtor = None
        if choice.isdigit():
            debtor_id = int(choice) - 1
            if 0 <= debtor_id < len(debtor_summary):
                selected_debtor = debtor_summary[debtor_id]
        else:
            # Search by name
            matching_debtors = [
                debtor for debtor in debtor_summary
                if choice.lower() in debtor['debtor_name'].lower()
            ]
            if len(matching_debtors) == 1:
                selected_debtor = matching_debtors[0]
            elif len(matching_debtors) > 1:
                print(f"{Colors.RED}Multiple debtors match '{choice}'. Please use ID or exact name.{Colors.RESET}")
                return
            else:
                print(f"{Colors.RED}No debtors found matching '{choice}'.{Colors.RESET}")
                return
        
        if selected_debtor:
            print(f"\n=== Paying Debt for {selected_debtor['debtor_name']} ({selected_debtor['debtor_phone']}) ===")
            print(f"Total Amount Owed: {selected_debtor['total_amount_owed']}")
            
            try:
                payment_amount = float(input("Enter payment amount (0 for full payment): ").strip())
                
                if payment_amount < 0:
                    print(f"{Colors.RED}Payment amount cannot be negative.{Colors.RESET}")
                    return
                
                if payment_amount == 0:
                    payment_amount = selected_debtor['total_amount_owed']
                
                if payment_amount > selected_debtor['total_amount_owed']:
                    print(f"{Colors.RED}Payment amount cannot exceed total amount owed ({selected_debtor['total_amount_owed']}).{Colors.RESET}")
                    return
                
                # Fetch all debt records for the selected debtor
                cursor = conn_debts.execute("""
                    SELECT id, amount_owed 
                    FROM debts 
                    WHERE store_id = ? AND debtor_name = ? AND debtor_phone = ?
                    ORDER BY created_at
                """, (store_id, selected_debtor['debtor_name'], selected_debtor['debtor_phone']))
                
                debts = cursor.fetchall()
                
                # Distribute payment across debts (FIFO)
                remaining_payment = payment_amount
                
                for debt in debts:
                    if remaining_payment <= 0:
                        break
                    
                    if remaining_payment >= debt['amount_owed']:
                        payment_for_debt = debt['amount_owed']
                        conn_debts.execute("DELETE FROM debts WHERE id = ?", (debt['id'],))
                    else:
                        payment_for_debt = remaining_payment
                        conn_debts.execute("UPDATE debts SET amount_owed = amount_owed - ?,synced = 0 WHERE id = ?", 
                                         (payment_for_debt, debt['id']))
                    
                    remaining_payment -= payment_for_debt
                
                # Record payment in debt_payments table
                if payment_amount > 0:
                    # Get the first debt ID for reference
                    first_debt_id = debts[0]['id'] if debts else None
                    
                    if first_debt_id:
                        conn_debts.execute("""
                            INSERT INTO debt_payments (debt_id, amount, store_id, store_code, user_id, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (first_debt_id, payment_amount, store_id, current_user['current_store_code'], 
                             current_user['id'], datetime.now().isoformat()))
                
                conn_debts.commit()
                
                if remaining_payment == 0 and payment_amount == selected_debtor['total_amount_owed']:
                    print(f"{Colors.GREEN}All debts for {selected_debtor['debtor_name']} fully paid and removed.{Colors.RESET}")
                else:
                    remaining_total = selected_debtor['total_amount_owed'] - payment_amount
                    print(f"{Colors.GREEN}Payment of {payment_amount} processed for {selected_debtor['debtor_name']}. Remaining: {remaining_total}{Colors.RESET}")
                
            except ValueError:
                print(f"{Colors.RED}Invalid input. Payment amount must be a number.{Colors.RESET}")
                
    except sqlite3.Error as e:
        conn_debts.rollback()
        print(f"{Colors.RED}Error processing debt payment: {e}{Colors.RESET}")
    finally:
        conn_debts.close()
        conn_inventory.close()

def view_debts(current_user):
    """
    Display all debts for the current store with debtor details.
    Only accessible by users with BOSS role.
    """
    conn_debts = get_db_connection(DEBTS_DB)
    conn_inventory = get_db_connection(INVENTORY_DB)
    
    try:
        if current_user['role'] != 'boss':
            print(f"{Colors.RED}Only bosses can view debts.{Colors.RESET}")
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
        
        print(f"\n=== Debts for Store: {store['name']} ===")
        print("=== List of Debtors ===")
        
        # Aggregate debts by debtor
        cursor = conn_debts.execute("""
            SELECT debtor_name, debtor_phone, SUM(amount_owed) as total_amount_owed
            FROM debts 
            WHERE store_id = ?
            GROUP BY debtor_name, debtor_phone
        """, (store_id,))
        
        debtor_summary = cursor.fetchall()
        
        if not debtor_summary:
            print(f"{Colors.RED}No debts found.{Colors.RESET}")
            return
        
        # Display debtor summary
        for i, debtor in enumerate(debtor_summary):
            print(f"{i+1}. {debtor['debtor_name']} ({debtor['debtor_phone']}) - Total: {debtor['total_amount_owed']}")
        
        # Prompt for debtor selection
        while True:
            choice = input("\nEnter debtor ID, full/partial name, or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return
            
            selected_debtor = None
            if choice.isdigit():
                debtor_id = int(choice) - 1
                if 0 <= debtor_id < len(debtor_summary):
                    selected_debtor = debtor_summary[debtor_id]
            else:
                # Search by name
                matching_debtors = [
                    debtor for debtor in debtor_summary
                    if choice.lower() in debtor['debtor_name'].lower()
                ]
                if len(matching_debtors) == 1:
                    selected_debtor = matching_debtors[0]
                elif len(matching_debtors) > 1:
                    print(f"{Colors.RED}Multiple debtors match '{choice}'. Please use ID or exact name.{Colors.RESET}")
                    continue
                else:
                    print(f"{Colors.RED}No debtors found matching '{choice}'.{Colors.RESET}")
                    continue
            
            if selected_debtor:
                print(f"\n=== Debt Details for {selected_debtor['debtor_name']} ({selected_debtor['debtor_phone']}) ===")
                
                # Get detailed debt records
                cursor = conn_debts.execute("""
                    SELECT d.id, d.sale_id, d.amount_owed, d.created_at
                    FROM debts d
                    WHERE d.store_id = ? AND d.debtor_name = ? AND d.debtor_phone = ?
                    ORDER BY d.created_at
                """, (store_id, selected_debtor['debtor_name'], selected_debtor['debtor_phone']))
                
                debt_details = cursor.fetchall()
                
                if not debt_details:
                    print(f"{Colors.RED}No detailed debt records found for {selected_debtor['debtor_name']}.{Colors.RESET}")
                    continue
                
                # Display detailed debts
                print("\nDebt Details:")
                for debt in debt_details:
                    print(f"Debt ID: {debt['id']}, Sale ID: {debt['sale_id']}, Amount: {debt['amount_owed']}, Date: {debt['created_at']}")
                
                total_owed = sum(debt['amount_owed'] for debt in debt_details)
                print(f"\nTotal Amount Owed: {total_owed}")
                
    except sqlite3.Error as e:
        print(f"{Colors.RED}Error viewing debts: {e}{Colors.RESET}")
    finally:
        conn_debts.close()
        conn_inventory.close()