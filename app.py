from flask import Flask, render_template, request, redirect, session
import sqlite3, random

app = Flask(__name__)
app.secret_key = "secret123"

def db_conn():
    return sqlite3.connect("database.db")

# INIT DB
def init_db():
    db = db_conn()

    db.execute("""
    CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
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

    db.commit()
    db.close()

# HOME
@app.route("/")
def home():
    return render_template("login.html")

# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"]
        email=request.form["email"]
        password=request.form["password"]

        role = "student"   # default role

        db=db_conn()
        db.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                   (name,email,password,role))
        db.commit()

        return redirect("/")

    return render_template("register.html")

# LOGIN
@app.route("/login", methods=["POST"])
def login():
    email=request.form["email"]
    password=request.form["password"]

    db=db_conn()
    cur=db.cursor()
    cur.execute("SELECT * FROM users WHERE email=? AND password=?",(email,password))
    user=cur.fetchone()

    if user:
        session["user"]=user[0]
        session["role"]=user[4]   # store role
        return redirect("/dashboard")

    return "Invalid Login"

# DASHBOARD
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

# QUIZ
@app.route("/quiz")
def quiz():
    db=db_conn()
    questions=db.execute("SELECT * FROM questions").fetchall()

    questions=random.sample(questions, min(5,len(questions)))

    return render_template("quiz.html",questions=questions)

# SUBMIT
@app.route("/submit", methods=["POST"])
def submit():
    db=db_conn()
    questions=db.execute("SELECT * FROM questions").fetchall()

    score=0
    for q in questions:
        if request.form.get(str(q[0]))==q[6]:
            score+=1

    db.execute("INSERT INTO results(user_id,score) VALUES(?,?)",(session["user"],score))
    db.commit()

    return render_template("result.html",score=score)

# LEADERBOARD
@app.route("/leaderboard")
def leaderboard():
    db=db_conn()
    data=db.execute("""
    SELECT users.name, MAX(results.score)
    FROM results JOIN users
    ON users.id=results.user_id
    GROUP BY users.name
    ORDER BY MAX(results.score) DESC
    """).fetchall()

    return render_template("leaderboard.html",data=data)

# ADMIN PANEL (PROTECTED)
@app.route("/admin", methods=["GET","POST"])
def admin():

    if session.get("role") != "admin":
        return "Access Denied ❌"

    db = db_conn()

    if request.method=="POST":
        q=request.form["q"]
        o1=request.form["o1"]
        o2=request.form["o2"]
        o3=request.form["o3"]
        o4=request.form["o4"]
        ans=request.form["ans"]

        db.execute("""
        INSERT INTO questions(question,option1,option2,option3,option4,answer)
        VALUES(?,?,?,?,?,?)
        """,(q,o1,o2,o3,o4,ans))
        db.commit()

    questions = db.execute("SELECT * FROM questions").fetchall()

    return render_template("admin.html",questions=questions)

# DELETE SINGLE QUESTION
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

# RESET LEADERBOARD
@app.route("/reset_results")
def reset_results():

    if session.get("role") != "admin":
        return "Access Denied ❌"

    db = db_conn()
    db.execute("DELETE FROM results")
    db.commit()
    return redirect("/admin")

if __name__=="__main__":
    init_db()
    app.run(debug=True)