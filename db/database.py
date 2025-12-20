"""
SQLite database for storing fridge history and user preferences.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Database file location
DB_PATH = Path(__file__).parent.parent / "data" / "fridge.db"


def get_connection():
    """Get database connection, creating tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Fridge history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fridge_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            detected_items TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User preferences table (single row)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            custom_instructions TEXT DEFAULT '',
            default_mode TEXT DEFAULT 'smart'
        )
    """)
    
    # Insert default preferences if not exists
    cursor.execute("""
        INSERT OR IGNORE INTO preferences (id, custom_instructions, default_mode)
        VALUES (1, '', 'smart')
    """)
    
    conn.commit()
    conn.close()
    print(f"📦 Database initialized at {DB_PATH}")


# ============ History Functions ============

def add_history(date: str, detected_items: dict) -> int:
    """
    Add a fridge detection to history.
    
    Args:
        date: Date string (YYYY-MM-DD)
        detected_items: Dict of item counts, e.g., {"milk": 2, "eggs": 6}
        
    Returns:
        ID of the new record
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO fridge_history (date, detected_items) VALUES (?, ?)",
        (date, json.dumps(detected_items))
    )
    
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"   💾 Saved detection to history (id={record_id}, date={date})")
    return record_id


def get_history(limit: int = 30) -> list[dict]:
    """
    Get recent fridge history, ordered by date descending.
    
    Returns:
        List of history records with id, date, items
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, date, detected_items, created_at FROM fridge_history ORDER BY date DESC LIMIT ?",
        (limit,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "date": row["date"],
            "items": json.loads(row["detected_items"]),
            "created_at": row["created_at"]
        })
    
    return history


def delete_history(record_id: int) -> bool:
    """Delete a history record by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM fridge_history WHERE id = ?", (record_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    if deleted:
        print(f"   🗑️ Deleted history record {record_id}")
    
    return deleted


def clear_history() -> int:
    """Delete all history records. Returns count deleted."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM fridge_history")
    count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"   🗑️ Cleared {count} history records")
    return count


# ============ Preferences Functions ============

def get_preferences() -> dict:
    """Get user preferences."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT custom_instructions, default_mode FROM preferences WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "custom_instructions": row["custom_instructions"] or "",
            "default_mode": row["default_mode"] or "smart"
        }
    return {"custom_instructions": "", "default_mode": "smart"}


def set_preferences(custom_instructions: str = None, default_mode: str = None) -> None:
    """Update user preferences."""
    conn = get_connection()
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    if custom_instructions is not None:
        updates.append("custom_instructions = ?")
        values.append(custom_instructions)
    
    if default_mode is not None:
        updates.append("default_mode = ?")
        values.append(default_mode)
    
    if updates:
        cursor.execute(
            f"UPDATE preferences SET {', '.join(updates)} WHERE id = 1",
            values
        )
        conn.commit()
    
    conn.close()


# ============ History Context for AI ============

def get_history_context(limit: int = 10) -> str:
    """
    Get history formatted for AI context.
    
    Returns string like:
    - Dec 18: milk x2, eggs x6, cheese x1
    - Dec 15: milk x1, eggs x3
    """
    history = get_history(limit)
    
    if not history:
        return "No previous fridge history available."
    
    lines = []
    for record in history:
        items_str = ", ".join(f"{k} x{v}" for k, v in record["items"].items())
        # Format date nicely
        try:
            dt = datetime.strptime(record["date"], "%Y-%m-%d")
            date_str = dt.strftime("%b %d")
        except:
            date_str = record["date"]
        lines.append(f"- {date_str}: {items_str}")
    
    return "\n".join(lines)


# Initialize on import
init_db()
