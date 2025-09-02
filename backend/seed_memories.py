#!/usr/bin/env python3
"""
Seed script to populate the memories database with sample data.
This creates realistic memories across all 4 categories for demo purposes.
"""

import sqlite3
import uuid
from datetime import datetime

# Database file path (same as in main.py)
DB_PATH = "chat_app.db"

# Sample memories organized by type
SAMPLE_MEMORIES = {
    "identity": [
        {"key": "name", "value": "I'm Alex, a software engineer passionate about AI and human-computer interaction"},
        {"key": "role", "value": "Senior Backend Developer at a fintech startup, focusing on API design and scalability"},
        {"key": "background", "value": "Computer Science graduate with 5 years experience in Python, distributed systems"},
        {"key": "interests", "value": "Machine learning, open source projects, rock climbing, and cooking"},
        {"key": "values", "value": "I believe in building technology that empowers people and creates genuine value"},
        {"key": "location", "value": "Based in San Francisco, originally from Portland"},
    ],
    
    "principles": [
        {"key": "code_quality", "value": "Write code that tells a story - clear, maintainable, and well-tested"},
        {"key": "collaboration", "value": "Best solutions emerge from diverse perspectives and respectful dialogue"},
        {"key": "learning", "value": "Stay curious and embrace being wrong - it's how we grow"},
        {"key": "user_focus", "value": "Every technical decision should ultimately serve the end user's needs"},
        {"key": "sustainability", "value": "Build systems that can evolve and scale without burning out the team"},
        {"key": "transparency", "value": "Share knowledge openly and document decisions for future context"},
    ],
    
    "focus": [
        {"key": "current_project", "value": "Leading the redesign of our payment processing API for better reliability"},
        {"key": "learning_goal", "value": "Deep diving into Rust for systems programming and performance optimization"},
        {"key": "team_priority", "value": "Mentoring two junior developers and improving our code review process"},
        {"key": "personal_project", "value": "Building an open-source tool for API documentation generation"},
        {"key": "health_goal", "value": "Maintaining work-life balance with regular climbing sessions 3x per week"},
        {"key": "reading", "value": "Currently reading 'Designing Data-Intensive Applications' by Martin Kleppmann"},
    ],
    
    "signals": [
        {"key": "energy_pattern", "value": "Most productive in morning hours, creative thinking peaks around 10-11 AM"},
        {"key": "stress_indicator", "value": "When I start over-engineering simple solutions, it's time to step back"},
        {"key": "team_dynamic", "value": "Notice increased collaboration when we do regular pair programming sessions"},
        {"key": "learning_style", "value": "Learn best through hands-on projects rather than theoretical study"},
        {"key": "decision_making", "value": "Tend to overthink architecture decisions - setting 2-day decision deadlines helps"},
        {"key": "motivation", "value": "Most energized when working on problems that directly impact user experience"},
    ]
}

def init_database():
    """Initialize the database and create the memories table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create memories table (same schema as main.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print("✓ Database initialized")

def clear_existing_memories():
    """Clear all existing memories from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM memories")
    rows_deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    print(f"✓ Cleared {rows_deleted} existing memories")

def seed_memories():
    """Insert sample memories into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_inserted = 0
    
    for memory_type, memories in SAMPLE_MEMORIES.items():
        print(f"\n📝 Seeding {memory_type} memories...")
        
        for memory in memories:
            memory_id = str(uuid.uuid4())
            
            cursor.execute(
                "INSERT INTO memories (id, type, key, value) VALUES (?, ?, ?, ?)",
                (memory_id, memory_type, memory["key"], memory["value"])
            )
            
            print(f"  + {memory['key']}: {memory['value'][:50]}...")
            total_inserted += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Successfully seeded {total_inserted} memories across all categories")

def verify_seeded_data():
    """Verify the seeded data by querying the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n🔍 Verifying seeded data:")
    
    for memory_type in SAMPLE_MEMORIES.keys():
        cursor.execute("SELECT COUNT(*) FROM memories WHERE type = ?", (memory_type,))
        count = cursor.fetchone()[0]
        print(f"  {memory_type}: {count} memories")
    
    # Show total count
    cursor.execute("SELECT COUNT(*) FROM memories")
    total_count = cursor.fetchone()[0]
    print(f"  Total: {total_count} memories")
    
    conn.close()

def main():
    """Main function to run the seeding process."""
    print("🌱 Starting memory seeding process...")
    print("=" * 50)
    
    try:
        # Initialize database
        init_database()
        
        # Clear existing data
        clear_existing_memories()
        
        # Seed new data
        seed_memories()
        
        # Verify the results
        verify_seeded_data()
        
        print("\n" + "=" * 50)
        print("🎉 Memory seeding completed successfully!")
        print("\nYou can now start the backend server and see the seeded memories in the UI.")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())