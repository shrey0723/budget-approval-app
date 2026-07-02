from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)
CORS(app)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, sample)
        conn.commit()
    cur.close()
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
    department = request.args.get("department")
    status = request.args.get("status")
    category = request.args.get("category")

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []
    if department:
        query += " AND department = %s"
        params.append(department)
    if status:
        query += " AND status = %s"
        params.append(status)
    if category:
        query += " AND category = %s"
        params.append(category)
    query += " ORDER BY created_at DESC"

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/expenses", methods=["POST"])
def create_expense():
    data = request.get_json(force=True)
    required = ["title", "amount", "department", "category", "submitted_by"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO expenses (title, amount, department, category, justification, status, submitted_by, created_at)
        VALUES (%s, %s, %s, %s, %s, 'Pending', %s, %s)
        RETURNING id
    """, (
        data["title"],
        float(data["amount"]),
        data["department"],
        data["category"],
        data.get("justification", ""),
        data["submitted_by"],
        datetime.utcnow().isoformat(),
    ))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Expense submitted", "id": new_id}), 201


@app.route("/api/expenses/<int:expense_id>/status", methods=["PATCH"])
def update_status(expense_id):
    data = request.get_json(force=True)
    new_status = data.get("status")
    if new_status not in ("Approved", "Rejected", "Pending"):
        return jsonify({"error": "status must be Approved, Rejected, or Pending"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE expenses SET status = %s WHERE id = %s", (new_status, expense_id))
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    if affected == 0:
        return jsonify({"error": "Expense not found"}), 404
    return jsonify({"message": f"Expense {expense_id} marked {new_status}"})


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    affected = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    if affected == 0:
        return jsonify({"error": "Expense not found"}), 404
    return jsonify({"message": "Deleted"})


@app.route("/api/aggregate", methods=["GET"])
def aggregate():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT department, ROUND(CAST(SUM(amount) AS numeric), 2) AS total
        FROM expenses WHERE status = 'Approved'
        GROUP BY department ORDER BY total DESC
    """)
    by_department = cur.fetchall()

    cur.execute("""
        SELECT category, ROUND(CAST(SUM(amount) AS numeric), 2) AS total
        FROM expenses WHERE status = 'Approved'
        GROUP BY category ORDER BY total DESC
    """)
    by_category = cur.fetchall()

    cur.execute("""
        SELECT status, COUNT(*) AS count, ROUND(CAST(SUM(amount) AS numeric), 2) AS total
        FROM expenses GROUP BY status
    """)
    by_status = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "by_department": [dict(r) for r in by_department],
        "by_category": [dict(r) for r in by_category],
        "by_status": [dict(r) for r in by_status],
    })


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)