from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import secrets
import string

def generate_id(prefix: str) -> str:
    chars = string.ascii_lowercase + string.digits
    suffix = ''.join(secrets.choice(chars) for _ in range(8))
    return f"{prefix}_{suffix}"

class WorkflowModel(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("WF"))
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    schedule: Optional[str] = None
    triggers: List[str] = Field(default_factory=list)
    tools_required: List[str] = Field(default_factory=list)
    tool_profiles: Dict[str, str] = Field(default_factory=dict)  # {tool_name: profile}
    author: Optional[str] = None
    version: str = "1.0.0"
    active: bool = True
    file_path: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class ToolModel(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("TL"))
    name: str
    display_name: Optional[str] = None
    logo_path: Optional[str] = None
    config_path: Optional[str] = None
    readme_path: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class ToolProfileModel(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("TP"))
    tool_id: str
    profile_name: str
    config_data: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    active: bool = True
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class LogModel(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("LG"))
    entity_type: str
    entity_id: Optional[str] = None
    level: str
    message: str
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    execution_id: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None

class InterfaceModel(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("IF"))
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    route: str
    icon: Optional[str] = None
    file_path: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class ScheduledJobModel(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("SJ"))
    workflow_id: str
    cron_expression: str
    active: bool = True
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class SettingModel(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("ST"))
    key: str
    value: str
    category: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

class WorkflowExecutionModel(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("WE"))
    workflow_id: str
    trigger_type: str
    start_time: Optional[datetime] = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    status: str = "running"
    input_data: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None