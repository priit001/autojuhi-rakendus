from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import csv
from datetime import datetime
import math
import os

app = Flask(__name__)
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

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
    conn, cursor = loo_andmebaas()
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(kilomeetrid), 0) FROM soidud")
    total_rides, total_km = cursor.fetchone()
    conn.close()

    return {
        "total_rides": total_rides,
        "total_km": round(total_km, 2)
    }


def calculate_monthly_statistics():
    conn, cursor = loo_andmebaas()
    cursor.execute("""
        SELECT
            strftime('%Y-%m', kuupaev) AS kuu,
            COUNT(*),
            COALESCE(SUM(kilomeetrid), 0)
        FROM soidud
        WHERE strftime('%Y-%m', kuupaev) IS NOT NULL
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

@app.route("/lisa", methods=["GET", "POST"])
def lisa_soit():
    if request.method == "GET":
        return render_template("add_ride.html")

    kuupaev = request.form.get("kuupaev", "").strip()
    marsruut = request.form.get("marsruut", "").strip()
    kilomeetrid_input = request.form.get("kilomeetrid", "").strip()
    errors = []

    if not kuupaev:
        errors.append("Kuupäev on kohustuslik.")
    else:
        try:
            datetime.strptime(kuupaev, "%Y-%m-%d")
        except ValueError:
            errors.append("Sisesta korrektne kuupäev.")

    if not marsruut:
        errors.append("Marsruut ei tohi olla tühi.")

    try:
        kilomeetrid = float(kilomeetrid_input)
    except ValueError:
        errors.append("Kilomeetrid peavad olema arv.")
    else:
        if not math.isfinite(kilomeetrid):
            errors.append("Kilomeetrid peavad olema lõplik arv.")
        elif kilomeetrid < 0:
            errors.append("Kilomeetrid ei tohi olla negatiivsed.")

    if errors:
        return render_template(
            "add_ride.html",
            error=" ".join(errors),
            kuupaev=kuupaev,
            marsruut=marsruut,
            kilomeetrid=kilomeetrid_input
        ), 400

    conn, cursor = loo_andmebaas()
    cursor.execute("INSERT INTO soidud (kuupaev, marsruut, kilomeetrid) VALUES (?, ?, ?)",
                   (kuupaev, marsruut, kilomeetrid))
    conn.commit()
    conn.close()
    return redirect("/soidud")

@app.route("/soidud")
def soidud():
    conn, cursor = loo_andmebaas()
    cursor.execute("SELECT id, kuupaev, marsruut, kilomeetrid FROM soidud ORDER BY id DESC")
    rides = cursor.fetchall()
    conn.close()
    return render_template("rides.html", rides=rides)

@app.route("/kustuta/<int:id>", methods=["POST"])
def kustuta_soit(id):
    conn, cursor = loo_andmebaas()
    cursor.execute("DELETE FROM soidud WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/soidud")

@app.route("/stats")
@app.route("/statistika")
def stats():
    stats = calculate_statistics_from_db()
    return render_template(
        "stats.html",
        total_rides=stats["total_rides"],
        total_km=stats["total_km"]
    )


@app.route("/export")
def export_csv():
    conn, cursor = loo_andmebaas()
    cursor.execute("SELECT id, kuupaev, marsruut, kilomeetrid FROM soidud")
    rows = cursor.fetchall()
    conn.close()

    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
    export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
    os.makedirs(export_dir, exist_ok=True)
    filename = os.path.join(export_dir, f"soidud_{timestamp}.csv")

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

