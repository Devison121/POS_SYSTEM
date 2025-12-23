from typing import Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from models.product import ValidationResult
from utils.color_output import Colors

@dataclass
class ValidationService:
    """Service for input validation"""
    
    @staticmethod
    def validate_positive_int(prompt: str, current_value: int = 0, min_value: int = 0, field_name: str = "value") -> int:
        """Validate positive integer with current value as default"""
        while True:
            try:
                user_input = input(f"{Colors.BLUE}{prompt} (current: {current_value}): {Colors.RESET}").strip()
                
                if not user_input:
                    return current_value
                
                value = int(user_input)
                
                if value < min_value:
                    print(f"{Colors.RED}❌ {field_name} must be at least {min_value}{Colors.RESET}")
                    continue
                    
                return value
                
            except ValueError:
                print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")
    
    @staticmethod
    def validate_positive_float(prompt: str, current_value: float = 0.0, min_value: float = 0.0, field_name: str = "value") -> float:
        """Validate positive float with current value as default"""
        while True:
            try:
                user_input = input(f"{Colors.BLUE}{prompt} (current: {current_value:.2f}): {Colors.RESET}").strip()
                
                if not user_input:
                    return current_value
                
                value = float(user_input)
                
                if value < min_value:
                    print(f"{Colors.RED}❌ {field_name} must be at least {min_value:.2f}{Colors.RESET}")
                    continue
                    
                return value
                
            except ValueError:
                print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")
    
    @staticmethod
    def validate_stock_quantity(prompt: str, current_stock: int = 0) -> int:
        """Validate stock quantity with confirmation for zero stock"""
        while True:
            quantity = ValidationService.validate_positive_int(prompt, current_stock, 0, "Stock quantity")
            
            if quantity == 0:
                confirm = input(f"{Colors.YELLOW}⚠️  Stock quantity is 0. Are you sure? (yes/no): {Colors.RESET}").strip().lower()
                if confirm != 'yes':
                    print(f"{Colors.BLUE}Please enter stock quantity again{Colors.RESET}")
                    continue
            
            return quantity
    
    @staticmethod
    def validate_low_stock_threshold(prompt: str, current_threshold: int = 5, current_stock: int = 0) -> int:
        """Validate low stock threshold with smart checks against current stock"""
        while True:
            threshold = ValidationService.validate_positive_int(prompt, current_threshold, 1, "Low stock threshold")
            
            if threshold > current_stock:
                print(f"{Colors.RED}❌ WARNING: Low stock threshold ({threshold}) is GREATER than current stock ({current_stock}){Colors.RESET}")
                print(f"{Colors.RED}   This means the product will always be considered 'low stock'{Colors.RESET}")
                
                confirm = input(f"{Colors.YELLOW}Are you sure you want to continue? (yes/no): {Colors.RESET}").strip().lower()
                if confirm != 'yes':
                    print(f"{Colors.BLUE}Please enter a new low stock threshold{Colors.RESET}")
                    continue
            
            # Smart suggestions
            if current_stock > 0:
                suggested_threshold =  current_stock / 2 #max(1, min(10, current_stock // 5))
                
                if threshold != suggested_threshold:
                    print(f"{Colors.CYAN}💡 Suggested threshold: {suggested_threshold} (about 20% of current stock){Colors.RESET}")
                    use_suggested = input(f"{Colors.BLUE}Use suggested threshold? (yes/no): {Colors.RESET}").strip().lower()
                    if use_suggested == 'yes':
                        threshold = suggested_threshold
                        print(f"{Colors.GREEN}✓ Using suggested threshold: {threshold}{Colors.RESET}")
            
            return threshold
    
    @staticmethod
    def validate_expiry_date(date_input: str, current_expiry: Optional[str] = None) -> ValidationResult:
        """Validate expiry date input"""
        from datetime import datetime
        
        if not date_input:
            return ValidationResult(is_valid=True, value=current_expiry)
        
        try:
            try:
                input_date = datetime.strptime(date_input, '%Y-%m-%d')
            except ValueError:
                return ValidationResult(is_valid=False, value=None, message="Invalid date format. Please use YYYY-MM-DD or YYYY-M-D format")
            
            year = input_date.year
            month = input_date.month
            day = input_date.day
            
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            current_year = today.year
            
            min_year = current_year
            max_year = current_year + 10
            
            if year < min_year or year > max_year:
                return ValidationResult(is_valid=False, value=None, message=f"Invalid year. Please enter a year between  {min_year} and {max_year}")
            
            one_day_ago = today
            if input_date < one_day_ago:
                return ValidationResult(is_valid=True, value=date_input, message="WARNING: This expiry date is in the past!")
            
            max_future_date = today.replace(year=max_year)
            if input_date > max_future_date:
                return ValidationResult(is_valid=True, value=date_input, message="WARNING: This expiry date is more than 10 years in the future!")
            
            formatted_date = input_date.strftime('%Y-%m-%d')
            return ValidationResult(is_valid=True, value=formatted_date)
            
        except ValueError as e:
            return ValidationResult(is_valid=False, value=None, message=f"Invalid date: {e}. Please use YYYY-MM-DD or YYYY-M-D format")
        except Exception as e:
            return ValidationResult(is_valid=False, value=None, message=f"Error validating date: {e}")
    
    @staticmethod
    def validate_relation(prompt: str, current_relation: int = 1) -> int:
        """Validate unit relation (must be positive integer)"""
        while True:
            relation = ValidationService.validate_positive_int(prompt, current_relation, 1, "Relation")
            
            if relation <= 0:
                print(f"{Colors.RED}❌ Relation must be greater than 0{Colors.RESET}")
                continue
                
            return relation
    
    @staticmethod
    def update_with_validation_int(prompt: str, current_value: int, min_value: int = 0) -> int:
        """Helper function for integer validation with current value"""
        while True:
            try:
                user_input = input(f"{Colors.BLUE}{prompt}: {Colors.RESET}").strip()
                if not user_input:
                    return current_value
                value = int(user_input)
                if value < min_value:
                    print(f"{Colors.RED}❌ Value must be at least {min_value}{Colors.RESET}")
                    continue
                return value
            except ValueError:
                print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")
    
    @staticmethod
    def update_with_validation_float(prompt: str, current_value: float, min_value: float = 0) -> float:
        """Helper function for float validation with current value"""
        while True:
            try:
                user_input = input(f"{Colors.BLUE}{prompt}: {Colors.RESET}").strip()
                if not user_input:
                    return current_value            
                value = float(user_input) if user_input else current_value
                if value < min_value:
                    print(f"{Colors.RED}❌ Value must be at least {min_value}{Colors.RESET}")
                    continue
                return value
            except ValueError:
                print(f"{Colors.RED}❌ Please enter a valid number{Colors.RESET}")