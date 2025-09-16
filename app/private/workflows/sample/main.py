from typing import Dict, Any, List
from app.private.tools.example_tool.main import ExampleTool
from app.private.tools.notion.main import NotionTool

def execute(data: Dict[str, Any] = None, tools: Dict[str, Any] = None) -> Dict[str, Any]:
    tools_config = build_tools_config(data)
    
    tools_instances = {}
    for tool_name, config in tools_config.items():
        if tool_name == "example":
            if "profile" in config:
                tools_instances[tool_name] = ExampleTool(profile=config["profile"])
            else:
                tools_instances[tool_name] = ExampleTool(config=config["config"])
        elif tool_name == "notion":
            if "profile" in config:
                tools_instances[tool_name] = NotionTool(profile=config["profile"])
            else:
                tools_instances[tool_name] = NotionTool(config=config["config"])
    
    return execute_business_logic(tools_instances, data)

def build_tools_config(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    tools_profiles = get_tools_profiles()
    
    config = {}
    for tool_name, profile in tools_profiles.items():
        if profile.startswith("INPUT_"):
            input_key = profile.replace("INPUT_", "").lower()
            config[tool_name] = {"config": {input_key: data.get(input_key)}}
        else:
            config[tool_name] = {"profile": profile}
    
    return config

def get_required_inputs() -> List[Dict[str, Any]]:
    return [
        {
            "name": "example_key",
            "type": "password",
            "label": "Clé Example",
            "required": True,
            "description": "Votre clé API Example"
        },
        {
            "name": "target_message",
            "type": "text",
            "label": "Message cible",
            "required": False,
            "description": "Message à traiter"
        }
    ]

def get_tools_profiles() -> Dict[str, str]:
    return {
        "example": "INPUT_EXAMPLE_KEY",
        "notion": "TEST"
    }

def execute_business_logic(tools: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    example_tool = tools.get("example")
    notion_tool = tools.get("notion")
    
    if not example_tool or not notion_tool:
        return {"success": False, "error": "Tools initialization failed"}
    
    message = data.get("target_message", "Workflow execution")
    
    example_result = example_tool.execute("example_action", {"message": message})
    if not example_result.get("success"):
        return {"success": False, "error": f"Example tool failed: {example_result.get('error')}"}
    
    notion_result = notion_tool.execute("test_connection")
    if not notion_result.get("success"):
        return {"success": False, "error": f"Notion tool failed: {notion_result.get('error')}"}
    
    return {
        "success": True,
        "result": {
            "example_output": example_result["result"],
            "notion_status": notion_result["result"],
            "processed_message": message
        }
    }