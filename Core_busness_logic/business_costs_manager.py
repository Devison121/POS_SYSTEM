# business_costs_manager.py
# Module to manage business costs, system costs, and other payments
import sqlite3
from pathlib import Path
import sys
from datetime import datetime
import re

# Add package root to path
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    from Databases.database_connection import get_db_connection, OTHER_PAYMENTS_DB
except ImportError:
    print("Error: Could not import database connection module")
    sys.exit(1)

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class BusinessCostsManager:
    def __init__(self, user=None):
        """
        Initialize BusinessCostsManager with user context
        
        Args:
            user (dict): User object from login containing:
                - id: user ID
                - role: user role ('boss' or 'seller')
                - current_store_id: current store ID
                - current_store_code: current store code
        """
        self.db_path = OTHER_PAYMENTS_DB
        self.user = user
    
    def get_db_connection(self):
        """Get database connection for other_payments database"""
        return get_db_connection(self.db_path)
    
    def _check_permission(self):
        """Check if user has permission to manage costs (boss only)"""
        if not self.user:
            print(f"{Colors.RED}Error: No user logged in.{Colors.RESET}")
            return False
        
        if self.user.get('role') != 'boss':
            print(f"{Colors.RED}Error: Only boss users can manage business costs.{Colors.RESET}")
            return False
        
        if not self.user.get('current_store_id') or not self.user.get('current_store_code'):
            print(f"{Colors.RED}Error: No store selected.{Colors.RESET}")
            return False
        
        return True
    
    def _get_store_context(self):
        """Get store context from user object"""
        return {
            'store_id': self.user['current_store_id'],
            'store_code': self.user['current_store_code']
        }
    
    def _validate_date(self, date_string):
        """
        Validate date format (YYYY-MM-DD)
        
        Args:
            date_string (str): Date string to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not date_string:
            return False
            
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_string):
            return False
        
        try:
            datetime.strptime(date_string, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def _validate_amount(self, amount_string):
        """
        Validate amount format
        
        Args:
            amount_string (str): Amount string to validate
            
        Returns:
            tuple: (is_valid, amount_value) 
        """
        if not amount_string:
            return False, None
        
        try:
            amount = float(amount_string)
            if amount <= 0:
                return False, None
            return True, amount
        except ValueError:
            return False, None
    
    def add_business_cost(self, cost_category, description, amount, cost_date, 
                         frequency='one_time', recurring_end_date=None):
        """
        Add a business cost record
        
        Args:
            cost_category (str): Category of cost (rent, electricity, loan_interest, storage, marketing, insurance, other)
            description (str): Description of the cost
            amount (float): Amount of the cost
            cost_date (str): Date of cost (YYYY-MM-DD)
            frequency (str): Frequency of cost (one_time, daily, weekly, monthly, yearly)
            recurring_end_date (str, optional): End date for recurring costs
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._check_permission():
            return False
        
        store_context = self._get_store_context()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO business_costs 
                (store_id, store_code, cost_category, description, amount, cost_date, frequency, recurring_end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                store_context['store_id'], 
                store_context['store_code'], 
                cost_category, 
                description, 
                amount, 
                cost_date, 
                frequency, 
                recurring_end_date
            ))
            
            conn.commit()
            conn.close()
            print(f"{Colors.GREEN}Business cost added successfully: {description} - ${amount:.2f}{Colors.RESET}")
            return True
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}Error adding business cost: {e}{Colors.RESET}")
            return False
    
    def add_system_cost(self, cost_type, description, amount, frequency='monthly'):
        """
        Add a system cost record
        
        Args:
            cost_type (str): Type of cost (pos_license, software_fee, maintenance, internet, other)
            description (str): Description of the cost
            amount (float): Amount of the cost
            frequency (str): Frequency of cost (daily, weekly, monthly, yearly, one_time)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._check_permission():
            return False
        
        store_context = self._get_store_context()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_costs 
                (store_id, store_code, cost_type, description, amount, frequency)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                store_context['store_id'], 
                store_context['store_code'], 
                cost_type, 
                description, 
                amount, 
                frequency
            ))
            
            conn.commit()
            conn.close()
            print(f"{Colors.GREEN}System cost added successfully: {description} - ${amount:.2f}{Colors.RESET}")
            return True
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}Error adding system cost: {e}{Colors.RESET}")
            return False
    
    def add_other_payment(self, payment_type, description, amount, payment_date, recipient=None):
        """
        Add an other payment record
        
        Args:
            payment_type (str): Type of payment
            description (str): Description of the payment
            amount (float): Amount of the payment
            payment_date (str): Date of payment (YYYY-MM-DD)
            recipient (str, optional): Recipient of the payment
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._check_permission():
            return False
        
        store_context = self._get_store_context()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO other_payments 
                (store_id, store_code, payment_type, description, amount, payment_date, recipient)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                store_context['store_id'], 
                store_context['store_code'], 
                payment_type, 
                description, 
                amount, 
                payment_date, 
                recipient
            ))
            
            conn.commit()
            conn.close()
            print(f"{Colors.GREEN}Other payment added successfully: {description} - ${amount:.2f}{Colors.RESET}")
            return True
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}Error adding other payment: {e}{Colors.RESET}")
            return False
    
    def get_business_costs(self):
        """
        Get business costs for current store
        
        Returns:
            list: List of business cost records
        """
        if not self._check_permission():
            return []
        
        store_context = self._get_store_context()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM business_costs 
                WHERE store_id = ? 
                ORDER BY cost_date DESC
            ''', (store_context['store_id'],))
            
            costs = cursor.fetchall()
            conn.close()
            return costs
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}Error retrieving business costs: {e}{Colors.RESET}")
            return []
    
    def get_system_costs(self):
        """
        Get system costs for current store
        
        Returns:
            list: List of system cost records
        """
        if not self._check_permission():
            return []
        
        store_context = self._get_store_context()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM system_costs 
                WHERE store_id = ? 
                ORDER BY created_at DESC
            ''', (store_context['store_id'],))
            
            costs = cursor.fetchall()
            conn.close()
            return costs
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}Error retrieving system costs: {e}{Colors.RESET}")
            return []
    
    def get_other_payments(self):
        """
        Get other payments for current store
        
        Returns:
            list: List of other payment records
        """
        if not self._check_permission():
            return []
        
        store_context = self._get_store_context()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM other_payments 
                WHERE store_id = ? 
                ORDER BY payment_date DESC
            ''', (store_context['store_id'],))
            
            payments = cursor.fetchall()
            conn.close()
            return payments
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}Error retrieving other payments: {e}{Colors.RESET}")
            return []
    
    def get_total_costs(self, start_date=None, end_date=None):
        """
        Get total costs for current store within a date range
        
        Args:
            start_date (str, optional): Start date (YYYY-MM-DD)
            end_date (str, optional): End date (YYYY-MM-DD)
            
        Returns:
            dict: Dictionary with total costs by category
        """
        if not self._check_permission():
            return {}
        
        store_context = self._get_store_context()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Build query with date filters
            date_condition = ""
            params = [store_context['store_id']]
            
            if start_date and end_date:
                date_condition = "AND (cost_date BETWEEN ? AND ? OR created_at BETWEEN ? AND ?)"
                params.extend([start_date, end_date, start_date, end_date])
            elif start_date:
                date_condition = "AND (cost_date >= ? OR created_at >= ?)"
                params.extend([start_date, start_date])
            elif end_date:
                date_condition = "AND (cost_date <= ? OR created_at <= ?)"
                params.extend([end_date, end_date])
            
            # Business costs
            cursor.execute(f'''
                SELECT cost_category, SUM(amount) as total 
                FROM business_costs 
                WHERE store_id = ? {date_condition}
                GROUP BY cost_category
            ''', params)
            business_totals = {row['cost_category']: row['total'] for row in cursor.fetchall()}
            
            # System costs
            cursor.execute(f'''
                SELECT cost_type, SUM(amount) as total 
                FROM system_costs 
                WHERE store_id = ? {date_condition}
                GROUP BY cost_type
            ''', params)
            system_totals = {row['cost_type']: row['total'] for row in cursor.fetchall()}
            
            # Other payments
            cursor.execute(f'''
                SELECT payment_type, SUM(amount) as total 
                FROM other_payments 
                WHERE store_id = ? {date_condition}
                GROUP BY payment_type
            ''', params)
            other_totals = {row['payment_type']: row['total'] for row in cursor.fetchall()}
            
            conn.close()
            
            return {
                'business_costs': business_totals,
                'system_costs': system_totals,
                'other_payments': other_totals,
                'total_all_costs': sum(business_totals.values()) + sum(system_totals.values()) + sum(other_totals.values())
            }
            
        except sqlite3.Error as e:
            print(f"{Colors.RED}Error calculating total costs: {e}{Colors.RESET}")
            return {}
    
    def display_costs_summary(self):
        """Display a summary of all costs for the current store"""
        if not self._check_permission():
            return
        
        print(f"\n{Colors.BLUE}=== COSTS SUMMARY FOR STORE ==={Colors.RESET}")
        
        # Get all costs
        business_costs = self.get_business_costs()
        system_costs = self.get_system_costs()
        other_payments = self.get_other_payments()
        
        # Display business costs
        if business_costs:
            print(f"\n{Colors.YELLOW}--- Business Costs ---{Colors.RESET}")
            for cost in business_costs:
                print(f"  {cost['cost_category']}: {cost['description']} - ${cost['amount']:.2f} ({cost['cost_date']})")
        else:
            print(f"\n{Colors.YELLOW}--- No Business Costs ---{Colors.RESET}")
        
        # Display system costs
        if system_costs:
            print(f"\n{Colors.YELLOW}--- System Costs ---{Colors.RESET}")
            for cost in system_costs:
                print(f"  {cost['cost_type']}: {cost['description']} - ${cost['amount']:.2f}")
        else:
            print(f"\n{Colors.YELLOW}--- No System Costs ---{Colors.RESET}")
        
        # Display other payments
        if other_payments:
            print(f"\n{Colors.YELLOW}--- Other Payments ---{Colors.RESET}")
            for payment in other_payments:
                recipient_info = f" to {payment['recipient']}" if payment['recipient'] else ""
                print(f"  {payment['payment_type']}: {payment['description']}{recipient_info} - ${payment['amount']:.2f}")
        else:
            print(f"\n{Colors.YELLOW}--- No Other Payments ---{Colors.RESET}")
        
        # Display totals
        totals = self.get_total_costs()
        print(f"\n{Colors.GREEN}--- Total Costs ---{Colors.RESET}")
        print(f"Total Business Costs: ${sum(totals['business_costs'].values()):.2f}")
        print(f"Total System Costs: ${sum(totals['system_costs'].values()):.2f}")
        print(f"Total Other Payments: ${sum(totals['other_payments'].values()):.2f}")
        print(f"{Colors.GREEN}Grand Total: ${totals['total_all_costs']:.2f}{Colors.RESET}")


def business_costs_menu(user):
    """
    Main menu for managing business costs (boss only)
    
    Args:
        user (dict): Logged in user object
    """
    if user.get('role') != 'boss':
        print(f"{Colors.RED}Access denied. Only boss users can manage business costs.{Colors.RESET}")
        return
    
    manager = BusinessCostsManager(user)
    
    while True:
        print(f"\n{Colors.BLUE}=== BUSINESS COSTS MANAGEMENT ==={Colors.RESET}")
        print("1. Add Business Cost")
        print("2. Add System Cost")
        print("3. Add Other Payment")
        print("4. View Costs Summary")
        print("5. View Business Costs")
        print("6. View System Costs")
        print("7. View Other Payments")
        print("8. View Total Costs")
        print("9. Back to Main Menu")
        
        choice = input(f"{Colors.YELLOW}Choose an option (1-9): {Colors.RESET}").strip()
        
        if choice == '1':
            add_business_cost_flow(manager)
        elif choice == '2':
            add_system_cost_flow(manager)
        elif choice == '3':
            add_other_payment_flow(manager)
        elif choice == '4':
            manager.display_costs_summary()
        elif choice == '5':
            display_business_costs(manager)
        elif choice == '6':
            display_system_costs(manager)
        elif choice == '7':
            display_other_payments(manager)
        elif choice == '8':
            display_total_costs(manager)
        elif choice == '9':
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please try again.{Colors.RESET}")


def get_valid_input(prompt, validation_func, error_message, allow_back=True):
    """
    Get valid input from user with option to go back
    
    Args:
        prompt (str): Input prompt
        validation_func (function): Function to validate input
        error_message (str): Error message if validation fails
        allow_back (bool): Whether to allow going back
        
    Returns:
        tuple: (input_value, should_continue) - if should_continue is False, user wants to go back
    """
    while True:
        user_input = input(prompt).strip()
        
        if allow_back and user_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return None, False
        
        is_valid, value = validation_func(user_input)
        if is_valid:
            return value, True
        
        print(f"{Colors.RED}{error_message}{Colors.RESET}")
        if allow_back:
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")


def validate_required_text(text):
    """Validate required text input"""
    if not text:
        return False, None
    return True, text


def validate_optional_text(text):
    """Validate optional text input"""
    return True, text if text else None


def validate_category_choice(choice, categories):
    """Validate category choice"""
    if choice in categories:
        return True, categories[choice]
    return False, None


def validate_frequency(freq):
    """Validate frequency input"""
    valid_frequencies = ['one_time', 'daily', 'weekly', 'monthly', 'yearly']
    if not freq:
        return True, 'one_time'  # Default value
    if freq in valid_frequencies:
        return True, freq
    return False, None


def validate_system_cost_frequency(freq):
    """Validate system cost frequency input"""
    valid_frequencies = ['daily', 'weekly', 'monthly', 'yearly', 'one_time']
    if not freq:
        return True, 'monthly'  # Default value
    if freq in valid_frequencies:
        return True, freq
    return False, None


def validate_date(date_string, allow_empty=False):
    """Validate date input"""
    manager = BusinessCostsManager()
    if allow_empty and not date_string:
        return True, None
    if not date_string:
        date_string = datetime.now().strftime("%Y-%m-%d")
        return True, date_string
    return manager._validate_date(date_string), date_string


def validate_amount(amount_string):
    """Validate amount input"""
    manager = BusinessCostsManager()
    return manager._validate_amount(amount_string)


def add_business_cost_flow(manager):
    """Flow for adding a business cost"""
    print(f"\n{Colors.BLUE}=== ADD BUSINESS COST ==={Colors.RESET}")
    print(f"{Colors.YELLOW}Type 'back' at any time to return to previous menu{Colors.RESET}")
    
    # Cost categories
    categories = {
        '1': 'rent',
        '2': 'electricity', 
        '3': 'loan_interest',
        '4': 'storage',
        '5': 'marketing',
        '6': 'insurance',
        '7': 'other'
    }
    
    print("Cost Categories:")
    for key, category in categories.items():
        print(f"  {key}. {category}")
    
    # Get category
    while True:
        category_choice = input("Select category (1-7): ").strip()
        if category_choice.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        if category_choice in categories:
            cost_category = categories[category_choice]
            break
        else:
            print(f"{Colors.RED}Invalid category selection. Please choose 1-7.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Get description
    description, should_continue = get_valid_input(
        "Description: ",
        validate_required_text,
        "Description is required."
    )
    if not should_continue:
        return
    
    # Get amount
    while True:
        amount_input = input("Amount: ").strip()
        if amount_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        is_valid, amount = validate_amount(amount_input)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid amount. Please enter a positive number.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Get cost date
    while True:
        cost_date_input = input("Cost date (YYYY-MM-DD) [today]: ").strip()
        if cost_date_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        if not cost_date_input:
              cost_date_input = datetime.now().strftime("%Y-%m-%d")

        is_valid, cost_date = validate_date(cost_date_input, allow_empty=True)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid date format. Please use YYYY-MM-DD.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Get frequency
    while True:
        frequency_input = input("Frequency (one_time, daily, weekly, monthly, yearly) [one_time]: ").strip()
        if frequency_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        is_valid, frequency = validate_frequency(frequency_input)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid frequency. Please choose from: one_time, daily, weekly, monthly, yearly.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Get recurring end date if needed
    recurring_end_date = None
    if frequency != 'one_time':
        while True:
            end_date_input = input("Recurring end date (YYYY-MM-DD) [optional]: ").strip()
            if end_date_input.lower() in ['back', 'b', 'cancel', 'exit']:
                return
            
            if not end_date_input:
                break
            
            is_valid, end_date = validate_date(end_date_input, allow_empty=False)
            if is_valid:
                recurring_end_date = end_date
                break
            else:
                print(f"{Colors.RED}Invalid date format. Please use YYYY-MM-DD.{Colors.RESET}")
                print(f"{Colors.YELLOW}Type 'back' to return to previous menu or leave empty for no end date{Colors.RESET}")
    
    # Confirm and add
    print(f"\n{Colors.YELLOW}Please confirm the details:{Colors.RESET}")
    print(f"Category: {cost_category}")
    print(f"Description: {description}")
    print(f"Amount: ${amount:.2f}")
    print(f"Date: {cost_date}")
    print(f"Frequency: {frequency}")
    if recurring_end_date:
        print(f"Recurring End Date: {recurring_end_date}")
    
    while True:
        confirm = input("Add this business cost? (y/n): ").strip().lower()
        if confirm in ['back', 'b', 'cancel', 'exit', 'n', 'no']:
            print(f"{Colors.YELLOW}Cancelled.{Colors.RESET}")
            return
        elif confirm in ['y', 'yes']:
            break
        else:
            print(f"{Colors.RED}Please enter 'y' for yes or 'n' for no.{Colors.RESET}")
    
    manager.add_business_cost(
        cost_category=cost_category,
        description=description,
        amount=amount,
        cost_date=cost_date,
        frequency=frequency,
        recurring_end_date=recurring_end_date
    )


def add_system_cost_flow(manager):
    """Flow for adding a system cost"""
    print(f"\n{Colors.BLUE}=== ADD SYSTEM COST ==={Colors.RESET}")
    print(f"{Colors.YELLOW}Type 'back' at any time to return to previous menu{Colors.RESET}")
    
    # Cost types
    cost_types = {
        '1': 'pos_license',
        '2': 'software_fee',
        '3': 'maintenance',
        '4': 'internet', 
        '5': 'other'
    }
    
    print("Cost Types:")
    for key, cost_type in cost_types.items():
        print(f"  {key}. {cost_type}")
    
    # Get cost type
    while True:
        type_choice = input("Select cost type (1-5): ").strip()
        if type_choice.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        if type_choice in cost_types:
            cost_type = cost_types[type_choice]
            break
        else:
            print(f"{Colors.RED}Invalid cost type selection. Please choose 1-5.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Get description
    description, should_continue = get_valid_input(
        "Description: ",
        validate_required_text,
        "Description is required."
    )
    if not should_continue:
        return
    
    # Get amount
    while True:
        amount_input = input("Amount: ").strip()
        if amount_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        is_valid, amount = validate_amount(amount_input)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid amount. Please enter a positive number.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Get frequency
    while True:
        frequency_input = input("Frequency (daily, weekly, monthly, yearly, one_time) [monthly]: ").strip()
        if frequency_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        is_valid, frequency = validate_system_cost_frequency(frequency_input)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid frequency. Please choose from: daily, weekly, monthly, yearly, one_time.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Confirm and add
    print(f"\n{Colors.YELLOW}Please confirm the details:{Colors.RESET}")
    print(f"Type: {cost_type}")
    print(f"Description: {description}")
    print(f"Amount: ${amount:.2f}")
    print(f"Frequency: {frequency}")
    
    while True:
        confirm = input("Add this system cost? (y/n): ").strip().lower()
        if confirm in ['back', 'b', 'cancel', 'exit', 'n', 'no']:
            print(f"{Colors.YELLOW}Cancelled.{Colors.RESET}")
            return
        elif confirm in ['y', 'yes']:
            break
        else:
            print(f"{Colors.RED}Please enter 'y' for yes or 'n' for no.{Colors.RESET}")
    
    manager.add_system_cost(
        cost_type=cost_type,
        description=description,
        amount=amount,
        frequency=frequency
    )


def add_other_payment_flow(manager):
    """Flow for adding other payment"""
    print(f"\n{Colors.BLUE}=== ADD OTHER PAYMENT ==={Colors.RESET}")
    print(f"{Colors.YELLOW}Type 'back' at any time to return to previous menu{Colors.RESET}")
    
    # Get payment type
    payment_type, should_continue = get_valid_input(
        "Payment type: ",
        validate_required_text,
        "Payment type is required."
    )
    if not should_continue:
        return
    
    # Get description
    description, should_continue = get_valid_input(
        "Description: ",
        validate_required_text,
        "Description is required."
    )
    if not should_continue:
        return
    
    # Get amount
    while True:
        amount_input = input("Amount: ").strip()
        if amount_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        is_valid, amount = validate_amount(amount_input)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid amount. Please enter a positive number.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Get payment date
    while True:
        payment_date_input = input("Payment date (YYYY-MM-DD) [today]: ").strip()
        if payment_date_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        if not payment_date_input:
              payment_date_input = datetime.now().strftime("%Y-%m-%d")
        
        is_valid, payment_date = validate_date(payment_date_input, allow_empty=True)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid date format. Please use YYYY-MM-DD.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu{Colors.RESET}")
    
    # Get recipient (optional)
    recipient, should_continue = get_valid_input(
        "Recipient [optional]: ",
        validate_optional_text,
        ""
    )
    if not should_continue:
        return
    
    # Confirm and add
    print(f"\n{Colors.YELLOW}Please confirm the details:{Colors.RESET}")
    print(f"Payment Type: {payment_type}")
    print(f"Description: {description}")
    print(f"Amount: ${amount:.2f}")
    print(f"Date: {payment_date}")
    if recipient:
        print(f"Recipient: {recipient}")
    
    while True:
        confirm = input("Add this payment? (y/n): ").strip().lower()
        if confirm in ['back', 'b', 'cancel', 'exit', 'n', 'no']:
            print(f"{Colors.YELLOW}Cancelled.{Colors.RESET}")
            return
        elif confirm in ['y', 'yes']:
            break
        else:
            print(f"{Colors.RED}Please enter 'y' for yes or 'n' for no.{Colors.RESET}")
    
    manager.add_other_payment(
        payment_type=payment_type,
        description=description,
        amount=amount,
        payment_date=payment_date,
        recipient=recipient
    )


def display_business_costs(manager):
    """Display business costs"""
    costs = manager.get_business_costs()
    if not costs:
        print(f"{Colors.YELLOW}No business costs found.{Colors.RESET}")
        return
    
    print(f"\n{Colors.BLUE}=== BUSINESS COSTS ==={Colors.RESET}")
    for cost in costs:
        print(f"Category: {cost['cost_category']}")
        print(f"Description: {cost['description']}")
        print(f"Amount: ${cost['amount']:.2f}")
        print(f"Date: {cost['cost_date']}")
        print(f"Frequency: {cost['frequency']}")
        if cost['recurring_end_date']:
            print(f"Recurring End: {cost['recurring_end_date']}")
        print("-" * 40)


def display_system_costs(manager):
    """Display system costs"""
    costs = manager.get_system_costs()
    if not costs:
        print(f"{Colors.YELLOW}No system costs found.{Colors.RESET}")
        return
    
    print(f"\n{Colors.BLUE}=== SYSTEM COSTS ==={Colors.RESET}")
    for cost in costs:
        print(f"Type: {cost['cost_type']}")
        print(f"Description: {cost['description']}")
        print(f"Amount: ${cost['amount']:.2f}")
        print(f"Frequency: {cost['frequency']}")
        print(f"Created: {cost['created_at']}")
        print("-" * 40)


def display_other_payments(manager):
    """Display other payments"""
    payments = manager.get_other_payments()
    if not payments:
        print(f"{Colors.YELLOW}No other payments found.{Colors.RESET}")
        return
    
    print(f"\n{Colors.BLUE}=== OTHER PAYMENTS ==={Colors.RESET}")
    for payment in payments:
        print(f"Type: {payment['payment_type']}")
        print(f"Description: {payment['description']}")
        print(f"Amount: ${payment['amount']:.2f}")
        print(f"Date: {payment['payment_date']}")
        if payment['recipient']:
            print(f"Recipient: {payment['recipient']}")
        print("-" * 40)


def display_total_costs(manager):
    """Display total costs"""
    print(f"\n{Colors.BLUE}=== TOTAL COSTS ==={Colors.RESET}")
    print(f"{Colors.YELLOW}Type 'back' at any time to return to previous menu{Colors.RESET}")
    
    # Get start date
    while True:
        start_date_input = input("Start date (YYYY-MM-DD) [optional]: ").strip()
        if start_date_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        if not start_date_input:
            start_date = None
            break
        
        is_valid, start_date = validate_date(start_date_input, allow_empty=False)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid date format. Please use YYYY-MM-DD.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu or leave empty for no start date{Colors.RESET}")
    
    # Get end date
    while True:
        end_date_input = input("End date (YYYY-MM-DD) [optional]: ").strip()
        if end_date_input.lower() in ['back', 'b', 'cancel', 'exit']:
            return
        
        if not end_date_input:
            end_date = None
            break
        
        is_valid, end_date = validate_date(end_date_input, allow_empty=False)
        if is_valid:
            break
        else:
            print(f"{Colors.RED}Invalid date format. Please use YYYY-MM-DD.{Colors.RESET}")
            print(f"{Colors.YELLOW}Type 'back' to return to previous menu or leave empty for no end date{Colors.RESET}")
    
    totals = manager.get_total_costs(start_date=start_date, end_date=end_date)
    
    if not any(totals.values()):
        print(f"{Colors.YELLOW}No costs found for the specified period.{Colors.RESET}")
        return
    
    print(f"\n{Colors.GREEN}--- Business Costs ---{Colors.RESET}")
    for category, total in totals['business_costs'].items():
        print(f"  {category}: ${total:.2f}")
    
    print(f"\n{Colors.GREEN}--- System Costs ---{Colors.RESET}")
    for cost_type, total in totals['system_costs'].items():
        print(f"  {cost_type}: ${total:.2f}")
    
    print(f"\n{Colors.GREEN}--- Other Payments ---{Colors.RESET}")
    for payment_type, total in totals['other_payments'].items():
        print(f"  {payment_type}: ${total:.2f}")
    
    print(f"\n{Colors.GREEN}Grand Total: {totals['total_all_costs']:.2f}{Colors.RESET}")


if __name__ == "__main__":
    # For testing purposes
    print("This module is designed to be used with the user login system.")
    print("Import and use business_costs_menu(user) function.")