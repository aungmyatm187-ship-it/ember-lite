"""
Ember Lessons System
Ember learns from its own mistakes

Philosophy: "No record, no evidence"
→ "No mistake record, no improvement"
"""

import sqlite3
import os
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(__file__), "lessons.db")


def init_lessons_db():
    """Create the lessons database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_type TEXT NOT NULL,
            trigger_pattern TEXT,
            mistake TEXT NOT NULL,
            root_cause TEXT,
            fix TEXT NOT NULL,
            prevention TEXT,
            severity TEXT DEFAULT 'medium',
            learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            times_encountered INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()
    return DB_PATH


def record_lesson(lesson_type, mistake, fix, root_cause=None,
                  prevention=None, trigger_pattern=None, severity="medium"):
    """
    Record a lesson
    
    Args:
        lesson_type: "syntax_error", "logic_error", "runtime_error", "process_error"
        mistake: what went wrong
        fix: how it was fixed
        root_cause: root cause
        prevention: how to avoid it next time
        trigger_pattern: which pattern to watch for
        severity: "low", "medium", "high", "critical"
    """
    init_lessons_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if this lesson already exists
    c.execute("""
        SELECT id, times_encountered FROM lessons
        WHERE mistake = ? AND fix = ?
    """, (mistake, fix))
    existing = c.fetchone()
    
    if existing:
        # If it exists, increment the count
        c.execute("""
            UPDATE lessons
            SET times_encountered = times_encountered + 1
            WHERE id = ?
        """, (existing[0],))
        lesson_id = existing[0]
        print(f"📚 Lesson #{lesson_id} reinforced (encountered {existing[1] + 1} times)")
    else:
        # Insert new
        c.execute("""
            INSERT INTO lessons
            (lesson_type, trigger_pattern, mistake, root_cause, fix, prevention, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            lesson_type, trigger_pattern, mistake,
            root_cause, fix, prevention, severity
        ))
        lesson_id = c.lastrowid
        print(f"📚 Lesson #{lesson_id} recorded")
    
    conn.commit()
    conn.close()
    return lesson_id


def get_lessons(lesson_type=None, severity=None, limit=20):
    """Fetch lessons"""
    init_lessons_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = "SELECT * FROM lessons WHERE 1=1"
    params = []
    
    if lesson_type:
        query += " AND lesson_type = ?"
        params.append(lesson_type)
    
    if severity:
        query += " AND severity = ?"
        params.append(severity)
    
    query += " ORDER BY times_encountered DESC, learned_at DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0],
            "type": r[1],
            "trigger_pattern": r[2],
            "mistake": r[3],
            "root_cause": r[4],
            "fix": r[5],
            "prevention": r[6],
            "severity": r[7],
            "learned_at": r[8],
            "times_encountered": r[9]
        }
        for r in rows
    ]


def check_for_pattern(code_or_command: str) -> list:
    """
    Inspect code or command and warn about possible issues
    (Ember can use this before running a command)
    """
    init_lessons_db()
    warnings = []
    
    lessons = get_lessons(limit=100)
    for lesson in lessons:
        pattern = lesson.get("trigger_pattern")
        if not pattern:
            continue
        
        # Simple substring matching
        if pattern.lower() in code_or_command.lower():
            warnings.append({
                "lesson_id": lesson["id"],
                "pattern": pattern,
                "warning": lesson["mistake"],
                "fix": lesson["fix"],
                "severity": lesson["severity"]
            })
    
    return warnings


def summary() -> str:
    """Summary of lessons"""
    init_lessons_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM lessons")
    total = c.fetchone()[0]
    
    c.execute("""
        SELECT lesson_type, COUNT(*) 
        FROM lessons GROUP BY lesson_type
    """)
    by_type = c.fetchall()
    
    c.execute("""
        SELECT SUM(times_encountered) FROM lessons
    """)
    total_encounters = c.fetchone()[0] or 0
    
    conn.close()
    
    lines = [
        "=" * 60,
        "  📚 Ember Lessons Summary",
        "=" * 60,
        f"",
        f"  Total Lessons:      {total}",
        f"  Total Encounters:   {total_encounters}",
        f"",
        f"  By Type:",
    ]
    
    for lesson_type, count in by_type:
        lines.append(f"    • {lesson_type}: {count}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


# =========================================================
# SEED: Record today's mistakes
# =========================================================

def seed_initial_lessons():
    """Insert the initial lessons"""
    
    # Lesson 1: Python Reserved Keyword
    record_lesson(
        lesson_type="syntax_error",
        trigger_pattern="from=context.get",
        mistake="Accidentally used Python reserved keyword 'from' as a keyword argument",
        root_cause="'from' is a Python reserved keyword, so it cannot be used as a keyword argument",
        fix="Rename 'from' to 'from_val' and update the placeholder in the template",
        prevention="Before naming variables or arguments, check them against Python's reserved keyword list",
        severity="high"
    )
    
    # Lesson 2: Copy/Paste Duplicate Lines
    record_lesson(
        lesson_type="process_error",
        trigger_pattern="duplicate_lines",
        mistake="Copy/pasting long code in Termux duplicated lines and caused a syntax error",
        root_cause="Termux's terminal sometimes mishandles multi-line paste",
        fix="Write the script file in one shot using 'cat > file << ENDOFFILE'; use 'ENDOFFILE' instead of 'EOF'",
        prevention="After writing code, always check syntax with 'python3 -m py_compile file.py'",
        severity="high"
    )
    
    # Lesson 3: Heredoc Delimiter Collision
    record_lesson(
        lesson_type="process_error",
        trigger_pattern="<< 'EOF'",
        mistake="When 'EOF' appeared in the file content, the heredoc closed prematurely",
        root_cause="The heredoc delimiter was not unique and got confused with 'EOF' in the content",
        fix="Change the delimiter to a unique word like 'ENDOFFILE'",
        prevention="When using heredoc, always use a unique delimiter instead of 'EOF'",
        severity="medium"
    )
    
    print("✅ Seed lessons recorded.")


if __name__ == "__main__":
    print("=" * 60)
    print("  Testing Lessons System")
    print("=" * 60)
    print()
    
    init_lessons_db()
    seed_initial_lessons()
    
    print()
    print(summary())
    
    print("\n🔍 Testing pattern check:")
    test_code = """
    message = rule["template"].format(
        from=context.get("from", "?"),
        to=context.get("to", "?")
    )
    """
    warnings = check_for_pattern(test_code)
    
    if warnings:
        for w in warnings:
            print(f"   ⚠️  [{w['severity'].upper()}] Lesson #{w['lesson_id']}")
            print(f"      Mistake: {w['warning']}")
            print(f"      Fix: {w['fix']}")
    else:
        print("   ✅ No issues detected.")
    
    print("\n✅ Lessons test complete.")
