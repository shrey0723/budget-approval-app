"""
Internal Expense / Budget Approval Dashboard - Backend
--------------------------------------------------------
A small REST API demonstrating:
- CRUD endpoints
- Role-based approval workflow (Employee submits, Manager approves/rejects)
- Data aggregation endpoint (spend by department / category) for dashboard charts

Run:
    pip install -r requirements.txt
    python app.py

Server runs on http://localhost:5000
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")

app = Flask(__name__)
CORS(app)  # allow the React frontend (different port) to call this API


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            department TEXT NOT NULL,
            category TEXT NOT NULL,
            justification TEXT,
            status TEXT NOT NULL DEFAULT 'Pending',
            submitted_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()

    # Seed with sample data if the table is empty (nice for demo/screenshots)
    cur.execute("SELECT COUNT(*) FROM expenses")
    if cur.fetchone()[0] == 0:
        sample = [
            ("New laptops for design team", 4200.0, "Design", "Equipment", "Refresh 5 aging laptops", "Approved", "aditi.rao", "2026-06-02T10:00:00"),
            ("Team offsite venue booking", 1800.0, "Engineering", "Travel", "Quarterly planning offsite", "Pending", "raj.mehta", "2026-06-10T09:30:00"),
            ("Ad campaign - Q3 launch", 9500.0, "Marketing", "Advertising", "Product launch push", "Pending", "sara.khan", "2026-06-15T14:20:00"),
            ("Cloud infra upgrade", 6200.0, "Engineering", "Software", "Scale staging environment", "Approved", "raj.mehta", "2026-06-18T11:00:00"),
            ("Recruiting event sponsorship", 2500.0, "HR", "Events", "Campus hiring drive", "Rejected", "neha.iyer", "2026-06-20T16:45:00"),
            ("Design software licenses", 1200.0, "Design", "Software", "Figma seats renewal", "Approved", "aditi.rao", "2026-06-22T08:15:00"),
        ]
        cur.executemany("""
            INSERT INTO expenses (title, amount, department, category, justification, status, submitted_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample)
        conn.commit()
    conn.close()


def row_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "amount": row["amount"],
        "department": row["department"],
        "category": row["category"],
        "justification": row["justification"],
        "status": row["status"],
        "submitted_by": row["submitted_by"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/expenses", methods=["GET"])
def list_expenses():
    """List expenses, with optional filters: department, status, category."""
    department = request.args.get("department")
    status = request.args.get("status")
    category = request.args.get("category")

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    if department:
        query += " AND department = ?"
        params.append(department)
    if status:
        query += " AND status = ?"
        params.append(status)
    if category:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY created_at DESC"

    conn = get_db()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/expenses", methods=["POST"])
def create_expense():
    """Submit a new expense request (Employee action)."""
    data = request.get_json(force=True)
    required = ["title", "amount", "department", "category", "submitted_by"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO expenses (title, amount, department, category, justification, status, submitted_by, created_at)
        VALUES (?, ?, ?, ?, ?, 'Pending', ?, ?)
    """, (
        data["title"],
        float(data["amount"]),
        data["department"],
        data["category"],
        data.get("justification", ""),
        data["submitted_by"],
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"message": "Expense submitted", "id": new_id}), 201


@app.route("/api/expenses/<int:expense_id>/status", methods=["PATCH"])
def update_status(expense_id):
    """Approve or reject an expense (Manager action)."""
    data = request.get_json(force=True)
    new_status = data.get("status")
    if new_status not in ("Approved", "Rejected", "Pending"):
        return jsonify({"error": "status must be Approved, Rejected, or Pending"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE expenses SET status = ? WHERE id = ?", (new_status, expense_id))
    conn.commit()
    affected = cur.rowcount
    conn.close()

    if affected == 0:
        return jsonify({"error": "Expense not found"}), 404
    return jsonify({"message": f"Expense {expense_id} marked {new_status}"})


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    if affected == 0:
        return jsonify({"error": "Expense not found"}), 404
    return jsonify({"message": "Deleted"})


@app.route("/api/aggregate", methods=["GET"])
def aggregate():
    """
    Aggregation endpoint powering the dashboard chart:
    total spend by department, and by category, for Approved expenses.
    This is the 'data pipeline / aggregation' evidence for the resume.
    """
    conn = get_db()

    by_department = conn.execute("""
        SELECT department, ROUND(SUM(amount), 2) AS total
        FROM expenses
        WHERE status = 'Approved'
        GROUP BY department
        ORDER BY total DESC
    """).fetchall()

    by_category = conn.execute("""
        SELECT category, ROUND(SUM(amount), 2) AS total
        FROM expenses
        WHERE status = 'Approved'
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    by_status = conn.execute("""
        SELECT status, COUNT(*) AS count, ROUND(SUM(amount), 2) AS total
        FROM expenses
        GROUP BY status
    """).fetchall()

    conn.close()

    return jsonify({
        "by_department": [dict(r) for r in by_department],
        "by_category": [dict(r) for r in by_category],
        "by_status": [dict(r) for r in by_status],
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
