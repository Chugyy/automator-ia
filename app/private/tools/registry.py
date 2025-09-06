"""Registry minimal pour les outils sample/"""

_tools = {}

def register(name: str, args_schema=None):
    """Décorateur pour enregistrer une fonction outil"""
    def decorator(func):
        _tools[name] = {'func': func, 'schema': args_schema}
        return func
    return decorator

def get_tools():
    """Retourne tous les outils enregistrés"""
    return _tools

def get_tool(name: str):
    """Retourne un outil spécifique"""
    return _tools.get(name)