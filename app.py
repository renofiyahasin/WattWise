from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "wattwise.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "wattwise-demo-secret-key"

def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        name TEXT DEFAULT 'WattWise User',
        email TEXT DEFAULT '',
        tariff REAL DEFAULT 8.0,
        monthly_goal REAL DEFAULT 500.0
    );

    CREATE TABLE IF NOT EXISTS appliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Other',
        wattage REAL NOT NULL,
        hours_per_day REAL NOT NULL,
        days_per_month INTEGER NOT NULL DEFAULT 30,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS usage_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appliance_name TEXT NOT NULL,
        wattage REAL NOT NULL,
        hours_per_day REAL NOT NULL,
        days_per_month INTEGER NOT NULL,
        kwh REAL NOT NULL,
        cost REAL NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM profile").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO profile (id, name, tariff, monthly_goal) VALUES (1, ?, ?, ?)",
            ("WattWise User", 8.0, 500.0)
        )
    conn.commit()
    conn.close()

def profile():
    conn = get_db()
    row = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
    conn.close()
    return row

def calc(wattage, hours, days, tariff):
    kwh = (float(wattage) * float(hours) * int(days)) / 1000
    cost = kwh * float(tariff)
    return round(kwh, 2), round(cost, 2)

@app.route("/")
def home():
    return render_template("index.html", profile=profile())

@app.route("/dashboard")
def dashboard():
    conn = get_db()
    appliances = conn.execute("SELECT * FROM appliances ORDER BY id DESC").fetchall()
    p = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
    conn.close()
    total_kwh = sum(calc(a["wattage"], a["hours_per_day"], a["days_per_month"], p["tariff"])[0] for a in appliances)
    total_cost = round(total_kwh * p["tariff"], 2)
    return render_template("dashboard.html", appliances=appliances, profile=p,
                           total_kwh=round(total_kwh, 2), total_cost=total_cost)

@app.route("/appliances")
def appliances():
    conn = get_db()
    rows = conn.execute("SELECT * FROM appliances ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("appliances.html", appliances=rows)

@app.route("/appliance/add", methods=["GET", "POST"])
def add_appliance():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "Other")
        wattage = float(request.form.get("wattage", 0))
        hours = float(request.form.get("hours_per_day", 0))
        days = int(request.form.get("days_per_month", 30))
        if not name or wattage <= 0 or hours < 0 or hours > 24 or days < 1 or days > 31:
            flash("Please enter valid appliance details.", "error")
            return redirect(url_for("add_appliance"))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        conn.execute("""INSERT INTO appliances
            (name, category, wattage, hours_per_day, days_per_month, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (name, category, wattage, hours, days, now))
        tariff = profile()["tariff"]
        kwh, cost = calc(wattage, hours, days, tariff)
        conn.execute("""INSERT INTO usage_history
            (appliance_name, wattage, hours_per_day, days_per_month, kwh, cost, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, wattage, hours, days, kwh, cost, now))
        conn.commit()
        conn.close()
        flash(f"{name} added successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("add_appliance.html")

@app.route("/appliance/delete/<int:appliance_id>", methods=["POST"])
def delete_appliance(appliance_id):
    conn = get_db()
    conn.execute("DELETE FROM appliances WHERE id=?", (appliance_id,))
    conn.commit()
    conn.close()
    flash("Appliance removed.", "success")
    return redirect(request.referrer or url_for("appliances"))

@app.route("/analysis")
def analysis():
    conn = get_db()
    rows = conn.execute("SELECT * FROM appliances ORDER BY id").fetchall()
    p = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
    history = conn.execute("""SELECT substr(created_at,1,7) month,
        ROUND(SUM(kwh),2) kwh, ROUND(SUM(cost),2) cost
        FROM usage_history GROUP BY substr(created_at,1,7)
        ORDER BY month DESC LIMIT 6""").fetchall()
    conn.close()
    data = []
    for a in rows:
        kwh, cost = calc(a["wattage"], a["hours_per_day"], a["days_per_month"], p["tariff"])
        data.append({"name": a["name"], "category": a["category"], "kwh": kwh, "cost": cost})
    data.sort(key=lambda x: x["kwh"], reverse=True)
    return render_template("analysis.html", data=data, history=history, profile=p)

@app.route("/suggestions")
def suggestions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM appliances").fetchall()
    p = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
    conn.close()
    suggestions = []
    for a in rows:
        kwh, cost = calc(a["wattage"], a["hours_per_day"], a["days_per_month"], p["tariff"])
        if a["hours_per_day"] >= 6:
            saved_kwh, saved_cost = calc(a["wattage"], 2, a["days_per_month"], p["tariff"])
            suggestions.append({
                "title": f"Reduce {a['name']} usage",
                "text": f"Current usage is {a['hours_per_day']:.1f} hours/day. Reducing it by 2 hours/day could save about ₹{max(0, cost-saved_cost):.0f}/month.",
                "saving": round(max(0, cost-saved_cost), 2)
            })
        if a["wattage"] >= 100:
            suggestions.append({
                "title": f"Check efficiency of {a['name']}",
                "text": f"This appliance is rated at {a['wattage']:.0f} W. Compare energy-efficient alternatives and avoid unnecessary standby time.",
                "saving": 0
            })
    if not suggestions:
        suggestions.append({
            "title": "Start tracking your appliances",
            "text": "Add your frequently used appliances to get personalized saving suggestions.",
            "saving": 0
        })
    return render_template("suggestions.html", suggestions=suggestions)

@app.route("/simulator", methods=["GET", "POST"])
def simulator():
    p = profile()
    result = None
    if request.method == "POST":
        wattage = float(request.form.get("wattage", 0))
        current = float(request.form.get("current_hours", 0))
        new = float(request.form.get("new_hours", 0))
        days = int(request.form.get("days", 30))
        if wattage > 0 and current >= 0 and new >= 0 and days > 0:
            old_kwh, old_cost = calc(wattage, current, days, p["tariff"])
            new_kwh, new_cost = calc(wattage, new, days, p["tariff"])
            result = {
                "old_kwh": old_kwh, "new_kwh": new_kwh,
                "saved_kwh": round(max(0, old_kwh-new_kwh), 2),
                "old_cost": old_cost, "new_cost": new_cost,
                "saved_cost": round(max(0, old_cost-new_cost), 2),
                "reduction": round(max(0, (current-new)/current*100), 1) if current else 0
            }
    return render_template("simulator.html", result=result, profile=p)

@app.route("/goal", methods=["GET", "POST"])
def goal():
    p = profile()
    if request.method == "POST":
        goal_value = float(request.form.get("monthly_goal", 0))
        conn = get_db()
        conn.execute("UPDATE profile SET monthly_goal=? WHERE id=1", (max(0, goal_value),))
        conn.commit()
        conn.close()
        flash("Monthly saving goal updated.", "success")
        return redirect(url_for("goal"))
    conn = get_db()
    total = conn.execute("SELECT COALESCE(SUM(cost),0) FROM usage_history").fetchone()[0]
    conn.close()
    progress = min(100, (float(total) / p["monthly_goal"] * 100)) if p["monthly_goal"] else 0
    return render_template("goal.html", profile=profile(), total=round(total,2), progress=round(progress,1))

@app.route("/history")
def history():
    conn = get_db()
    rows = conn.execute("SELECT * FROM usage_history ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("history.html", history=rows)

@app.route("/profile", methods=["GET", "POST"])
def profile_page():
    if request.method == "POST":
        name = request.form.get("name", "WattWise User").strip()
        email = request.form.get("email", "").strip()
        tariff = float(request.form.get("tariff", 8))
        goal_value = float(request.form.get("monthly_goal", 500))
        conn = get_db()
        conn.execute("UPDATE profile SET name=?, email=?, tariff=?, monthly_goal=? WHERE id=1",
                     (name, email, max(0, tariff), max(0, goal_value)))
        conn.commit()
        conn.close()
        flash("Profile saved.", "success")
        return redirect(url_for("profile_page"))
    return render_template("profile.html", profile=profile())

@app.route("/api/summary")
def api_summary():
    conn = get_db()
    rows = conn.execute("SELECT * FROM appliances").fetchall()
    p = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
    conn.close()
    values = [calc(a["wattage"], a["hours_per_day"], a["days_per_month"], p["tariff"]) for a in rows]
    return jsonify({
        "appliances": len(rows),
        "kwh": round(sum(x[0] for x in values), 2),
        "cost": round(sum(x[1] for x in values), 2)
    })

init_db()

if __name__ == "__main__":
    app.run(debug=True)
