#!/usr/bin/env python3
"""
Build System - Consolide les requirements et variables d'environnement
Usage: python build.py [--requirements-only|--env-only]
"""

import os
import glob
import subprocess
import sys
from pathlib import Path
from dotenv import dotenv_values

class BuildSystem:
    def __init__(self):
        self.tools_dir = "private/tools"
        self.config_dir = "../config"
        self.requirements_built = f"{self.config_dir}/requirements.txt"
        self.env_built = f"{self.config_dir}/.env"
    
    def discover_tools(self):
        """Scan tools directory pour découvrir tous les outils"""
        tools = []
        
        if not os.path.exists(self.tools_dir):
            print(f"⚠️  Tools directory '{self.tools_dir}' not found")
            return tools
            
        for tool_path in glob.glob(f"{self.tools_dir}/*/"):
            if os.path.isdir(tool_path):
                tool_name = os.path.basename(tool_path.rstrip('/'))
                if not tool_name.startswith('.') and tool_name != '__pycache__':
                    tools.append(tool_name)
        
        return sorted(tools)
    
    def build_requirements(self):
        """Consolide tous les requirements.txt des outils"""
        print("🔍 Scanning tool requirements...")
        
        # Dict pour gérer les versions : {package_name: highest_version}
        requirements_dict = {}
        tools_with_reqs = []
        
        for tool in self.discover_tools():
            req_file = f"{self.tools_dir}/{tool}/requirements.txt"
            if os.path.exists(req_file):
                try:
                    with open(req_file, 'r', encoding='utf-8') as f:
                        requirements = []
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                requirements.append(line)
                                
                                # Parse package name et version (support >=, ==, ~=)
                                for operator in ['>=', '==', '~=', '>', '<', '!=']:
                                    if operator in line:
                                        pkg_name = line.split(operator)[0].strip()
                                        pkg_version = line.split(operator)[1].strip()
                                        
                                        # Garde la version la plus élevée pour >=, sinon garde la contrainte exacte
                                        if operator == '>=' and (pkg_name not in requirements_dict or pkg_version > requirements_dict[pkg_name]):
                                            requirements_dict[pkg_name] = pkg_version
                                        elif operator != '>=' or pkg_name not in requirements_dict:
                                            requirements_dict[pkg_name] = f"{operator}{pkg_version}"
                                        break
                                else:
                                    # Pas de version spécifiée
                                    pkg_name = line.strip()
                                    if pkg_name and pkg_name not in requirements_dict:
                                        requirements_dict[pkg_name] = None
                        
                        if requirements:
                            tools_with_reqs.append(tool)
                            print(f"  📦 {tool}: {len(requirements)} packages")
                
                except Exception as e:
                    print(f"  ❌ Error reading {req_file}: {e}")
        
        # Le dossier config existe déjà
        
        # Met à jour la section built du requirements.txt
        self._update_requirements_section(requirements_dict, tools_with_reqs)
            
        return len(requirements_dict)
    
    def _update_requirements_section(self, requirements_dict, tools_with_reqs):
        """Met à jour la section built du requirements.txt"""
        try:
            # Lit le contenu existant
            if os.path.exists(self.requirements_built):
                with open(self.requirements_built, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                lines = ["# Base requirements\n", "fastapi\n", "uvicorn\n", "apscheduler\n", "\n"]
            
            # Trouve l'index de la section auto-generée
            built_start = -1
            for i, line in enumerate(lines):
                if "# Auto-generated requirements - DO NOT EDIT" in line:
                    built_start = i
                    break
            
            # Garde seulement la partie base
            if built_start != -1:
                base_lines = lines[:built_start]
            else:
                base_lines = lines
                
            # Nettoie les lignes vides en fin de section base
            while base_lines and base_lines[-1].strip() == "":
                base_lines.pop()
            
            # Ajoute la section built
            built_lines = [
                "\n\n# Auto-generated requirements - DO NOT EDIT\n",
                "# Run 'python build.py' to regenerate\n",
                f"# Consolidated from {len(tools_with_reqs)} tools: {', '.join(tools_with_reqs)}\n"
            ]
            
            for pkg_name in sorted(requirements_dict.keys()):
                version = requirements_dict[pkg_name]
                if version and not version.startswith(('>=', '==', '~=', '>', '<', '!=')):
                    built_lines.append(f"{pkg_name}>={version}\n")
                elif version:
                    built_lines.append(f"{pkg_name}{version}\n")
                else:
                    built_lines.append(f"{pkg_name}\n")
            
            # Écrit le fichier complet
            with open(self.requirements_built, 'w', encoding='utf-8') as f:
                f.writelines(base_lines + built_lines)
            
            print(f"📝 Updated {self.requirements_built} with {len(requirements_dict)} packages")
            
        except Exception as e:
            print(f"❌ Error updating requirements file: {e}")
            return 0
    
    def install_requirements(self):
        """Installe les dépendances consolidées"""
        if not os.path.exists(self.requirements_built):
            print("⚠️  No requirements-built.txt found")
            return False
            
        print(f"🚀 Installing dependencies from {self.requirements_built}...")
        
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', self.requirements_built], 
                capture_output=True, 
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                print("✅ Dependencies installed successfully")
                return True
            else:
                print(f"❌ Installation failed:")
                print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error during installation: {e}")
            return False
    
    def build_env_file(self):
        """Consolide tous les .env.* en .env.built"""
        print("🔍 Scanning environment profiles...")
        
        all_vars = {}
        profiles_found = []
        
        # Scan dans le dossier de chaque outil
        for tool in self.discover_tools():
            tool_path = f"{self.tools_dir}/{tool}"
            env_pattern = f"{tool_path}/.env.*"
            env_files = glob.glob(env_pattern)
            
            for env_file in env_files:
                try:
                    filename = os.path.basename(env_file)
                    
                    # Skip .env seul (pas de suffixe)
                    if filename == ".env":
                        continue
                    
                    # Extraire le nom du profil
                    if filename.startswith(".env."):
                        profile_suffix = filename[5:]  # Enlève ".env."
                        # Format final: TOOL_PROFILE
                        profile_name = f"{tool.upper()}_{profile_suffix}"
                    else:
                        continue
                    
                    config = dotenv_values(env_file)
                    
                    if config:  # Seulement si le fichier contient des variables
                        for key, value in config.items():
                            if key and value:  # Ignore les clés/valeurs vides
                                # Format: TOOL_PROFILE_VAR
                                env_key = f"{profile_name}_{key}"
                                all_vars[env_key] = value
                        
                        profiles_found.append(profile_name)
                        print(f"  🏷️  {profile_name}: {len(config)} variables")
                        
                except Exception as e:
                    print(f"  ❌ Error reading {env_file}: {e}")
        
        # Scan aussi à la racine du projet
        root_env_files = glob.glob("../.env.*_*")
        for env_file in root_env_files:
            try:
                profile_name = os.path.basename(env_file).replace('.env.', '')
                config = dotenv_values(env_file)
                
                if config:
                    for key, value in config.items():
                        if key and value:
                            env_key = f"{profile_name}_{key}"
                            all_vars[env_key] = value
                    
                    if profile_name not in profiles_found:
                        profiles_found.append(profile_name)
                        print(f"  🏷️  {profile_name}: {len(config)} variables")
                    
            except Exception as e:
                print(f"  ❌ Error reading {env_file}: {e}")
        
        # Met à jour la section built du .env
        self._update_env_section(all_vars, profiles_found)
            
        return len(all_vars)
    
    def _update_env_section(self, all_vars, profiles_found):
        """Met à jour la section built du .env"""
        try:
            # Lit le contenu existant
            base_content = ""
            if os.path.exists(self.env_built):
                with open(self.env_built, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Trouve la section built
                marker = "# DO NOT EDIT BELOW THIS LINE - Generated content"
                if marker in content:
                    base_content = content.split(marker)[0] + marker
                else:
                    base_content = content
            else:
                # Crée le contenu de base par défaut
                base_content = """# Base configuration
APP_NAME=MonSuperAPI
DEBUG=false
HOST=127.0.0.1
PORT=8000
VERSION=dev
DATABASE_URL=sqlite:///./database.db
SECRET_KEY=dev-secret-key-change-in-prod
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Built configuration (auto-updated by build.py)
# DO NOT EDIT BELOW THIS LINE - Generated content"""
            
            # Construit la section built
            built_content = f"\n# Profiles: {', '.join(sorted(profiles_found))}\n"
            
            for key, value in sorted(all_vars.items()):
                # Escape les valeurs qui contiennent des espaces ou caractères spéciaux
                if (' ' in str(value) or '=' in str(value)) and not (str(value).startswith('"') and str(value).endswith('"')):
                    value = f'"{value}"'
                built_content += f"{key}={value}\n"
            
            # Écrit le fichier complet
            with open(self.env_built, 'w', encoding='utf-8') as f:
                f.write(base_content + built_content)
            
            print(f"📝 Updated {self.env_built} with {len(all_vars)} variables")
            
        except Exception as e:
            print(f"❌ Error updating env file: {e}")
            import traceback
            print(traceback.format_exc())
            return 0
    
    def run_full_build(self):
        """Build complet : requirements + env"""
        print("🏗️  Starting build process...")
        discovered_tools = self.discover_tools()
        print(f"🔍 Discovered tools: {', '.join(discovered_tools)}")
        
        req_count = self.build_requirements()
        env_count = self.build_env_file()
        
        if req_count > 0:
            success = self.install_requirements()
            if not success:
                print("⚠️  Build completed with installation errors")
                return False
        
        # Validation finale
        self._validate_build()
        
        print(f"✅ Build complete: {req_count} packages, {env_count} variables")
        return True
    
    def _validate_build(self):
        """Valide que les fichiers générés sont cohérents"""
        try:
            # Vérifie requirements.txt
            if os.path.exists(self.requirements_built):
                with open(self.requirements_built, 'r') as f:
                    req_content = f.read()
                    if "# Auto-generated requirements" not in req_content:
                        print("⚠️  Warning: requirements.txt missing build section")
            
            # Vérifie .env
            if os.path.exists(self.env_built):
                with open(self.env_built, 'r') as f:
                    env_content = f.read()
                    if "# DO NOT EDIT BELOW THIS LINE" not in env_content:
                        print("⚠️  Warning: .env missing build section")
            
            print("✅ Build validation passed")
            
        except Exception as e:
            print(f"⚠️  Build validation warning: {e}")

def main():
    builder = BuildSystem()
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--requirements-only":
            count = builder.build_requirements()
            if count > 0:
                builder.install_requirements()
        elif arg == "--env-only":
            builder.build_env_file()
        elif arg == "--help" or arg == "-h":
            print(__doc__)
            print("Options:")
            print("  --requirements-only  Build and install requirements only")
            print("  --env-only          Build environment variables only")
            print("  --help, -h          Show this help message")
        else:
            print(f"Unknown option: {arg}")
            print("Use --help for available options")
            sys.exit(1)
    else:
        success = builder.run_full_build()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()