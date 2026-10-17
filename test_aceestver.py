import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _install_matplotlib_stub():
    pyplot = types.ModuleType("matplotlib.pyplot")
    for name in (
        "figure", "plot", "title", "xlabel", "ylabel", "ylim",
        "grid", "xticks", "tight_layout", "show",
    ):
        setattr(pyplot, name, MagicMock())

    matplotlib = types.ModuleType("matplotlib")
    matplotlib.__path__ = []
    matplotlib.pyplot = pyplot
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot


_install_matplotlib_stub()
sys.path.insert(0, str(Path(__file__).resolve().parent))
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
        self.options = kwargs
        self.value = ""
        self.pack = MagicMock()
        self.bind = MagicMock()
        self.add = MagicMock()
        self.configure = MagicMock()
        self.delete = MagicMock()
        self.insert = MagicMock()
        self.title = MagicMock()
        self.geometry = MagicMock()
        self.heading = MagicMock()
        self.column = MagicMock()

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def __getitem__(self, key):
        return self.options.get(key, [])

    def __setitem__(self, key, value):
        self.options[key] = value


class TestACEestApp(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_aceest_fitness.db"
        self.patches = [patch.object(Aceestver, "DB_NAME", str(self.db_path))]
        self.widgets = []

        for module, name in (
            (Aceestver.tk, "Label"),
            (Aceestver.tk, "Frame"),
            (Aceestver.tk, "LabelFrame"),
            (Aceestver.tk, "Entry"),
            (Aceestver.tk, "Text"),
            (Aceestver.ttk, "Combobox"),
            (Aceestver.ttk, "Scale"),
            (Aceestver.ttk, "Button"),
            (Aceestver.ttk, "Notebook"),
            (Aceestver.ttk, "Treeview"),
        ):
            self.patches.append(
                patch.object(module, name, side_effect=self._make_widget)
            )

        for active_patch in self.patches:
            active_patch.start()

        for name, default in (
            ("StringVar", ""),
            ("IntVar", 0),
            ("DoubleVar", 0.0),
        ):
            active_patch = patch.object(
                Aceestver.tk,
                name,
                side_effect=lambda *args, _default=default, **kwargs: DummyVariable(
                    kwargs.get("value", _default)
                ),
            )
            active_patch.start()
            self.patches.append(active_patch)

        for name in (
            "figure", "plot", "title", "xlabel", "ylabel", "ylim",
            "grid", "xticks", "tight_layout", "show",
        ):
            getattr(Aceestver.plt, name).reset_mock()

        self.root = MagicMock()
        self.app = Aceestver.ACEestApp(self.root)

    def tearDown(self):
        if hasattr(self, "app"):
            self.app.conn.close()
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def _make_widget(self, *args, **kwargs):
        widget = DummyWidget(*args, **kwargs)
        self.widgets.append(widget)
        return widget

    def test_constructor_configures_window_and_creates_database_tables(self):
        self.root.title.assert_called_once_with("ACEest Fitness & Performance")
        self.root.geometry.assert_called_once_with("1300x850")
        self.root.configure.assert_called_once_with(bg="#1a1a1a")

        self.app.cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        self.assertEqual(
            [row[0] for row in self.app.cur.fetchall()],
            ["clients", "exercises", "metrics", "progress", "workouts"],
        )
        self.assertEqual(self.app.client_list.options["values"], [])
        self.assertEqual(
            set(self.app.programs),
            {
                "Fat Loss (FL) – 3 day",
                "Fat Loss (FL) – 5 day",
                "Muscle Gain (MG) – PPL",
                "Beginner (BG)",
            },
        )

    @patch("Aceestver.messagebox.showerror")
    def test_save_client_requires_name_and_program(self, showerror):
        self.app.save_client()

        showerror.assert_called_once_with("Error", "Name is required")
        self.app.name.set("Sam")
        with patch.object(Aceestver.messagebox, "showerror") as showerror:
            self.app.save_client()
        showerror.assert_called_once_with("Error", "Program is required")
        self.app.cur.execute("SELECT COUNT(*) FROM clients")
        self.assertEqual(self.app.cur.fetchone()[0], 0)

    @patch("Aceestver.messagebox.showinfo")
    def test_save_client_inserts_client_and_calorie_estimate(self, showinfo):
        self.app.name.set(" Sam ")
        self.app.age.set(35)
        self.app.height.set(175)
        self.app.weight.set(70)
        self.app.program.set("Muscle Gain (MG) – PPL")
        self.app.target_weight.set(75)
        self.app.target_adherence.set(90)

        self.app.save_client()

        self.app.cur.execute(
            "SELECT name, age, height, weight, program, calories, "
            "target_weight, target_adherence FROM clients WHERE name=?",
            ("Sam",),
        )
        self.assertEqual(
            self.app.cur.fetchone(),
            ("Sam", 35, 175.0, 70.0, "Muscle Gain (MG) – PPL", 2450, 75.0, 90),
        )
        self.assertEqual(self.app.current_client, "Sam")
        self.assertEqual(self.app.client_list.options["values"], ["Sam"])
        showinfo.assert_called_once_with("Saved", "Client data saved")

    @patch("Aceestver.messagebox.showinfo")
    def test_save_client_replaces_existing_unique_name(self, showinfo):
        self.app.name.set("Sam")
        self.app.age.set(35)
        self.app.weight.set(70)
        self.app.program.set("Muscle Gain (MG) – PPL")
        self.app.save_client()

        self.app.age.set(36)
        self.app.weight.set(72)
        self.app.program.set("Fat Loss (FL) – 3 day")
        self.app.save_client()

        self.app.cur.execute(
            "SELECT COUNT(*), age, weight, program, calories "
            "FROM clients WHERE name=?",
            ("Sam",),
        )
        self.assertEqual(
            self.app.cur.fetchone(),
            (1, 36, 72.0, "Fat Loss (FL) – 3 day", 1584),
        )
        self.assertEqual(showinfo.call_count, 2)

    @patch("Aceestver.messagebox.showwarning")
    def test_load_client_warns_when_name_is_missing_or_not_found(self, showwarning):
        self.app.load_client()
        showwarning.assert_called_once_with(
            "No Client", "Enter or select client name first"
        )

        self.app.name.set("Missing")
        self.app.load_client()
        self.assertEqual(showwarning.call_count, 2)
        showwarning.assert_called_with("Not Found", "Client not found")

    @patch("Aceestver.messagebox.showinfo")
    def test_load_client_populates_fields_and_summary(self, showinfo):
        self.app.cur.execute(
            """
            INSERT INTO clients
            (name, age, height, weight, program, calories, target_weight, target_adherence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("Sam", 35, 175.0, 70.0, "Muscle Gain (MG) – PPL", 2450, 75.0, 90),
        )
        self.app.conn.commit()
        self.app.name.set("Sam")

        self.app.load_client()

        self.assertEqual(self.app.current_client, "Sam")
        self.assertEqual(self.app.age.get(), 35)
        self.assertEqual(self.app.height.get(), 175.0)
        self.assertEqual(self.app.weight.get(), 70.0)
        self.assertEqual(self.app.program.get(), "Muscle Gain (MG) – PPL")
        self.assertEqual(self.app.target_weight.get(), 75.0)
        self.assertEqual(self.app.target_adherence.get(), 90)
        summary = self.app.summary.insert.call_args.args[1]
        self.assertIn("Name      : Sam", summary)
        self.assertIn("Calories  : 2450 kcal/day", summary)
        self.assertIn("Target Weight: 75.0 kg", summary)
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

    @patch("Aceestver.messagebox.showwarning")
    def test_save_progress_requires_client_name(self, showwarning):
        self.app.save_progress()
        showwarning.assert_called_once_with("No Client", "Enter client name first")
        self.app.cur.execute("SELECT COUNT(*) FROM progress")
        self.assertEqual(self.app.cur.fetchone()[0], 0)

    @patch("Aceestver.messagebox.showwarning")
    def test_ensure_client_requires_a_client_and_accepts_name(self, showwarning):
        self.assertFalse(self.app.ensure_client())
        showwarning.assert_called_once_with(
            "No Client", "Select or enter client first"
        )
        self.app.name.set("Sam")
        self.assertTrue(self.app.ensure_client())
        self.assertEqual(self.app.current_client, "Sam")

    @patch("Aceestver.messagebox.showinfo")
    @patch("Aceestver.messagebox.showwarning")
    def test_bmi_info_calculates_bmi_and_warns_for_missing_data(
        self, showwarning, showinfo
    ):
        self.app.current_client = "Sam"
        self.app.height.set(175)
        self.app.weight.set(70)
        self.app.show_bmi_info()
        self.assertIn("BMI for Sam: 22.9 (Normal)", showinfo.call_args.args[1])

        self.app.height.set(0)
        self.app.show_bmi_info()
        showwarning.assert_called_once_with(
            "Missing Data", "Enter valid height and weight first"
        )

    def test_progress_chart_plots_saved_adherence(self):
        self.app.current_client = "Sam"
        self.app.cur.execute(
            "INSERT INTO progress (client_name, week, adherence) VALUES "
            "('Sam', 'Week 01 - 2026', 80), ('Sam', 'Week 02 - 2026', 90)"
        )
        self.app.conn.commit()

        self.app.show_progress_chart()

        Aceestver.plt.plot.assert_called_once_with(
            ["Week 01 - 2026", "Week 02 - 2026"],
            [80, 90],
            marker="o",
            linewidth=2,
        )
        Aceestver.plt.show.assert_called_once_with()

    def test_weight_chart_plots_saved_body_metrics(self):
        self.app.current_client = "Sam"
        self.app.cur.execute(
            "INSERT INTO metrics (client_name, date, weight) VALUES "
            "('Sam', '2026-01-01', 70), ('Sam', '2026-02-01', 68)"
        )
        self.app.conn.commit()

        self.app.show_weight_chart()

        Aceestver.plt.plot.assert_called_once_with(
            ["2026-01-01", "2026-02-01"],
            [70.0, 68.0],
            marker="o",
            linewidth=2,
            color="orange",
        )
        Aceestver.plt.show.assert_called_once_with()

    def test_workout_history_displays_current_clients_records(self):
        self.app.current_client = "Sam"
        self.app.cur.execute(
            "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) "
            "VALUES ('Sam', '2026-05-01', 'Strength', 45, 'Squats')"
        )
        self.app.conn.commit()
        history_window = DummyWidget()
        with patch.object(Aceestver.tk, "Toplevel", return_value=history_window):
            self.app.open_workout_history_window()

        tree = self.widgets[-1]
        tree.insert.assert_called_once_with(
            "", "end", values=("2026-05-01", "Strength", 45, "Squats")
        )
        self.assertEqual(
            self.app.status_var.get(), "Loaded workout history for Sam"
        )


if __name__ == "__main__":
    unittest.main()
