import csv
import io
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as app_module


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.original_db_name = app_module.DB_NAME
        self.original_app_file = app_module.__file__
        self.original_testing = app_module.app.config.get("TESTING")
        self.temp_dir = tempfile.TemporaryDirectory(prefix="autojuhi_test_")
        self.addCleanup(self.temp_dir.cleanup)
        self.addCleanup(setattr, app_module, "DB_NAME", self.original_db_name)
        self.addCleanup(setattr, app_module, "__file__", self.original_app_file)
        self.addCleanup(app_module.app.config.__setitem__, "TESTING", self.original_testing)

        self.test_root = Path(self.temp_dir.name)
        self.app_root = self.test_root / "webapp"
        self.app_root.mkdir()
        app_module.DB_NAME = str(self.test_root / "users_test.db")
        app_module.__file__ = str(self.app_root / "app.py")
        app_module.app.config["TESTING"] = True

        connection, _ = app_module.loo_andmebaas()
        connection.close()
        self.client = app_module.app.test_client()

    def read_rides(self, database_path=None):
        connection = sqlite3.connect(database_path or app_module.DB_NAME)
        try:
            return connection.execute(
                "SELECT id, kuupaev, marsruut, kilomeetrid FROM soidud ORDER BY id"
            ).fetchall()
        finally:
            connection.close()

    def insert_ride(self, kuupaev, marsruut, kilomeetrid):
        connection = sqlite3.connect(app_module.DB_NAME)
        try:
            cursor = connection.execute(
                "INSERT INTO soidud (kuupaev, marsruut, kilomeetrid) VALUES (?, ?, ?)",
                (kuupaev, marsruut, kilomeetrid),
            )
            connection.commit()
            return cursor.lastrowid
        finally:
            connection.close()

    def upload_csv(self, content, filename="rides.csv"):
        return self.client.post(
            "/import",
            data={"file": (io.BytesIO(content), filename)},
            content_type="multipart/form-data",
        )

    def test_homepage_opens(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

    def test_add_ride_form_opens(self):
        response = self.client.get("/lisa")

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="kuupaev"', response.get_data(as_text=True))

    def test_valid_ride_is_saved(self):
        response = self.client.post(
            "/lisa",
            data={"kuupaev": "2026-01-03", "marsruut": "Tallinn-Tartu", "kilomeetrid": "186.5"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            [(row[1], row[2], row[3]) for row in self.read_rides()],
            [("2026-01-03", "Tallinn-Tartu", 186.5)],
        )

    def test_blank_route_is_rejected(self):
        response = self.client.post(
            "/lisa",
            data={"kuupaev": "2026-01-03", "marsruut": "   ", "kilomeetrid": "10"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.read_rides(), [])

    def test_nonnumeric_kilometers_are_rejected(self):
        response = self.client.post(
            "/lisa",
            data={"kuupaev": "2026-01-03", "marsruut": "Tallinn-Tartu", "kilomeetrid": "abc"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.read_rides(), [])

    def test_negative_kilometers_are_rejected(self):
        response = self.client.post(
            "/lisa",
            data={"kuupaev": "2026-01-03", "marsruut": "Tallinn-Tartu", "kilomeetrid": "-1"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.read_rides(), [])

    def test_missing_and_invalid_dates_are_rejected(self):
        for date_value in ("", "2026-02-30"):
            with self.subTest(date=date_value):
                response = self.client.post(
                    "/lisa",
                    data={"kuupaev": date_value, "marsruut": "Tallinn-Tartu", "kilomeetrid": "10"},
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.read_rides(), [])

    def test_rides_page_displays_saved_rides(self):
        self.insert_ride("2026-01-03", "Tallinn-Tartu", 186.5)

        response = self.client.get("/soidud")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tallinn-Tartu", response.get_data(as_text=True))

    def test_post_delete_removes_only_selected_ride(self):
        deleted_id = self.insert_ride("2026-01-03", "Tallinn-Tartu", 186.5)
        remaining_id = self.insert_ride("2026-01-04", "Tartu-Parnu", 128)

        response = self.client.post(f"/kustuta/{deleted_id}")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.read_rides(), [(remaining_id, "2026-01-04", "Tartu-Parnu", 128.0)])

    def test_general_statistics_routes_show_correct_totals(self):
        self.insert_ride("2025-01-05", "A-B", 10.5)
        self.insert_ride("2025-01-20", "B-C", 20.25)
        self.insert_ride("2026-02-03", "C-D", 40)

        stats_response = self.client.get("/stats")
        alias_response = self.client.get("/statistika")

        self.assertEqual(stats_response.status_code, 200)
        self.assertEqual(alias_response.status_code, 200)
        self.assertEqual(stats_response.get_data(), alias_response.get_data())
        page = stats_response.get_data(as_text=True)
        self.assertIn("3</p>", page)
        self.assertIn("70.75", page)

    def test_monthly_statistics_group_months_and_years(self):
        self.insert_ride("2025-01-05", "A-B", 10.5)
        self.insert_ride("2025-01-20", "B-C", 20.25)
        self.insert_ride("2025-02-03", "C-D", 30)
        self.insert_ride("2026-01-02", "D-E", 40)

        self.assertEqual(
            app_module.calculate_monthly_statistics(),
            [("2025-01", 2, 30.75), ("2025-02", 1, 30.0), ("2026-01", 1, 40.0)],
        )
        response = self.client.get("/stats/kuud")
        page = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        for value in ("2025-01", "2025-02", "2026-01", "30.75", "30.0", "40.0"):
            self.assertIn(value, page)

    def test_empty_database_statistics_do_not_fail(self):
        stats_response = self.client.get("/stats")
        alias_response = self.client.get("/statistika")
        monthly_response = self.client.get("/stats/kuud")

        self.assertEqual(stats_response.status_code, 200)
        self.assertEqual(alias_response.status_code, 200)
        self.assertEqual(monthly_response.status_code, 200)
        self.assertIn("0</p>", stats_response.get_data(as_text=True))
        self.assertNotIn("<td>", monthly_response.get_data(as_text=True))

    def test_csv_import_saves_multiple_rides(self):
        response = self.upload_csv(
            b"kuupaev,marsruut,kilomeetrid\n"
            b"2026-01-03,Tallinn-Tartu,186.5\n"
            b"2026-02-04,Tartu-Parnu,128\n"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(row[1], row[2], row[3]) for row in self.read_rides()],
            [("2026-01-03", "Tallinn-Tartu", 186.5), ("2026-02-04", "Tartu-Parnu", 128.0)],
        )

    def test_invalid_csv_rows_are_rejected_without_invalid_inserts(self):
        invalid_rows = (
            b"kuupaev,marsruut,kilomeetrid\n2026-01-03,   ,10\n",
            b"kuupaev,marsruut,kilomeetrid\n2026-01-03,Tallinn,abc\n",
            b"kuupaev,marsruut,kilomeetrid\n2026-01-03,Tallinn,-1\n",
        )
        for content in invalid_rows:
            with self.subTest(content=content):
                response = self.upload_csv(content)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.read_rides(), [])

    def test_csv_import_ignores_invalid_rows_but_imports_valid_ones(self):
        response = self.upload_csv(
            b"kuupaev,marsruut,kilomeetrid\n"
            b"2026-04-01,Valga-Tartu,70\n"
            b"2026-04-02,,80\n"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.read_rides()), 1)
        self.assertEqual(self.read_rides()[0][2], "Valga-Tartu")

    def test_malformed_csv_is_rejected(self):
        response = self.upload_csv(b'kuupaev,marsruut,kilomeetrid\n2026-01-01,"Route,10\n')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.read_rides(), [])

    def test_csv_missing_required_column_is_rejected(self):
        response = self.upload_csv(b"kuupaev,marsruut\n2026-01-01,Tallinn\n")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.read_rides(), [])

    def test_empty_and_invalid_utf8_csv_are_rejected(self):
        for content in (b"", b"kuupaev,marsruut,kilomeetrid\n\xff\n"):
            with self.subTest(content=content):
                response = self.upload_csv(content)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.read_rides(), [])

    def test_csv_export_uses_utf8_and_model_columns(self):
        self.insert_ride("2026-01-03", "Tallinn-Tartu", 186.5)

        response = self.client.get("/export")
        exported = response.get_data()
        export_files = list((self.app_root / "exports").glob("*.csv"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(export_files), 1)
        with export_files[0].open("r", encoding="utf-8", newline="") as csv_file:
            rows = list(csv.reader(csv_file))
        self.assertEqual(rows[0], ["kuupaev", "marsruut", "kilomeetrid"])
        self.assertEqual(rows[1], ["2026-01-03", "Tallinn-Tartu", "186.5"])
        self.assertEqual(exported.decode("utf-8").splitlines()[0], "kuupaev,marsruut,kilomeetrid")

    def test_export_can_be_imported_into_a_fresh_database(self):
        self.insert_ride("2026-01-03", "Tallinn-Tartu", 186.5)
        self.insert_ride("2026-02-04", "Tartu-Parnu", 128)
        expected = [(row[1], row[2], row[3]) for row in self.read_rides()]
        exported = self.client.get("/export").get_data()

        roundtrip_database = self.test_root / "roundtrip.db"
        app_module.DB_NAME = str(roundtrip_database)
        response = self.upload_csv(exported, "exported.csv")

        self.assertEqual(response.status_code, 200)
        actual = [(row[1], row[2], row[3]) for row in self.read_rides(roundtrip_database)]
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
