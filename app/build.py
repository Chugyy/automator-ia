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
                                
                                # Parse package name et version
                                if '>=' in line:
                                    pkg_name = line.split('>=')[0]
                                    pkg_version = line.split('>=')[1]
                                    
                                    # Garde la version la plus élevée
                                    if pkg_name not in requirements_dict or pkg_version > requirements_dict[pkg_name]:
                                        requirements_dict[pkg_name] = pkg_version
                                else:
                                    # Pas de version spécifiée
                                    pkg_name = line
                                    if pkg_name not in requirements_dict:
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
                lines = ["# Base requirements\n"]
            
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
                
            # Ajoute la section built
            built_lines = [
                "\n# Auto-generated requirements - DO NOT EDIT\n",
                "# Run 'python build.py' to regenerate\n",
                f"# Consolidated from {len(tools_with_reqs)} tools: {', '.join(tools_with_reqs)}\n"
            ]
            
            for pkg_name in sorted(requirements_dict.keys()):
                version = requirements_dict[pkg_name]
                if version:
                    built_lines.append(f"{pkg_name}>={version}\n")
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
            if os.path.exists(self.env_built):
                with open(self.env_built, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # Trouve l'index de la section auto-generée
            built_start = -1
            for i, line in enumerate(lines):
                if "# DO NOT EDIT BELOW THIS LINE - Generated content" in line:
                    built_start = i
                    break
            
            # Garde seulement la partie base
            if built_start != -1:
                base_lines = lines[:built_start + 1]
            else:
                base_lines = lines + ["\n# Built configuration (auto-updated by build.py)\n# DO NOT EDIT BELOW THIS LINE - Generated content\n"]
                
            # Ajoute les variables built
            built_lines = [f"\n# Profiles: {', '.join(sorted(profiles_found))}\n"]
            
            for key, value in sorted(all_vars.items()):
                # Escape les valeurs qui contiennent des espaces
                if ' ' in value and not (value.startswith('"') and value.endswith('"')):
                    value = f'"{value}"'
                built_lines.append(f"{key}={value}\n")
            
            # Écrit le fichier complet
            with open(self.env_built, 'w', encoding='utf-8') as f:
                f.writelines(base_lines + built_lines)
            
            print(f"📝 Updated {self.env_built} with {len(all_vars)} variables")
            
        except Exception as e:
            print(f"❌ Error updating env file: {e}")
            return 0
    
    def run_full_build(self):
        """Build complet : requirements + env"""
        print("🏗️  Starting build process...")
        print(f"🔍 Discovered tools: {', '.join(self.discover_tools())}")
        
        req_count = self.build_requirements()
        env_count = self.build_env_file()
        
        if req_count > 0:
            success = self.install_requirements()
            if not success:
                print("⚠️  Build completed with installation errors")
                return False
        
        print(f"✅ Build complete: {req_count} packages, {env_count} variables")
        return True

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