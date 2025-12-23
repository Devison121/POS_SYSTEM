# database/__init__.py

"""
Database module for POS system
"""
from .connection import DatabaseManager, DatabaseConfig

__all__ = [
    'DatabaseManager',
    'DatabaseConfig'
]