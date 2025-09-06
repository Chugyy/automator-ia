import os
import glob
import json
from typing import Dict, List, Any
from pathlib import Path
from dotenv import dotenv_values
from app.common.database.crud import *
from app.common.database.models import ToolModel, ToolProfileModel

class ToolsService:
    TOOLS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "private", "tools")
    
    @classmethod
    def get_available_tools(cls) -> List[Dict[str, Any]]:
        tools_data = []
        
        # Force sync filesystem tools with database
        cls._sync_tools_to_db()
        
        # Get tools from database
        db_tools = list_tools()
        
        for tool in db_tools:
            # Vérifier que l'outil est actif et que son dossier existe encore
            if not tool.active:
                continue
            tool_dir = os.path.join(cls.TOOLS_DIR, tool.name)
            if not os.path.exists(tool_dir):
                continue
                
            # Charger les profils depuis .env ET base de données
            all_profiles = cls.get_tool_profiles(tool.name)
            
            tool_info = {
                "id": tool.id,
                "name": tool.name,
                "display_name": tool.display_name or tool.name.title(),
                "logo_path": tool.logo_path,
                "has_logo": os.path.exists(tool.logo_path) if tool.logo_path else False,
                "profiles": all_profiles,  # Utilise la méthode qui charge .env + DB
                "config_path": tool.config_path,
                "readme_path": tool.readme_path,
                "active": tool.active
            }
            tools_data.append(tool_info)
        
        return sorted(tools_data, key=lambda x: x['name'])
    
    @classmethod
    def get_tool_profiles(cls, tool_name: str) -> List[Dict[str, Any]]:
        """Charge les profils depuis les fichiers .env et la DB"""
        profiles = []
        
        # 1. Charger les profils depuis les fichiers .env dans le dossier de l'outil
        env_profiles = cls._load_env_profiles(tool_name)
        profiles.extend(env_profiles)
        
        # 2. Charger les profils depuis la base de données (mode libre/dashboard)
        tool = get_tool_by_name(tool_name)
        if tool:
            db_profiles = get_tool_profiles(tool.id)
            for p in db_profiles:
                profiles.append({
                    "name": p.profile_name,
                    "config": p.config_data,
                    "id": p.id,
                    "source": "database"
                })
        
        return profiles
    
    @classmethod
    def get_tool_config_schema(cls, tool_name: str) -> Dict[str, Any]:
        """Récupère le schéma de configuration enrichi depuis config.json"""
        try:
            config_path = os.path.join(cls.TOOLS_DIR, tool_name, "config.json")
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    return {
                        "tool_name": schema.get("tool_name", tool_name),
                        "display_name": schema.get("display_name", tool_name.title()),
                        "description": schema.get("description", ""),
                        "required_params": schema.get("required_params", []),
                        "optional_params": schema.get("optional_params", {}),
                        "default_config": schema.get("optional_params", {}),
                        "profile_examples": schema.get("profile_examples", {}),
                        "actions": schema.get("actions", {}),
                        "setup_instructions": schema.get("setup_instructions", {})
                    }
        except Exception:
            pass
        
        return {
            "tool_name": tool_name,
            "display_name": tool_name.title(),
            "description": "",
            "required_params": [],
            "optional_params": {},
            "default_config": {},
            "profile_examples": {},
            "actions": {},
            "setup_instructions": {}
        }
    
    @classmethod
    def create_profile(cls, tool_name: str, profile_name: str, config: Dict[str, str], save_to_env: bool = True) -> bool:
        """Crée un profil en base de données et optionnellement dans un fichier .env"""
        
        # Option 1: Sauvegarder dans un fichier .env (recommandé pour la persistance)
        if save_to_env:
            return cls.save_env_profile(tool_name, profile_name, config)
        
        # Option 2: Sauvegarder en base de données (mode libre/temporaire)
        tool = get_tool_by_name(tool_name)
        if not tool:
            return False
        
        profile = ToolProfileModel(
            tool_id=tool.id,
            profile_name=profile_name,
            config_data=config
        )
        
        try:
            create_tool_profile(profile)
            return True
        except:
            return False
    
    @classmethod
    def update_profile(cls, tool_name: str, profile_name: str, config: Dict[str, str]) -> bool:
        """Met à jour un profil (priorité fichier .env puis base de données)"""
        
        # Vérifier si le profil existe dans un fichier .env
        env_file_path = cls.get_env_profile_path(tool_name, profile_name)
        if os.path.exists(env_file_path):
            return cls.save_env_profile(tool_name, profile_name, config)
        
        # Sinon, mettre à jour en base de données
        tool = get_tool_by_name(tool_name)
        if not tool:
            return False
        
        profiles = get_tool_profiles(tool.id)
        profile = next((p for p in profiles if p.profile_name == profile_name), None)
        
        if not profile:
            return False
        
        return update_tool_profile(profile.id, {"config_data": config})
    
    @classmethod
    def delete_profile(cls, tool_name: str, profile_name: str) -> bool:
        """Supprime un profil (fichier .env ou base de données)"""
        
        # Vérifier si le profil existe dans un fichier .env
        env_file_path = cls.get_env_profile_path(tool_name, profile_name)
        if os.path.exists(env_file_path):
            try:
                os.remove(env_file_path)
                return True
            except Exception as e:
                print(f"Error deleting env profile {profile_name} for {tool_name}: {e}")
                return False
        
        # Sinon, supprimer de la base de données
        tool = get_tool_by_name(tool_name)
        if not tool:
            return False
        
        profiles = get_tool_profiles(tool.id)
        profile = next((p for p in profiles if p.profile_name == profile_name), None)
        
        if not profile:
            return False
        
        return delete_tool_profile(profile.id)
    
    @classmethod
    def toggle_tool(cls, tool_name: str) -> Dict[str, str]:
        """Active/désactive un outil"""
        tool = get_tool_by_name(tool_name, active_only=False)
        if not tool:
            return {"status": "error", "message": "Tool not found"}
        
        new_status = not tool.active
        success = update_tool(tool.id, {"active": new_status})
        
        if success:
            return {"status": "success", "message": f"Tool {tool_name} {'activated' if new_status else 'deactivated'}"}
        else:
            return {"status": "error", "message": "Failed to update tool status"}
    
    @classmethod
    def _sync_tools_to_db(cls):
        """Synchronise les outils du filesystem avec la base de données"""
        existing_tools = {t.name: t for t in list_tools()}
        filesystem_tools = set()
        
        # 1. Ajouter/mettre à jour les outils du filesystem
        for tool_dir in glob.glob(os.path.join(cls.TOOLS_DIR, "*/")):
            if not os.path.isdir(tool_dir):
                continue
                
            tool_name = os.path.basename(tool_dir.rstrip('/'))
            if tool_name.startswith('.') or tool_name == '__pycache__':
                continue
            
            # Vérifier que l'outil a bien config.json et main.py (nouvelle architecture)
            config_file = os.path.join(tool_dir, "config.json")
            main_file = os.path.join(tool_dir, "main.py")
            
            if not (os.path.exists(config_file) and os.path.exists(main_file)):
                continue
            
            filesystem_tools.add(tool_name)
            
            if tool_name not in existing_tools:
                # Charger le display_name depuis config.json
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    display_name = config_data.get("display_name", tool_name.title())
                except:
                    display_name = tool_name.title()
                
                tool = ToolModel(
                    name=tool_name,
                    display_name=display_name,
                    logo_path=os.path.join(tool_dir, "logo.png"),
                    config_path=config_file,
                    readme_path=os.path.join(tool_dir, "README.md")
                )
                tool_id = create_tool(tool)
                print(f"✅ Outil {tool_name} ajouté en base de données")
                
                # Note: les profils sont maintenant chargés depuis les fichiers .env
                cls._create_default_profiles(tool_id, tool_name)
        
        # 2. Désactiver les outils orphelins (présents en DB mais absents du filesystem)
        for tool_name, tool in existing_tools.items():
            if tool_name not in filesystem_tools:
                try:
                    # Désactiver l'outil orphelin (plus sûr que la suppression complète)
                    update_tool(tool.id, {"active": False})
                    print(f"🗑️ Outil orphelin {tool_name} désactivé (dossier supprimé)")
                except Exception as e:
                    print(f"❌ Erreur lors de la désactivation de l'outil {tool_name}: {e}")
    
    @classmethod
    def _create_default_profiles(cls, tool_id: str, tool_name: str):
        """Les profils sont maintenant gérés par les fichiers .env - plus de création automatique"""
        pass
    
    @classmethod
    def _get_logo_path(cls, tool_name: str) -> str:
        return os.path.join(cls.TOOLS_DIR, tool_name, "logo.png")
    
    @classmethod
    def _load_env_profiles(cls, tool_name: str) -> List[Dict[str, Any]]:
        """Charge les profils depuis os.environ, config/.env et les fichiers .env.*"""
        tool_dir = os.path.join(cls.TOOLS_DIR, tool_name)
        profiles_map: Dict[str, Dict[str, Any]] = {}
        profile_source: Dict[str, str] = {}
        source_prio = {"env_file": 1, "env_central": 2, "env_runtime": 3}

        def merge(profile: str, cfg: Dict[str, Any], src: str):
            if not cfg:
                return
            if profile not in profiles_map:
                profiles_map[profile] = {}
            profiles_map[profile].update(cfg)
            prev = profile_source.get(profile)
            if not prev or source_prio[src] > source_prio[prev]:
                profile_source[profile] = src

        # Schéma pour connaître les noms de paramètres valides
        schema = cls.get_tool_config_schema(tool_name)
        required = schema.get("required_params", []) or []
        optional = list((schema.get("optional_params", {}) or {}).keys())
        params_upper = {p.upper() for p in (required + optional)}

        # 1) Fichiers .env.* locaux (développement)
        try:
            if os.path.exists(tool_dir):
                env_files = glob.glob(os.path.join(tool_dir, ".env.*"))
                for env_file in env_files:
                    filename = os.path.basename(env_file)
                    if filename == ".env" or not filename.startswith(".env."):
                        continue
                    profile_name = filename[5:]
                    env_vars = dotenv_values(env_file)
                    config = {k.lower(): v for k, v in env_vars.items() if v}
                    if config:
                        merge(profile_name, config, "env_file")
        except Exception as e:
            print(f"Warning: Failed to load env profiles for {tool_name}: {e}")

        # 2) Fichier centralisé config/.env (si présent)
        try:
            config_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "config", ".env")
            if os.path.exists(config_env_file):
                central_vars = dotenv_values(config_env_file)
                for profile, cfg in cls._profiles_from_envmap(tool_name, central_vars, params_upper).items():
                    merge(profile, cfg, "env_central")
        except Exception:
            pass

        # 3) Variables d'environnement runtime (Render)
        for profile, cfg in cls._profiles_from_envmap(tool_name, os.environ, params_upper).items():
            merge(profile, cfg, "env_runtime")

        # Transforme en liste
        profiles: List[Dict[str, Any]] = []
        for name, cfg in profiles_map.items():
            entry = {"name": name, "config": cfg, "source": profile_source.get(name, "env_runtime")}
            profiles.append(entry)
        return profiles

    @classmethod
    def _profiles_from_envmap(cls, tool_name: str, mapping: Dict[str, Any], params_upper: set) -> Dict[str, Dict[str, Any]]:
        """Extrait {profile: config} depuis un mapping type os.environ pour un outil"""
        tool_prefix = f"{tool_name.upper()}_"
        result: Dict[str, Dict[str, Any]] = {}
        if not params_upper:
            return result
        for key, value in mapping.items():
            if not isinstance(key, str) or not isinstance(value, (str, bytes)):
                continue
            if not key.startswith(tool_prefix):
                continue
            for param in params_upper:
                suffix = f"_{param}"
                if key.endswith(suffix):
                    profile = key[len(tool_prefix):-len(suffix)]
                    if not profile:
                        continue
                    result.setdefault(profile, {})[param.lower()] = value
                    break
        return result
    
    @classmethod
    def get_env_profile_path(cls, tool_name: str, profile_name: str) -> str:
        """Retourne le chemin vers le fichier .env d'un profil"""
        return os.path.join(
            cls.TOOLS_DIR, 
            tool_name, 
            f".env.{profile_name}"
        )
    
    @classmethod
    def save_env_profile(cls, tool_name: str, profile_name: str, config: Dict[str, str]) -> bool:
        """Sauvegarde un profil dans un fichier .env"""
        try:
            env_file_path = cls.get_env_profile_path(tool_name, profile_name)
            
            # S'assurer que le dossier existe
            os.makedirs(os.path.dirname(env_file_path), exist_ok=True)
            
            # Écrire le fichier .env
            with open(env_file_path, 'w', encoding='utf-8') as f:
                for key, value in config.items():
                    # Convertir en majuscules pour le format .env standard
                    env_key = key.upper()
                    f.write(f"{env_key}={value}\n")
            
            return True
        except Exception as e:
            print(f"Error saving env profile {profile_name} for {tool_name}: {e}")
            return False
    
    @classmethod
    def force_resync(cls):
        """Force la re-synchronisation complète des outils"""
        print("🔄 Force resync des outils...")
        cls._sync_tools_to_db()
        print("✅ Synchronisation terminée")
