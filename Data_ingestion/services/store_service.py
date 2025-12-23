from typing import Optional, List
from dataclasses import dataclass
from database.connection import DatabaseManager
from models.product import Store
from utils.color_output import Colors

@dataclass
class StoreService:
    """Service for store-related operations"""
    db: 'DatabaseManager'
    
    def select_store(self) -> Optional[Store]:
        """Select an existing store from the database"""
        try:
            stores = self.db.execute_query(
                'inventory',
                "SELECT id, store_code, name, location FROM stores ORDER BY name",
                fetch=True
            )
            
            if not stores:
                print(f"{Colors.RED}Error: No stores found in database{Colors.RESET}")
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
                    selected_store = Store(id=store_id, store_code=store_code, name=name, location=location)
                    print(f"{Colors.GREEN}✓ Selected store: {name} ({store_code}){Colors.RESET}")
                    return selected_store
                else:
                    print(f"{Colors.RED}Invalid selection. Please choose between 1 and {len(stores)}{Colors.RESET}")
                    return None
            except ValueError:
                print(f"{Colors.RED}Please enter a valid number{Colors.RESET}")
                return None
                
        except Exception as e:
            print(f"{Colors.RED}Error selecting store: {e}{Colors.RESET}")
            return None
    
    def get_store_by_id(self, store_id: int) -> Optional[Store]:
        """Get store by ID"""
        try:
            result = self.db.execute_query(
                'inventory',
                "SELECT id, store_code, name, location FROM stores WHERE id = ?",
                (store_id,),
                fetch=True
            )
            
            if result:
                store_id, store_code, name, location = result[0]
                return Store(id=store_id, store_code=store_code, name=name, location=location)
            return None
        except Exception as e:
            print(f"{Colors.RED}Error getting store: {e}{Colors.RESET}")
            return None