import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from .db import get_db_connection
from .models import *

def _serialize_json(data: Any) -> str:
    if isinstance(data, (list, dict)):
        return json.dumps(data)
    return str(data) if data is not None else None

def _deserialize_json(data: str) -> Any:
    if not data:
        return None
    try:
        return json.loads(data)
    except:
        return data

# WORKFLOWS
def create_workflow(workflow: WorkflowModel) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workflows (id, name, display_name, description, category, schedule, 
                             triggers, tools_required, tool_profiles, author, version, active, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (workflow.id, workflow.name, workflow.display_name, workflow.description,
          workflow.category, workflow.schedule, _serialize_json(workflow.triggers),
          _serialize_json(workflow.tools_required), _serialize_json(workflow.tool_profiles),
          workflow.author, workflow.version, workflow.active, workflow.file_path))
    conn.commit()
    conn.close()
    return workflow.id

def get_workflow(workflow_id: str) -> Optional[WorkflowModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM workflows WHERE id = ? AND active = 1", (workflow_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(zip([desc[0] for desc in cursor.description], row))
        data['triggers'] = _deserialize_json(data['triggers']) or []
        data['tools_required'] = _deserialize_json(data['tools_required']) or []
        data['tool_profiles'] = _deserialize_json(data.get('tool_profiles', '{}')) or {}
        return WorkflowModel(**data)
    return None

def list_workflows(active_only: bool = False) -> List[WorkflowModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM workflows"
    if active_only:
        query += " WHERE active = 1"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    workflows = []
    for row in rows:
        data = dict(zip([desc[0] for desc in cursor.description], row))
        data['triggers'] = _deserialize_json(data['triggers']) or []
        data['tools_required'] = _deserialize_json(data['tools_required']) or []
        data['tool_profiles'] = _deserialize_json(data.get('tool_profiles', '{}')) or {}
        workflows.append(WorkflowModel(**data))
    return workflows

def update_workflow(workflow_id: str, updates: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = [_serialize_json(v) if k in ['triggers', 'tools_required', 'tool_profiles'] else v for k, v in updates.items()]
    values.append(workflow_id)
    cursor.execute(f"UPDATE workflows SET {set_clause} WHERE id = ?", values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def delete_workflow(workflow_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE workflows SET active = 0 WHERE id = ?", (workflow_id,))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

# TOOLS
def create_tool(tool: ToolModel) -> str:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO tools (id, name, display_name, logo_path, config_path, readme_path, active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tool.id, tool.name, tool.display_name, tool.logo_path,
              tool.config_path, tool.readme_path, tool.active))
        conn.commit()
        return tool.id
    except sqlite3.Error as e:
        conn.rollback()
        print(f"⚠️ Erreur création outil {tool.name}: {e}")
        return None
    finally:
        conn.close()

def get_tool(tool_id: str) -> Optional[ToolModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tools WHERE id = ? AND active = 1", (tool_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(zip([desc[0] for desc in cursor.description], row))
        return ToolModel(**data)
    return None

def get_tool_by_name(name: str, active_only: bool = True) -> Optional[ToolModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM tools WHERE name = ?"
    if active_only:
        query += " AND active = 1"
    cursor.execute(query, (name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(zip([desc[0] for desc in cursor.description], row))
        return ToolModel(**data)
    return None

def list_tools(active_only: bool = False) -> List[ToolModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM tools"
    if active_only:
        query += " WHERE active = 1"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [ToolModel(**dict(zip([desc[0] for desc in cursor.description], row))) for row in rows]

def update_tool(tool_id: str, updates: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(tool_id)
        cursor.execute(f"UPDATE tools SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        conn.rollback()
        print(f"⚠️ Erreur mise à jour outil {tool_id}: {e}")
        return False
    finally:
        conn.close()

# TOOL PROFILES
def create_tool_profile(profile: ToolProfileModel) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tool_profiles (id, tool_id, profile_name, config_data, is_default, active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (profile.id, profile.tool_id, profile.profile_name, 
          _serialize_json(profile.config_data), profile.is_default, profile.active))
    conn.commit()
    conn.close()
    return profile.id

def get_tool_profiles(tool_id: str) -> List[ToolProfileModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tool_profiles WHERE tool_id = ? AND active = 1", (tool_id,))
    rows = cursor.fetchall()
    conn.close()
    profiles = []
    for row in rows:
        data = dict(zip([desc[0] for desc in cursor.description], row))
        data['config_data'] = _deserialize_json(data['config_data']) or {}
        profiles.append(ToolProfileModel(**data))
    return profiles

def update_tool_profile(profile_id: str, updates: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = [_serialize_json(v) if k == 'config_data' else v for k, v in updates.items()]
    values.append(profile_id)
    cursor.execute(f"UPDATE tool_profiles SET {set_clause} WHERE id = ?", values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def delete_tool_profile(profile_id: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tool_profiles SET active = 0 WHERE id = ?", (profile_id,))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

# LOGS
def create_log(log: LogModel) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (id, entity_type, entity_id, level, message, execution_id, context_data)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (log.id, log.entity_type, log.entity_id, log.level, log.message,
          log.execution_id, _serialize_json(log.context_data)))
    conn.commit()
    conn.close()
    return log.id

def get_logs(entity_type: str = None, entity_id: str = None, limit: int = 100) -> List[LogModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM logs"
    params = []
    if entity_type:
        query += " WHERE entity_type = ?"
        params.append(entity_type)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    logs = []
    for row in rows:
        data = dict(zip([desc[0] for desc in cursor.description], row))
        data['context_data'] = _deserialize_json(data['context_data'])
        logs.append(LogModel(**data))
    return logs

# WORKFLOW EXECUTIONS
def create_workflow_execution(execution: WorkflowExecutionModel) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO workflow_executions (id, workflow_id, trigger_type, status, input_data)
        VALUES (?, ?, ?, ?, ?)
    """, (execution.id, execution.workflow_id, execution.trigger_type,
          execution.status, _serialize_json(execution.input_data)))
    conn.commit()
    conn.close()
    return execution.id

def update_workflow_execution(execution_id: str, updates: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = [_serialize_json(v) if k in ['input_data', 'result'] else v for k, v in updates.items()]
    values.append(execution_id)
    cursor.execute(f"UPDATE workflow_executions SET {set_clause} WHERE id = ?", values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

def get_workflow_executions(workflow_id: str = None, limit: int = 50) -> List[WorkflowExecutionModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM workflow_executions"
    params = []
    if workflow_id:
        query += " WHERE workflow_id = ?"
        params.append(workflow_id)
    query += " ORDER BY start_time DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    executions = []
    for row in rows:
        data = dict(zip([desc[0] for desc in cursor.description], row))
        data['input_data'] = _deserialize_json(data['input_data'])
        data['result'] = _deserialize_json(data['result'])
        executions.append(WorkflowExecutionModel(**data))
    return executions

# INTERFACES
def create_interface(interface: InterfaceModel) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO interfaces (id, name, display_name, description, route, icon, file_path, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (interface.id, interface.name, interface.display_name, interface.description,
          interface.route, interface.icon, interface.file_path, interface.active))
    conn.commit()
    conn.close()
    return interface.id

def list_interfaces(active_only: bool = True) -> List[InterfaceModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM interfaces"
    if active_only:
        query += " WHERE active = 1"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [InterfaceModel(**dict(zip([desc[0] for desc in cursor.description], row))) for row in rows]

# SETTINGS
def create_setting(setting: SettingModel) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO settings (id, key, value, category, active)
        VALUES (?, ?, ?, ?, ?)
    """, (setting.id, setting.key, setting.value, setting.category, setting.active))
    conn.commit()
    conn.close()
    return setting.id

def get_setting(key: str) -> Optional[SettingModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings WHERE key = ? AND active = 1", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(zip([desc[0] for desc in cursor.description], row))
        return SettingModel(**data)
    return None

def list_settings(category: str = None) -> List[SettingModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM settings WHERE active = 1"
    params = []
    if category:
        query += " AND category = ?"
        params.append(category)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [SettingModel(**dict(zip([desc[0] for desc in cursor.description], row))) for row in rows]

def update_setting(setting_id: str, value: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE id = ?", (value, setting_id))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated

# SCHEDULED JOBS
def create_scheduled_job(job: ScheduledJobModel) -> str:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scheduled_jobs (id, workflow_id, cron_expression, active, next_run, last_run)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job.id, job.workflow_id, job.cron_expression, job.active, job.next_run, job.last_run))
    conn.commit()
    conn.close()
    return job.id

def get_scheduled_jobs(active_only: bool = True) -> List[ScheduledJobModel]:
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM scheduled_jobs"
    if active_only:
        query += " WHERE active = 1"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [ScheduledJobModel(**dict(zip([desc[0] for desc in cursor.description], row))) for row in rows]

def update_scheduled_job(job_id: str, updates: Dict[str, Any]) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [job_id]
    cursor.execute(f"UPDATE scheduled_jobs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated