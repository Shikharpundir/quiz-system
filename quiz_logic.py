
import sqlite3
import random

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_all_categories():
    """Fetches unique subjects for the Dashboard Cards"""
    db = get_db_connection()
    categories = db.execute("SELECT DISTINCT category FROM questions").fetchall()
    db.close()
    return [cat['category'] for cat in categories]

def get_questions_by_category(category, limit=5):
    """Pulls random questions for a specific subject"""
    db = get_db_connection()
    all_q = db.execute("SELECT * FROM questions WHERE category=?", (category,)).fetchall()
    db.close()
    
    if not all_q:
        return []
    
    return random.sample(all_q, min(limit, len(all_q)))