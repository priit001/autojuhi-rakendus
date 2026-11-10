import sqlite3
import csv
import os

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
    return conn, cursor

def sisesta_soit():
    print("\n📥 Uue sõidu sisestamine")
    kuupaev = input("Sisesta kuupäev (YYYY-MM-DD): ")
    marsruut = input("Sisesta marsruut (nt Tallinn–Tartu): ")
    try:
        kilomeetrid = float(input("Sisesta läbitud kilomeetrid: "))
    except ValueError:
        print("❌ Viga: Kilomeetrid peavad olema arv.")
        return

    try:
        conn, cursor = loo_andmebaas()
        cursor.execute("INSERT INTO soidud (kuupaev, marsruut, kilomeetrid) VALUES (?, ?, ?)",
                       (kuupaev, marsruut, kilomeetrid))
        conn.commit()
        conn.close()
        print("✅ Sõit salvestatud!")
    except Exception as e:
        print(f"❌ Viga andmebaasiga: {e}")

def vaata_soite():
    print("\n📋 Salvestatud sõidud:")
    try:
        conn, cursor = loo_andmebaas()
        cursor.execute("SELECT kuupaev, marsruut, kilomeetrid FROM soidud")
        soidud = cursor.fetchall()

        if not soidud:
            print("ℹ️ Andmebaasis pole veel sõite.")
        else:
            for i, (kuupaev, marsruut, km) in enumerate(soidud, start=1):
                print(f"{i}. {kuupaev} – {marsruut} – {km} km")

        conn.close()
    except Exception as e:
        print(f"❌ Viga andmebaasiga: {e}")

def statistika():
    print("\n📊 Sõidustatistika:")
    try:
        conn, cursor = loo_andmebaas()
        cursor.execute("SELECT COUNT(*), SUM(kilomeetrid), AVG(kilomeetrid) FROM soidud")
        koguarv, summa, keskmine = cursor.fetchone()

        print(f"🔢 Sõitude arv: {koguarv}")
        print(f"📏 Läbitud kilomeetrid kokku: {summa:.2f} km")
        print(f"📊 Keskmine sõidu pikkus: {keskmine:.2f} km")

        conn.close()
    except Exception as e:
        print(f"❌ Viga statistika arvutamisel: {e}")

def kustuta_soit():
    print("\n🗑️ Sõidu kustutamine")
    try:
        conn, cursor = loo_andmebaas()
        cursor.execute("SELECT id, kuupaev, marsruut, kilomeetrid FROM soidud")
        soidud = cursor.fetchall()

        if not soidud:
            print("ℹ️ Andmebaasis pole sõite, mida kustutada.")
            conn.close()
            return

        print("📋 Vali sõit, mida soovid kustutada:")
        for i, (id, kuupaev, marsruut, km) in enumerate(soidud, start=1):
            print(f"{i}. {kuupaev} – {marsruut} – {km} km")

        valik = input("Sisesta kustutatava sõidu number: ")
        try:
            indeks = int(valik) - 1
            if indeks < 0 or indeks >= len(soidud):
                print("❌ Viga: Vale valik.")
                conn.close()
                return
        except ValueError:
            print("❌ Viga: Palun sisesta number.")
            conn.close()
            return

        kustutatav_id = soidud[indeks][0]
        cursor.execute("DELETE FROM soidud WHERE id = ?", (kustutatav_id,))
        conn.commit()
        conn.close()
        print("✅ Sõit kustutatud!")
    except Exception as e:
        print(f"❌ Viga kustutamisel: {e}")

def ekspordi_csv():
    print("\n📤 Eksporditakse sõidud faili 'soidud.csv'")
    try:
        conn, cursor = loo_andmebaas()
        cursor.execute("SELECT kuupaev, marsruut, kilomeetrid FROM soidud")
        soidud = cursor.fetchall()

        if not soidud:
            print("ℹ️ Pole midagi eksportida – andmebaasis pole sõite.")
            conn.close()
            return

        with open("soidud.csv", mode="w", newline="", encoding="utf-8") as fail:
            writer = csv.writer(fail)
            writer.writerow(["Kuupäev", "Marsruut", "Kilomeetrid"])
            for rida in soidud:
                writer.writerow(rida)

        conn.close()
        print("✅ Sõidud salvestatud faili 'soidud.csv'")
    except Exception as e:
        print(f"❌ Viga eksportimisel: {e}")

def kuva_menuu():
    print("\n=== AUTOJUHI RAKENDUS ===")
    print("1. Sisesta uus sõit")
    print("2. Vaata kõiki sõite")
    print("3. Näita statistikat")
    print("4. Kustuta sõit")
    print("5. Ekspordi CSV-faili")
    print("6. Välju")

def main():
    while True:
        kuva_menuu()
        valik = input("Vali tegevus (1-6): ")

        if valik == "1":
            sisesta_soit()
        elif valik == "2":
            vaata_soite()
        elif valik == "3":
            statistika()
        elif valik == "4":
            kustuta_soit()
        elif valik == "5":
            ekspordi_csv()
        elif valik == "6":
            print("Rakendus suletakse. Head päeva!")
            break
        else:
            print("❌ Viga: Palun vali arv vahemikus 1–6.")

if __name__ == "__main__":
    main()
