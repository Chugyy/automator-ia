#!/usr/bin/env python3
"""Test script for Notion page content retrieval"""

from ..private.tools.notion.main import NotionTool
import os
from dotenv import load_dotenv

def test_page_content():
    """Test page content retrieval"""
    # Charger le .env du backend
    load_dotenv("/Users/hugohoarau/Desktop/CODE/CODE_TEMPLATES/BASE_BUSINESS_CURSOR/backend/config/.env")
    
    # Configuration simple - juste le token
    config = {
        "token": os.getenv("NOTION_TEST_TOKEN"),
        "page_size": 100,
        "timeout": 30
    }
    
    tool = NotionTool(config=config)
    
    # Authentification
    if not tool.authenticate():
        print("❌ Authentification failed - Token:", config.get("token", "Not found"))
        return
    
    print("✅ Authentication successful")
    
    # Test avec un ID de page
    page_id = "2685cce4-8f1a-808a-94b6-f3f625bbc6a9"
    
    print(f"\nTesting page content retrieval for ID: {page_id}")
    print("=" * 60)
    
    # Test récupération métadonnées
    print("1. Getting page metadata...")
    page_result = tool.execute("get_page_from_url", {
        "url": f"https://www.notion.so/OpenAI-{page_id.replace('-', '')}?source=copy_link"
    })
    
    print(f"Page metadata result: {page_result.get('status', 'error')}")
    if page_result.get('data'):
        page_data = page_result['data']
        print(f"   Title: {page_data.get('properties', {}).get('title', {}).get('title', [{}])[0].get('text', {}).get('content', 'No title')}")
        print(f"   Created: {page_data.get('created_time')}")
        print(f"   Last edited: {page_data.get('last_edited_time')}")
    else:
        print(f"   Error: {page_result.get('error')}")
    
    print("\n2. Getting page content...")
    content_result = tool.execute("get_page_content", {"page_id": page_id})
    
    print(f"Content result: {content_result.get('status', 'error')}")
    if content_result.get('data'):
        blocks = content_result['data']['blocks']
        print(f"   Found {len(blocks)} blocks")
        
        for i, block in enumerate(blocks[:3]):  # Show first 3 blocks
            block_type = block.get('type', 'unknown')
            print(f"   Block {i+1}: {block_type}")
            
            # Show text content if available
            if block_type in ['paragraph', 'heading_1', 'heading_2', 'heading_3']:
                rich_text = block.get(block_type, {}).get('rich_text', [])
                if rich_text:
                    text = ''.join([t.get('text', {}).get('content', '') for t in rich_text])
                    print(f"      Text: {text[:100]}...")
        
        if len(blocks) > 3:
            print(f"   ... and {len(blocks) - 3} more blocks")
    else:
        print(f"   Error: {content_result.get('error')}")

if __name__ == "__main__":
    test_page_content()