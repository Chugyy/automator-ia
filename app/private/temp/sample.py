#!/usr/bin/env python3
"""Script de test temporaire pour ExampleTool"""

import sys
import os
from pathlib import Path

from ..tools.sample.main import ExampleTool
from dotenv import load_dotenv

def main():
    load_dotenv("backend/config/.env")
    
    config = {
        "api_key": "test_api_key_123",
        "base_url": "https://api.example.com"
    }
    
    tool = ExampleTool(config=config)
    
    print("=== Test ExampleTool en mode direct ===")
    
    if tool.authenticate():
        print("✓ Authentification réussie")
        
        test_result = tool.execute("test_connection")
        if test_result["success"]:
            print(f"✓ Test connexion: {test_result['result']}")
        else:
            print(f"✗ Test connexion échoué: {test_result['error']}")
        
        example_result = tool.execute("example_action", {"message": "Test depuis script temp"})
        if example_result["success"]:
            print(f"✓ Action example: {example_result['result']}")
        else:
            print(f"✗ Action example échouée: {example_result['error']}")
            
    else:
        print("✗ Échec authentification")

if __name__ == "__main__":
    main()