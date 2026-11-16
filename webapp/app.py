from flask import Flask, render_template, request, redirect, send_file
import sqlite3
import csv
import io
from datetime import datetime
import math
import os
from pathlib import Path

app = Flask(__name__)
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")

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


def validate_ride(kuupaev, marsruut, kilomeetrid_input):
    errors = []
    kilomeetrid = None

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
    except (TypeError, ValueError):
        errors.append("Kilomeetrid peavad olema arv.")
    else:
        if not math.isfinite(kilomeetrid):
            errors.append("Kilomeetrid peavad olema lõplik arv.")
        elif kilomeetrid < 0:
            errors.append("Kilomeetrid ei tohi olla negatiivsed.")

    return errors, kilomeetrid


def ride_duplicate_key(kuupaev, marsruut, kilomeetrid):
    kuupaev = str(kuupaev or "").strip()
    marsruut = str(marsruut or "").strip()
    if not kuupaev or not marsruut or kilomeetrid is None:
        return None

    try:
        kuupaev = datetime.strptime(kuupaev, "%Y-%m-%d").date().isoformat()
        kilomeetrid = float(kilomeetrid)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(kilomeetrid):
        return None
    return kuupaev, marsruut, kilomeetrid


def render_import_result(message, status=200):
    return render_template("index.html", import_message=message), status


def open_readonly_database(database_path):
    database_uri = Path(database_path).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(database_uri, uri=True)


def verify_database_backup(backup_path):
    connection = None
    try:
        connection = open_readonly_database(backup_path)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise ValueError("Varukoopia tervikluse kontroll ebaõnnestus.")

        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(soidud)")
        }
        required_columns = {"id", "kuupaev", "marsruut", "kilomeetrid"}
        if not required_columns.issubset(columns):
            raise ValueError("Varukoopias puudub nõutud soidud tabel või selle veerud.")

        ride_count = connection.execute("SELECT COUNT(*) FROM soidud").fetchone()[0]
        connection.execute(
            "SELECT id, kuupaev, marsruut, kilomeetrid FROM soidud LIMIT 1"
        ).fetchone()
        return ride_count
    except sqlite3.Error as error:
        raise ValueError("Varukoopia ei ole loetav SQLite andmebaas.") from error
    finally:
        if connection is not None:
            connection.close()


def create_database_backup():
    if not os.path.isfile(DB_NAME):
        raise FileNotFoundError("Lähteandmebaasi ei leitud.")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    suffix = 0
    while True:
        suffix_text = f"_{suffix}" if suffix else ""
        backup_path = os.path.join(BACKUP_DIR, f"users_{timestamp}{suffix_text}.db")
        try:
            with open(backup_path, "xb"):
                pass
            break
        except FileExistsError:
            suffix += 1

    source = None
    destination = None
    try:
        source = open_readonly_database(DB_NAME)
        destination = sqlite3.connect(backup_path)
        source.backup(destination)
        destination.close()
        destination = None
        source.close()
        source = None
        ride_count = verify_database_backup(backup_path)
        return backup_path, ride_count
    except Exception:
        if destination is not None:
            destination.close()
        if source is not None:
            source.close()
        if os.path.exists(backup_path):
            os.remove(backup_path)
        raise


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
    errors, kilomeetrid = validate_ride(kuupaev, marsruut, kilomeetrid_input)

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


@app.route("/backup", methods=["POST"])
def backup_database():
    try:
        backup_path, ride_count = create_database_backup()
    except (OSError, sqlite3.Error, ValueError) as error:
        message = f"Varundamine ebaõnnestus: {error}"
        return render_template("index.html", backup_message=message), 400

    message = (
        f"Varukoopia loodud ja kontrollitud: {os.path.basename(backup_path)} "
        f"({ride_count} sõitu)."
    )
    return render_template("index.html", backup_message=message)


@app.route("/import", methods=["POST"])
def import_csv():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return render_import_result("Vali importimiseks CSV-fail.", 400)

    try:
        csv_text = uploaded_file.stream.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(csv_text, newline=""), strict=True)
        if not reader.fieldnames:
            return render_import_result("CSV-fail on tühi või päiserida puudub.", 400)

        aliases = {
            "kuupaev": "kuupaev",
            "kuupäev": "kuupaev",
            "marsruut": "marsruut",
            "kilomeetrid": "kilomeetrid",
            "id": "id",
        }
        columns = {}
        for header in reader.fieldnames:
            canonical = aliases.get((header or "").strip().casefold())
            if canonical in columns and canonical != "id":
                return render_import_result("CSV-päises on korduv nõutud veerg.", 400)
            if canonical:
                columns[canonical] = header

        required_columns = {"kuupaev", "marsruut", "kilomeetrid"}
        missing_columns = required_columns - columns.keys()
        if missing_columns:
            return render_import_result(
                "CSV-st puuduvad nõutud veerud: " + ", ".join(sorted(missing_columns)) + ".",
                400
            )

        valid_rides = []
        invalid_rows = []
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                invalid_rows.append(f"Rida {row_number}: veergude arv ei klapi päisega.")
                continue

            kuupaev = (row.get(columns["kuupaev"]) or "").strip()
            marsruut = (row.get(columns["marsruut"]) or "").strip()
            kilomeetrid_input = (row.get(columns["kilomeetrid"]) or "").strip()
            errors, kilomeetrid = validate_ride(kuupaev, marsruut, kilomeetrid_input)
            if errors:
                invalid_rows.append(f"Rida {row_number}: {' '.join(errors)}")
            else:
                valid_rides.append((kuupaev, marsruut, kilomeetrid))
    except (UnicodeDecodeError, csv.Error):
        return render_import_result("CSV-faili ei saanud lugeda. Kontrolli UTF-8 kodeeringut ja CSV vormingut.", 400)

    if not valid_rides and not invalid_rows:
        return render_import_result("CSV-failis ei ole sõiduandmeid.", 400)

    duplicate_count = 0
    imported_rides = []
    if valid_rides:
        conn, cursor = loo_andmebaas()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            existing_rides = cursor.execute(
                "SELECT kuupaev, marsruut, kilomeetrid FROM soidud"
            ).fetchall()
            seen_keys = {
                key
                for row in existing_rides
                if (key := ride_duplicate_key(*row)) is not None
            }

            for ride in valid_rides:
                key = ride_duplicate_key(*ride)
                if key in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(key)
                imported_rides.append(ride)

            cursor.executemany(
                "INSERT INTO soidud (kuupaev, marsruut, kilomeetrid) VALUES (?, ?, ?)",
                imported_rides
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    message = (
        f"Imporditi {len(imported_rides)} sõitu. "
        f"{duplicate_count} duplikaati jäeti vahele. "
        f"{len(invalid_rows)} vigast rida lükati tagasi."
    )
    if invalid_rows:
        shown_errors = " ".join(invalid_rows[:5])
        remaining_count = len(invalid_rows) - 5
        if remaining_count > 0:
            shown_errors += f" Lisaks {remaining_count} vigast rida."
        message += f" {shown_errors}"
    return render_import_result(message, 400 if invalid_rows else 200)


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
        writer.writerow(["kuupaev", "marsruut", "kilomeetrid"])
        writer.writerows((row[1], row[2], row[3]) for row in rows)

    return send_file(filename, as_attachment=True)
@app.route("/stats/kuud")
def stats_kuud():
    monthly_stats = calculate_monthly_statistics()
    return render_template("stats_kuud.html", monthly_stats=monthly_stats)


def run_app():
    app.run(host="127.0.0.1", debug=False)


if __name__ == "__main__":
    run_app()

