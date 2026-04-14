from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3, random
import re
from math import isfinite
from datetime import datetime

app = Flask(__name__)
app.secret_key = "banking_secret_key"
DB = "banking.db"

# ─── DB SETUP ────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL CHECK (username <> '' AND username NOT GLOB '*[^A-Za-z_]*'),
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            full_name TEXT NOT NULL CHECK (full_name <> '' AND full_name NOT GLOB '*[^A-Za-z ]*'),
            email TEXT,
            phone TEXT CHECK (phone IS NULL OR phone = '' OR phone GLOB '[0-9]*'),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            account_number TEXT UNIQUE NOT NULL,
            balance REAL NOT NULL DEFAULT 0.00 CHECK (balance >= 0),
            created_at TEXT DEFAULT (DATETIME('now')),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            type TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            related_account_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT (DATETIME('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)

    # Default admin
    c.execute("SELECT id FROM users WHERE username = 'admin'")
    if not c.fetchone():
        hashed = generate_password_hash("admin123")
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')", ("admin", hashed))

    conn.commit()
    conn.close()

# ─── HELPERS ─────────────────────────────────────────────────

def is_admin():
    return session.get("role") == "admin"

def is_customer():
    return session.get("role") == "customer"

def generate_account_number():
    return "ACC" + str(random.randint(1000000000, 9999999999))

def is_valid_username(value):
    return bool(re.fullmatch(r"[A-Za-z_]+", str(value or "").strip()))

def is_valid_full_name(value):
    return bool(re.fullmatch(r"[A-Za-z ]+", str(value or "").strip()))

def is_valid_phone(value):
    phone = str(value or "").strip()
    if phone == "":
        return True
    return bool(re.fullmatch(r"[0-9]{10}", phone))

def parse_positive_amount(raw_amount):
    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return None

    if not isfinite(amount) or amount <= 0:
        return None

    return amount

@app.template_filter("format_datetime")
def format_dt(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value).replace("T", " ")).strftime("%d %b %Y, %I:%M %p")
    except:
        return value

# ─── AUTH ────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("admin_dashboard") if user["role"] == "admin" else url_for("customer_dashboard"))
        else:
            flash("Invalid username or password", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── ADMIN ROUTES ────────────────────────────────────────────

@app.route("/admin")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("login"))

    conn = get_db()
    customers = conn.execute("""
        SELECT c.id, c.full_name, c.email, c.phone,
               a.account_number, a.balance, a.id as account_id
        FROM customers c
        LEFT JOIN accounts a ON c.id = a.customer_id
    """).fetchall()
    conn.close()

    return render_template("admin.html", customers=customers)

@app.route("/admin/add_customer", methods=["POST"])
def add_customer():
    if not is_admin():
        return redirect(url_for("login"))

    full_name = request.form["full_name"].strip()
    email     = request.form["email"].strip()
    phone     = request.form["phone"].strip()
    username  = request.form["username"].strip()
    password  = request.form["password"]

    if not is_valid_username(username):
        flash("Username must contain only letters or underscore", "error")
        return redirect(url_for("admin_dashboard"))

    if not is_valid_full_name(full_name):
        flash("Full name must contain only letters and spaces", "error")
        return redirect(url_for("admin_dashboard"))

    if not is_valid_phone(phone):
        flash("Phone must contain 10 digits", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()

    if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
        flash("Username already exists", "error")
        conn.close()
        return redirect(url_for("admin_dashboard"))

    hashed  = generate_password_hash(password)
    user_id = conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'customer')", (username, hashed)).lastrowid
    customer_id = conn.execute("INSERT INTO customers (user_id, full_name, email, phone) VALUES (?, ?, ?, ?)", (user_id, full_name, email, phone)).lastrowid
    acc_number  = generate_account_number()
    conn.execute("INSERT INTO accounts (customer_id, account_number, balance) VALUES (?, ?, 0.00)", (customer_id, acc_number))

    conn.commit()
    conn.close()

    flash(f"Customer created! Account: {acc_number}", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_customer/<int:customer_id>", methods=["POST"])
def delete_customer(customer_id):
    if not is_admin():
        return redirect(url_for("login"))

    conn = get_db()
    accounts = conn.execute("SELECT id FROM accounts WHERE customer_id = ?", (customer_id,)).fetchall()
    for acc in accounts:
        conn.execute("DELETE FROM transactions WHERE account_id = ?", (acc["id"],))
    conn.execute("DELETE FROM accounts WHERE customer_id = ?", (customer_id,))
    row = conn.execute("SELECT user_id FROM customers WHERE id = ?", (customer_id,)).fetchone()
    conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
    if row:
        conn.execute("DELETE FROM users WHERE id = ?", (row["user_id"],))

    conn.commit()
    conn.close()

    flash("Customer deleted", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/transactions")
def admin_transactions():
    if not is_admin():
        return redirect(url_for("login"))

    conn = get_db()
    transactions = conn.execute("""
        SELECT t.id, t.type, t.amount, t.created_at,
               a.account_number, c.full_name
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        JOIN customers c ON a.customer_id = c.id
        ORDER BY t.created_at DESC
    """).fetchall()
    conn.close()

    return render_template("admin_transactions.html", transactions=transactions)

# ─── CUSTOMER ROUTES ─────────────────────────────────────────

@app.route("/customer")
def customer_dashboard():
    if not is_customer():
        return redirect(url_for("login"))

    conn = get_db()
    account = conn.execute("""
        SELECT c.full_name, c.email, c.phone,
               a.account_number, a.balance, a.id as account_id
        FROM customers c
        JOIN accounts a ON c.id = a.customer_id
        WHERE c.user_id = ?
    """, (session["user_id"],)).fetchone()

    transactions = conn.execute("""
        SELECT type, amount, created_at
        FROM transactions
        WHERE account_id = ?
        ORDER BY created_at DESC LIMIT 10
    """, (account["account_id"],)).fetchall()

    conn.close()
    return render_template("customer.html", account=account, transactions=transactions)

@app.route("/customer/deposit", methods=["POST"])
def deposit():
    if not is_customer():
        return redirect(url_for("login"))

    amount = parse_positive_amount(request.form.get("amount"))
    if amount is None:
        flash("Amount must be positive", "error")
        return redirect(url_for("customer_dashboard"))

    conn = get_db()
    acc = conn.execute("""
        SELECT a.id FROM accounts a
        JOIN customers c ON a.customer_id = c.id
        WHERE c.user_id = ?
    """, (session["user_id"],)).fetchone()

    conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, acc["id"]))
    conn.execute("INSERT INTO transactions (account_id, type, amount) VALUES (?, 'deposit', ?)", (acc["id"], amount))
    conn.commit()
    conn.close()

    flash(f"₹{amount:.2f} deposited successfully", "success")
    return redirect(url_for("customer_dashboard"))

@app.route("/customer/withdraw", methods=["POST"])
def withdraw():
    if not is_customer():
        return redirect(url_for("login"))

    amount = parse_positive_amount(request.form.get("amount"))
    if amount is None:
        flash("Invalid amount", "error")
        return redirect(url_for("customer_dashboard"))

    conn = get_db()
    acc = conn.execute("""
        SELECT a.id, a.balance FROM accounts a
        JOIN customers c ON a.customer_id = c.id
        WHERE c.user_id = ?
    """, (session["user_id"],)).fetchone()

    if amount <= 0 or amount > acc["balance"]:
        flash("Invalid amount or insufficient balance", "error")
        conn.close()
        return redirect(url_for("customer_dashboard"))

    conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, acc["id"]))
    conn.execute("INSERT INTO transactions (account_id, type, amount) VALUES (?, 'withdraw', ?)", (acc["id"], amount))
    conn.commit()
    conn.close()

    flash(f"₹{amount:.2f} withdrawn successfully", "success")
    return redirect(url_for("customer_dashboard"))

@app.route("/customer/transfer", methods=["POST"])
def transfer():
    if not is_customer():
        return redirect(url_for("login"))

    to_account_number = request.form["to_account"].strip()
    amount = parse_positive_amount(request.form.get("amount"))

    if amount is None:
        flash("Invalid amount", "error")
        return redirect(url_for("customer_dashboard"))

    conn = get_db()
    from_acc = conn.execute("""
        SELECT a.id, a.balance, a.account_number FROM accounts a
        JOIN customers c ON a.customer_id = c.id
        WHERE c.user_id = ?
    """, (session["user_id"],)).fetchone()

    to_acc = conn.execute("SELECT id FROM accounts WHERE account_number = ?", (to_account_number,)).fetchone()

    if not to_acc:
        flash("Recipient account not found", "error")
        conn.close()
        return redirect(url_for("customer_dashboard"))

    if to_account_number == from_acc["account_number"]:
        flash("Cannot transfer to your own account", "error")
        conn.close()
        return redirect(url_for("customer_dashboard"))

    if amount <= 0 or amount > from_acc["balance"]:
        flash("Invalid amount or insufficient balance", "error")
        conn.close()
        return redirect(url_for("customer_dashboard"))

    conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_acc["id"]))
    conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_acc["id"]))
    conn.execute("INSERT INTO transactions (account_id, type, amount, related_account_id) VALUES (?, 'transfer', ?, ?)", (from_acc["id"], amount, to_acc["id"]))
    conn.commit()
    conn.close()

    flash(f"₹{amount:.2f} transferred to {to_account_number}", "success")
    return redirect(url_for("customer_dashboard"))

# ─── RUN ─────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
