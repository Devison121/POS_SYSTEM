"""
Helper functions for the POS system
"""
import os
from typing import Optional

def sanitize_input(text: Optional[str]) -> Optional[str]:
    """Sanitize user input to prevent SQL injection"""
    if text:
        return text.replace('"', '').replace("'", "").replace(";", "").strip()
    return text

def get_database_path() -> str:
    """Get the database path"""
    return os.path.join(os.path.dirname(__file__), '..', '..', 'Databases')

def get_sales_db_path() -> str:
    """Get the sales database path"""
    return os.path.join(get_database_path(), 'sales.db')