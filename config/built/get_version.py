from pathlib import Path
import os
from dotenv import dotenv_values

def get_version():
    """Récupère la VERSION depuis .env ou défaut dev"""
    # Priorité 1: Variable d'environnement système
    version = os.getenv("VERSION")
    if version:
        return version
    
    # Priorité 2: Fichier .env racine
    env_file = Path("../../.env")
    if env_file.exists():
        env_vars = dotenv_values(str(env_file))
        version = env_vars.get("VERSION")
        if version:
            return version
    
    # Priorité 3: Défaut dev
    return "dev"