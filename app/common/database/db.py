import sqlite3
from pathlib import Path
import json

DB_PATH = Path(__file__).parent / "database.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workflows (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        display_name TEXT,
        description TEXT,
        category TEXT,
        schedule TEXT,
        triggers TEXT,
        tools_required TEXT,
        tool_profiles TEXT,
        author TEXT,
        version TEXT DEFAULT '1.0.0',
        active BOOLEAN DEFAULT 1,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Migration: ajouter la colonne tool_profiles si elle n'existe pas
    cursor.execute("PRAGMA table_info(workflows)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'tool_profiles' not in columns:
        cursor.execute("ALTER TABLE workflows ADD COLUMN tool_profiles TEXT DEFAULT '{}'")
        print("Migration: Ajout de la colonne tool_profiles à la table workflows")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tools (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        display_name TEXT,
        logo_path TEXT,
        config_path TEXT,
        readme_path TEXT,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tool_profiles (
        id TEXT PRIMARY KEY,
        tool_id TEXT NOT NULL,
        profile_name TEXT NOT NULL,
        config_data TEXT,
        is_default BOOLEAN DEFAULT 0,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tool_id) REFERENCES tools (id),
        UNIQUE(tool_id, profile_name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        entity_id TEXT,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        execution_id TEXT,
        context_data TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interfaces (
        id TEXT PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        display_name TEXT,
        description TEXT,
        route TEXT NOT NULL,
        icon TEXT,
        file_path TEXT,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scheduled_jobs (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        cron_expression TEXT NOT NULL,
        active BOOLEAN DEFAULT 1,
        next_run TIMESTAMP,
        last_run TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (workflow_id) REFERENCES workflows (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id TEXT PRIMARY KEY,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL,
        category TEXT,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workflow_executions (
        id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        trigger_type TEXT NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        duration REAL,
        status TEXT DEFAULT 'running',
        input_data TEXT,
        result TEXT,
        error TEXT,
        FOREIGN KEY (workflow_id) REFERENCES workflows (id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_entity ON logs(entity_type, entity_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_executions_workflow ON workflow_executions(workflow_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_tool ON tool_profiles(tool_id)")

    conn.commit()
    conn.close()

def get_db_connection():
    if not DB_PATH.exists():
        init_db()
    return sqlite3.connect(DB_PATH)