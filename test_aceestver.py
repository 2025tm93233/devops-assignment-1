import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import Aceestver


class DummyVariable:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class DummyWidget:
    def __init__(self, *args, **kwargs):
        self.pack = MagicMock()
        self.delete = MagicMock()
        self.insert = MagicMock()


class TestACEestApp(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_aceest_fitness.db"
        self.patches = [
            patch.object(Aceestver, "DB_NAME", str(self.db_path)),
        ]

        for module, name in (
            (Aceestver.tk, "Label"),
            (Aceestver.tk, "Frame"),
            (Aceestver.tk, "LabelFrame"),
            (Aceestver.tk, "Entry"),
            (Aceestver.tk, "Text"),
            (Aceestver.ttk, "Combobox"),
            (Aceestver.ttk, "Scale"),
            (Aceestver.ttk, "Button"),
        ):
            self.patches.append(
                patch.object(module, name, side_effect=self._make_widget)
            )

        for active_patch in self.patches:
            active_patch.start()

        for name in ("StringVar", "IntVar", "DoubleVar"):
            active_patch = patch.object(
                Aceestver.tk,
                name,
                side_effect=lambda *args, **kwargs: DummyVariable(
                    kwargs.get("value", "")
                ),
            )
            active_patch.start()
            self.patches.append(active_patch)

        self.root = MagicMock()
        self.app = Aceestver.ACEestApp(self.root)

    def tearDown(self):
        if hasattr(self, "app"):
            self.app.conn.close()
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    @staticmethod
    def _make_widget(*args, **kwargs):
        return DummyWidget()

    def test_constructor_configures_window_and_creates_database_tables(self):
        self.root.title.assert_called_once_with("ACEest Fitness & Performance")
        self.root.geometry.assert_called_once_with("1200x800")
        self.root.configure.assert_called_once_with(bg="#1a1a1a")

        self.app.cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        self.assertEqual(
            [row[0] for row in self.app.cur.fetchall()],
            ["clients", "progress", "sqlite_sequence"],
        )
        self.assertEqual(
            set(self.app.programs),
            {"Fat Loss (FL)", "Muscle Gain (MG)", "Beginner (BG)"},
        )

    @patch("Aceestver.messagebox.showerror")
    def test_save_client_requires_name_and_program(self, showerror):
        self.app.save_client()

        showerror.assert_called_once_with("Error", "Name and Program required")
        self.app.cur.execute("SELECT COUNT(*) FROM clients")
        self.assertEqual(self.app.cur.fetchone()[0], 0)

    @patch("Aceestver.messagebox.showinfo")
    def test_save_client_inserts_client_and_calorie_estimate(self, showinfo):
        self.app.name.set("Sam")
        self.app.age.set(35)
        self.app.weight.set(70)
        self.app.program.set("Muscle Gain (MG)")

        self.app.save_client()

        self.app.cur.execute(
            "SELECT name, age, weight, program, calories FROM clients WHERE name=?",
            ("Sam",),
        )
        self.assertEqual(
            self.app.cur.fetchone(),
            ("Sam", 35, 70.0, "Muscle Gain (MG)", 2450),
        )
        showinfo.assert_called_once_with("Saved", "Client data saved")

    @patch("Aceestver.messagebox.showinfo")
    def test_save_client_replaces_existing_unique_name(self, showinfo):
        self.app.name.set("Sam")
        self.app.age.set(35)
        self.app.weight.set(70)
        self.app.program.set("Muscle Gain (MG)")
        self.app.save_client()

        self.app.age.set(36)
        self.app.weight.set(72)
        self.app.program.set("Fat Loss (FL)")
        self.app.save_client()

        self.app.cur.execute(
            "SELECT COUNT(*), age, weight, program, calories "
            "FROM clients WHERE name=?",
            ("Sam",),
        )
        self.assertEqual(
            self.app.cur.fetchone(),
            (1, 36, 72.0, "Fat Loss (FL)", 1584),
        )
        self.assertEqual(showinfo.call_count, 2)

    @patch("Aceestver.messagebox.showwarning")
    def test_load_client_warns_when_name_is_not_found(self, showwarning):
        self.app.name.set("Missing")

        self.app.load_client()

        showwarning.assert_called_once_with("Not Found", "Client not found")
        self.app.summary.insert.assert_not_called()

    @patch("Aceestver.messagebox.showinfo")
    def test_load_client_populates_fields_and_summary(self, showinfo):
        self.app.cur.execute(
            "INSERT INTO clients (name, age, weight, program, calories) "
            "VALUES (?, ?, ?, ?, ?)",
            ("Sam", 35, 70.0, "Muscle Gain (MG)", 2450),
        )
        self.app.conn.commit()
        self.app.name.set("Sam")

        self.app.load_client()

        self.assertEqual(self.app.age.get(), 35)
        self.assertEqual(self.app.weight.get(), 70.0)
        self.assertEqual(self.app.program.get(), "Muscle Gain (MG)")
        self.app.summary.delete.assert_called_once_with("1.0", "end")
        summary = self.app.summary.insert.call_args.args[1]
        self.assertIn("Name     : Sam", summary)
        self.assertIn("Calories : 2450 kcal/day", summary)
        showinfo.assert_not_called()

    @patch("Aceestver.messagebox.showinfo")
    def test_save_progress_records_adherence_and_week(self, showinfo):
        self.app.name.set("Sam")
        self.app.adherence.set(85)

        self.app.save_progress()

        self.app.cur.execute(
            "SELECT client_name, week, adherence FROM progress"
        )
        client_name, week, adherence = self.app.cur.fetchone()
        self.assertEqual(client_name, "Sam")
        self.assertRegex(week, r"^Week \d{2} - \d{4}$")
        self.assertEqual(adherence, 85)
        showinfo.assert_called_once_with(
            "Progress Saved", "Weekly progress logged"
        )


if __name__ == "__main__":
    unittest.main()
