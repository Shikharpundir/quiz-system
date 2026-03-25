from flask import Flask, render_template, request, redirect, session, make_response
import sqlite3, random
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB ----------------
def db_conn():
    return sqlite3.connect("database.db")

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
        answer TEXT
    )""")

    db.execute("""
    CREATE TABLE IF NOT EXISTS results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        score INTEGER
    )""")

    db.execute("CREATE INDEX IF NOT EXISTS idx_email ON users(email)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_user_result ON results(user_id)")

    db.commit()
    db.close()

# ---------------- CACHE CONTROL ----------------
@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    response.cache_control.no_cache = True
    response.cache_control.must_revalidate = True
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# ---------------- MERGE SORT ----------------
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
    return render_template("login.html")

# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = "student"

        db = db_conn()
        try:
            db.execute(
                "INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                (name, email, password, role)
            )
            db.commit()
        except:
            return "User already exists!"

        return redirect("/")

    return render_template("register.html")

# LOGIN
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    db = db_conn()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cur.fetchone()

    if user and check_password_hash(user[3], password):
        session["user"] = user[0]
        session["role"] = user[4]
        return redirect("/dashboard")

    return "Invalid Login ❌"

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")

# QUIZ

@app.route("/quiz")
def quiz():
    if "user" not in session:
        return redirect("/")

    # 🔥 ALWAYS RESET OLD QUIZ SESSION
    session.pop("q_ids", None)

    db = db_conn()
    questions = db.execute("SELECT * FROM questions").fetchall()

    if not questions:
        return "No questions available!"

    questions = random.sample(questions, min(5, len(questions)))
    session["q_ids"] = [q[0] for q in questions]

    return render_template("quiz.html", questions=questions)

# SUBMIT
@app.route("/submit", methods=["POST"])
def submit():
    if "user" not in session:
        return redirect("/")

    db = db_conn()

    q_ids = session.get("q_ids", [])
    if not q_ids:
        return redirect("/quiz")

    query = f"SELECT * FROM questions WHERE id IN ({','.join(['?']*len(q_ids))})"
    questions = db.execute(query, q_ids).fetchall()

    answers_map = {str(q[0]): q[6] for q in questions}

    score = 0
    for qid, correct_ans in answers_map.items():
        if request.form.get(qid) == correct_ans:
            score += 1

    db.execute(
        "INSERT INTO results(user_id,score) VALUES(?,?)",
        (session["user"], score)
    )
    db.commit()

    # 🔥 IMPORTANT FIX
    session.pop("q_ids", None)

    return render_template("result.html", score=score)

# LEADERBOARD
@app.route("/leaderboard")
def leaderboard():
    db = db_conn()

    data = db.execute("""
    SELECT users.name, MAX(results.score)
    FROM results JOIN users
    ON users.id = results.user_id
    GROUP BY users.id
    """).fetchall()

    sorted_data = merge_sort(data)
    top_10 = sorted_data[:10]

    return render_template("leaderboard.html", data=top_10)

# ADMIN
@app.route("/admin", methods=["GET","POST"])
def admin():
    if session.get("role") != "admin":
        return "Access Denied ❌"

    db = db_conn()

    if request.method == "POST":
        db.execute("""
        INSERT INTO questions(question,option1,option2,option3,option4,answer)
        VALUES(?,?,?,?,?,?)
        """, (
            request.form["q"],
            request.form["o1"],
            request.form["o2"],
            request.form["o3"],
            request.form["o4"],
            request.form["ans"]
        ))
        db.commit()

    questions = db.execute("SELECT * FROM questions").fetchall()
    return render_template("admin.html", questions=questions)

# DELETE QUESTION
@app.route("/delete_question/<int:id>")
def delete_question(id):
    if session.get("role") != "admin":
        return "Access Denied ❌"

    db = db_conn()
    db.execute("DELETE FROM questions WHERE id=?", (id,))
    db.commit()
    return redirect("/admin")

# DELETE ALL QUESTIONS
@app.route("/delete_quiz")
def delete_quiz():
    if session.get("role") != "admin":
        return "Access Denied ❌"

    db = db_conn()
    db.execute("DELETE FROM questions")
    db.commit()
    return redirect("/admin")

# RESET RESULTS
@app.route("/reset_results")
def reset_results():
    if session.get("role") != "admin":
        return "Access Denied ❌"

    db = db_conn()
    db.execute("DELETE FROM results")
    db.commit()
    return redirect("/admin")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
