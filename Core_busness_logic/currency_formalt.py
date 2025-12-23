# currency_formatter.py
# Module to format currency amounts with symbols from database and commas

import os
import sys
from pathlib import Path

# Add the Databases directory to Python path to import database_connection
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

    try:
        from Databases.database_connection import get_db_connection, INVENTORY_DB
    except Exception:
        from POS_SYSTEM.Databases.database_connection import get_db_connection, INVENTORY_DB


def get_currency_symbol(store_id=None):
    """
    Get currency symbol from database for a specific store
    Returns default symbol if not found
    """
    try:
        conn = get_db_connection(INVENTORY_DB)
        cursor = conn.cursor()
        
        if store_id:
            # Get symbol for specific store
            cursor.execute("SELECT symbol FROM stores WHERE id = ?", (store_id,))
        else:
            # Get symbol for first store as default
            cursor.execute("SELECT symbol FROM stores LIMIT 1")
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result['symbol']:
            return result['symbol']
        else:
            return "TSh"  # Default symbol for Tanzania
    
    except Exception as e:
        print(f"Error getting currency symbol: {e}")
        return "TSh"  # Default fallback

def format_currency(amount, store_id=None, symbol=True):
    """
    Format currency with commas and symbol
    Args:
        amount: number to format
        store_id: store ID to get specific currency symbol
        symbol: whether to include currency symbol
    """
    try:
        # Get currency symbol from database
        currency_symbol = get_currency_symbol(store_id) if symbol else ""
        
        # Convert to float if string
        if isinstance(amount, str):
            # Remove any existing commas and spaces
            amount = amount.replace(',', '').replace(' ', '')
            amount = float(amount)
        
        # Format with commas
        formatted_amount = "{:,.2f}".format(float(amount))
        
        # Add currency symbol
        if symbol:
            if currency_symbol.upper() in ['TZS', 'TSH']:
                return f"{formatted_amount} {currency_symbol}"
            elif currency_symbol in ['$', '£', '€']:
                return f"{currency_symbol}{formatted_amount}"
            else:
                return f"{formatted_amount} {currency_symbol}"
        else:
            return formatted_amount
            
    except (ValueError, TypeError) as e:
        print(f"Error formatting currency: {e}")
        return str(amount)

def format_currency_no_symbol(amount):
    """
    Format currency with commas only (no symbol)
    """
    return format_currency(amount, symbol=False)
