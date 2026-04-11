from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# IMPORT YOUR NEW LOGIC FILE
from quiz_logic import get_all_categories, get_questions_by_category

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE CONNECTION ----------------
def db_conn():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = db_conn()
    db.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""")
    db.execute("""
    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        option1 TEXT,
        option2 TEXT,
        option3 TEXT,
        option4 TEXT,
        answer TEXT,
        category TEXT
    )""")
    db.execute("""
    CREATE TABLE IF NOT EXISTS results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        score INTEGER,
        category TEXT
    )""")
    db.commit()
    db.close()

# ---------------- CACHE CONTROL ----------------
@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    response.cache_control.no_cache = True
    response.cache_control.must_revalidate = True
    return response

# ---------------- MERGE SORT (FOR LEADERBOARD) ----------------
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i][1] > right[j][1]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for('dashboard'))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = "student"
        
        db = db_conn()
        try:
            db.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)", 
                       (name, email, password, role))
            db.commit()
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            return "User with this email already exists!"
        finally:
            db.close()
    return render_template("register.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]
    
    db = db_conn()
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    db.close()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["role"] = user["role"]
        return redirect(url_for('dashboard'))
    
    return "Invalid Login ❌ <a href='/'>Try again</a>"

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for('home'))
    
    # Logic moved to quiz_logic.py
    categories = get_all_categories()
    return render_template("dashboard.html", categories=categories)

@app.route("/quiz")
def quiz():
    if "user_id" not in session:
        return redirect(url_for('home'))

    category = request.args.get('category')
    
    # Logic moved to quiz_logic.py
    selected = get_questions_by_category(category)

    if not selected:
        return "No questions available for this subject! <a href='/dashboard'>Go Back</a>"

    session["q_ids"] = [q["id"] for q in selected]
    session["current_category"] = category 
    
    return render_template("quiz.html", questions=selected, category=category)

@app.route("/submit", methods=["POST"])
def submit():
    if "user_id" not in session:
        return redirect(url_for('home'))

    q_ids = session.get("q_ids")
    if not q_ids:
        return "Submission Error: Session expired."

    db = db_conn()
    placeholders = ','.join(['?'] * len(q_ids))
    questions = db.execute(f"SELECT id, answer, category FROM questions WHERE id IN ({placeholders})", q_ids).fetchall()

    score = 0
    performance = {} 

    for q in questions:
        cat = q["category"] or "General"
        if cat not in performance:
            performance[cat] = {"correct": 0, "total": 0}
        
        performance[cat]["total"] += 1
        user_answer = request.form.get(str(q["id"]))
        
        if user_answer == q["answer"]:
            score += 1
            performance[cat]["correct"] += 1

    recs = []
    for cat, stats in performance.items():
        acc = (stats["correct"] / stats["total"]) * 100
        if acc < 50:
            recs.append(f"🔴 Work harder on {cat}! Try reviewing the basics.")
        elif acc < 80:
            recs.append(f"🟠 You're doing okay in {cat}, but there's room for improvement.")
        else:
            recs.append(f"🟢 Excellent performance in {cat}!")

    db.execute("INSERT INTO results(user_id, score, category) VALUES(?,?,?)", 
               (session["user_id"], score, session.get("current_category", "General")))
    db.commit()
    db.close()

    session.pop("q_ids", None)
    return render_template("result.html", score=score, recommendations=recs)

@app.route("/leaderboard")
def leaderboard():
    db = db_conn()
    data = db.execute("""
        SELECT users.name, MAX(results.score) as top_score
        FROM results 
        JOIN users ON users.id = results.user_id
        GROUP BY users.id
    """).fetchall()
    db.close()
    
    data_list = [(row[0], row[1]) for row in data]
    sorted_data = merge_sort(data_list)
    
    return render_template("leaderboard.html", data=sorted_data[:10])

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("role") != "admin":
        return "Access Denied ❌"
    
    db = db_conn()
    if request.method == "POST":
        db.execute("""
            INSERT INTO questions(question, option1, option2, option3, option4, answer, category) 
            VALUES(?,?,?,?,?,?,?)
        """, (request.form["q"], request.form["o1"], request.form["o2"], 
              request.form["o3"], request.form["o4"], request.form["ans"],
              request.form["category"]))
        db.commit()
    
    questions = db.execute("SELECT * FROM questions").fetchall()
    db.close()
    return render_template("admin.html", questions=questions)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
