#!/usr/bin/env python3
"""
Quick script to view all memories in the database.
Useful for debugging and verification.
"""

import sqlite3
import json

# Database file path
DB_PATH = "chat_app.db"

def view_all_memories():
    """Display all memories organized by type."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all memories organized by type
    cursor.execute("SELECT id, type, key, value FROM memories ORDER BY type, key")
    rows = cursor.fetchall()
    
    if not rows:
        print("No memories found in database.")
        return
    
    # Organize by type
    memories_by_type = {}
    for row in rows:
        memory_id, memory_type, key, value = row
        if memory_type not in memories_by_type:
            memories_by_type[memory_type] = []
        memories_by_type[memory_type].append({
            "id": memory_id,
            "key": key,
            "value": value
        })
    
    # Display organized memories
    print("🧠 Current Memories in Database")
    print("=" * 60)
    
    type_icons = {
        "identity": "🧭",
        "principles": "📜", 
        "focus": "🎯",
        "signals": "🌡️"
    }
    
    for memory_type, memories in memories_by_type.items():
        icon = type_icons.get(memory_type, "📝")
        print(f"\n{icon} {memory_type.upper()} ({len(memories)} items)")
        print("-" * 40)
        
        for memory in memories:
            print(f"  🔑 {memory['key']}")
            print(f"     {memory['value']}")
            print(f"     ID: {memory['id'][:8]}...")
            print()
    
    conn.close()
    
    total_count = sum(len(memories) for memories in memories_by_type.values())
    print(f"📊 Total: {total_count} memories across {len(memories_by_type)} categories")

if __name__ == "__main__":
    view_all_memories()