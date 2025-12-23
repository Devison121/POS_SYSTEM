# 
import re
from typing import Optional, Tuple

class EmailValidator:
    """
    Simple email validation
    """
    
    def __init__(self):
        # Email pattern (RFC 5322 simplified)
        self.EMAIL_PATTERN = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        
    def validate(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format
        
        Args:
            email: Email to validate
           
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if input is empty or only whitespace
        if not email or email.strip() == "":
            return True, None  # Allow empty emails
        
        email = email.strip().lower()
        
        # Check @ symbol
        if email.count('@') != 1:
            return False, "Email must contain exactly one @ symbol"
        
        # Check basic pattern
        if not re.match(self.EMAIL_PATTERN, email):
            return False, "Email format is invalid"
        
        # Check for consecutive dots
        if '..' in email:
            return False, "Email cannot have two consecutive dots"
        
        # Split email
        local_part, domain = email.split('@', 1)
        
        # Check local part
        if not local_part:
            return False, "Email username cannot be empty"
        
        if local_part.startswith('.') or local_part.endswith('.'):
            return False, "Email username cannot start or end with a dot"
        
        # Check domain
        if not domain:
            return False, "Email domain cannot be empty"
        
        if '.' not in domain:
            return False, "Email domain must contain a dot (e.g., example.com)"
        
        # Check domain parts
        domain_parts = domain.split('.')
        tld = domain_parts[-1]
        
        if len(tld) < 2:
            return False, "Domain extension must have 2 or more characters"
        
        # Check length constraints
        if len(email) > 254:
            return False, "Email is too long (max 254 characters)"
        
        if len(local_part) > 64:
            return False, "Email username is too long (max 64 characters)"
        
        # Check each domain part
        for part in domain_parts:
            if not part:
                return False, "Domain part cannot be empty"
            if len(part) > 63:
                return False, f"Domain part '{part}' is too long"
            if part.startswith('-') or part.endswith('-'):
                return False, "Domain part cannot start or end with hyphen"
        
        return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format directly
    
    Args:
        email: Email to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    validator = EmailValidator()
    return validator.validate(email)


def normalize_email(email: str) -> str:
    """
    Normalize email
    
    Args:
        email: Raw email string
        
    Returns:
        Normalized email
    """
    if not email:
        return ""
    
    email = email.strip()
    
    # Convert to lowercase
    email = email.lower()
    
    # Remove extra spaces
    email = ' '.join(email.split())
    
    # Remove spaces around @
    email = email.replace(' @', '@').replace('@ ', '@')
    
    return email


def get_valid_email() -> str:
    """
    Get valid email from user with interactive validation
    
    Returns:
        Valid email string or empty string if user skips
    """
    print("Enter your email address (or press Space + Enter to skip)")
    
    while True:
        email = input("\nEmail: ").strip()
        
        # Check if user wants to skip (presses Space + Enter)
        if email == " ":
            print("Email entry skipped.")
            return ""
        
        # Normalize the email first
        normalized_email = normalize_email(email)
        
        # Validate the email
        is_valid, error_message = validate_email(normalized_email)
        
        if is_valid:
            if normalized_email == "":
                print("No email provided.")
                return ""
            else:
                print(f"✓ Valid email: {normalized_email}")
                return normalized_email
        else:
            print(f"✗ Invalid email: {error_message}")
            print("Please enter a valid email format (e.g., user@example.com)")
            
            # Show examples of valid emails
            print("\nExamples of valid emails:")
            print("  - user@example.com")
            print("  - john.doe@company.co.tz")
            print("  - user123@gmail.com")