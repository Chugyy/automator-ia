import os
import importlib.util
from typing import Dict, List, Any
from pathlib import Path
from app.common.database.crud import *
from app.common.database.models import InterfaceModel

class InterfaceRegistry:
    def __init__(self):
        self.interfaces_dir = Path(__file__).parent
        self.common_interfaces_dir = Path(__file__).parent.parent.parent / 'common' / 'interfaces'
        self._interfaces = {}
        self._load_interfaces()
    
    def _load_interfaces(self):
        """Synchronise interfaces filesystem -> base de données"""
        self._interfaces = {}
        
        # Charger les interfaces privées (private/interfaces/)
        self._load_interfaces_from_dir(self.interfaces_dir, "private.interfaces")
        
        # Charger les interfaces système (common/interfaces/)
        if self.common_interfaces_dir.exists():
            self._load_interfaces_from_dir(self.common_interfaces_dir, "common.interfaces")
    
    def _load_interfaces_from_dir(self, directory: Path, module_prefix: str):
        """Charge les interfaces depuis un répertoire donné"""
        for item in directory.iterdir():
            if item.is_dir() and item.name not in ['__pycache__', '.git']:
                main_file = item / 'main.py'
                
                if main_file.exists():
                    try:
                        # Import direct du fichier sans se baser sur le module_prefix
                        spec = importlib.util.spec_from_file_location(
                            f"interface_{item.name}_main", main_file)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        interface_info = {
                            'name': item.name,
                            'display_name': getattr(module, 'DISPLAY_NAME', item.name.replace('_', ' ').title()),
                            'description': getattr(module, 'DESCRIPTION', ''),
                            'route': getattr(module, 'ROUTE', f'/{item.name}'),
                            'icon': getattr(module, 'ICON', '🔧'),
                            'module': module,
                            'path': str(item),
                            'type': 'private' if 'private' in module_prefix else 'common'
                        }
                        
                        self._interfaces[item.name] = interface_info
                        
                        # Sync to database
                        self._sync_interface_to_db(item.name, interface_info, str(main_file))
                        
                    except Exception as e:
                        print(f"Erreur lors du chargement de l'interface {item.name}: {e}")
    
    def _sync_interface_to_db(self, name: str, info: Dict[str, Any], file_path: str):
        """Synchronise une interface vers la base de données"""
        existing_interfaces = {i.name: i for i in list_interfaces(active_only=False)}
        
        if name not in existing_interfaces:
            interface = InterfaceModel(
                name=name,
                display_name=info['display_name'],
                description=info['description'],
                route=info['route'],
                icon=info['icon'],
                file_path=file_path
            )
            create_interface(interface)
    
    def get_all_interfaces(self) -> Dict[str, Dict[str, Any]]:
        return self._interfaces
    
    def get_interface(self, name: str) -> Dict[str, Any]:
        return self._interfaces.get(name)
    
    def get_interface_cards(self) -> List[Dict[str, Any]]:
        db_interfaces = list_interfaces()
        cards = []
        for i in db_interfaces:
            card = {
                'name': i.name,
                'display_name': i.display_name,
                'description': i.description,
                'route': i.route,
                'icon': i.icon,
                'type': 'common'  # Default
            }
            # Get type from memory registry
            if i.name in self._interfaces:
                card['type'] = self._interfaces[i.name]['type']
            cards.append(card)
        return cards
    
    def reload_interfaces(self):
        self._load_interfaces()

# Instance globale du registry
interface_registry = InterfaceRegistry()

if __name__ == "__main__":
    # Test du registry
    registry = InterfaceRegistry()
    
    print("Interfaces découvertes:")
    for name, interface in registry.get_all_interfaces().items():
        print(f"  - {name}: {interface['display_name']} ({interface['route']})")
    
    print("\nCards pour le dashboard:")
    cards = registry.get_interface_cards()
    for card in cards:
        print(f"  {card['icon']} {card['display_name']}: {card['description']}")