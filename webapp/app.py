from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import csv
from datetime import datetime
import os

app = Flask(__name__)
DB_NAME = "users.db"

def loo_andmebaas():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS soidud (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kuupaev TEXT,
            marsruut TEXT,
            kilomeetrid REAL
        )
    """)
    conn.commit()
    return conn, cursor

def calculate_statistics_from_db():
    print("STAT FUNKTSIOON KÄIVITUS")

    conn, cursor = loo_andmebaas()
    cursor.execute("SELECT kilomeetrid FROM soidud")
    rows = cursor.fetchall()
    conn.close()

    km_list = [row[0] for row in rows]
    HIND_KM = 0.5

    if not km_list:
        return {
            "total_km": 0,
            "total_income": 0,
            "avg_price": 0
        }

    total_km = sum(km_list)
    total_income = total_km * HIND_KM

    return {
        "total_km": round(total_km, 2),
        "total_income": round(total_income, 2),
        "avg_price": round(HIND_KM, 2)
    }


def calculate_monthly_statistics():
    conn, cursor = loo_andmebaas()
    cursor.execute("""
        SELECT 
            substr(kuupaev, 7, 4) || '-' || substr(kuupaev, 4, 2) AS kuu,
            SUM(kilomeetrid)
        FROM soidud
        GROUP BY kuu
        ORDER BY kuu
    """)
    rows = cursor.fetchall()
    conn.close()

    return rows


@app.route("/")
def index():
    conn, cursor = loo_andmebaas()
    cursor.execute("SELECT id, kuupaev, marsruut, kilomeetrid FROM soidud")
    soidud = cursor.fetchall()
    conn.close()
    return render_template("index.html", soidud=soidud)

@app.route("/lisa", methods=["POST"])
def lisa_soit():
    kuupaev = request.form["kuupaev"]
    marsruut = request.form["marsruut"]
    try:
        kilomeetrid = float(request.form["kilomeetrid"])
    except ValueError:
        return "❌ Viga: Kilomeetrid peavad olema arv."

    conn, cursor = loo_andmebaas()
    cursor.execute("INSERT INTO soidud (kuupaev, marsruut, kilomeetrid) VALUES (?, ?, ?)",
                   (kuupaev, marsruut, kilomeetrid))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/kustuta/<int:id>")
def kustuta_soit(id):
    conn, cursor = loo_andmebaas()
    cursor.execute("DELETE FROM soidud WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/stats")
def stats():
    stats = calculate_statistics_from_db()
    return render_template(
        "stats.html",
        total_km=stats["total_km"],
        total_income=stats["total_income"],
        avg_price=stats["avg_price"]
    )


@app.route("/export")
def export_csv():
    conn, cursor = loo_andmebaas()
    cursor.execute("SELECT id, kuupaev, marsruut, kilomeetrid FROM soidud")
    rows = cursor.fetchall()
    conn.close()

    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
    filename = os.path.join("exports", f"soidud_{timestamp}.csv")

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Kuupäev", "Marsruut", "Kilomeetrid"])
        writer.writerows(rows)

    return send_file(filename, as_attachment=True)
@app.route("/stats/kuud")
def stats_kuud():
    monthly_stats = calculate_monthly_statistics()
    return render_template("stats_kuud.html", monthly_stats=monthly_stats)

if __name__ == "__main__":
    app.run(debug=True)

