import sqlite3

db = sqlite3.connect("database.db")
cur = db.cursor()

email = "edphoenix58@gmail.com"

# check if user exists
cur.execute("SELECT * FROM users WHERE email=?", (email,))
user = cur.fetchone()

if user:
    cur.execute("UPDATE users SET role='admin' WHERE email=?", (email,))
    db.commit()
    print("✅ Admin assigned successfully")
else:
    print("❌ User not found. Please register first.")

db.close()