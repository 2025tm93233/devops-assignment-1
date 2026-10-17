import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _install_dependency_stubs():
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = MagicMock(return_value=(MagicMock(), MagicMock()))
    pyplot.figure = MagicMock()
    pyplot.plot = MagicMock()
    pyplot.show = MagicMock()

    matplotlib = types.ModuleType("matplotlib")
    matplotlib.__path__ = []
    matplotlib.pyplot = pyplot
    backends = types.ModuleType("matplotlib.backends")
    backends.__path__ = []
    backend_tkagg = types.ModuleType("matplotlib.backends.backend_tkagg")

    class FigureCanvasTkAgg:
        def __init__(self, *args, **kwargs):
            self.widget = DummyWidget()

        def get_tk_widget(self):
            return self.widget

        def draw(self):
            pass

    backend_tkagg.FigureCanvasTkAgg = FigureCanvasTkAgg

    class FPDF:
        def __init__(self):
            self.add_page = MagicMock()
            self.set_font = MagicMock()
            self.cell = MagicMock()
            self.output = MagicMock()

    fpdf = types.ModuleType("fpdf")
    fpdf.FPDF = FPDF
    sys.modules.update(
        {
            "matplotlib": matplotlib,
            "matplotlib.pyplot": pyplot,
            "matplotlib.backends": backends,
            "matplotlib.backends.backend_tkagg": backend_tkagg,
            "fpdf": fpdf,
        }
    )


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
        self.destroy = MagicMock()
        self.heading = MagicMock()
        self.column = MagicMock()
        self.get_children = MagicMock(return_value=[])
        self.winfo_children = MagicMock(return_value=[])

    def get(self, *args):
        return self.value

    def set(self, value):
        self.value = value

    def __getitem__(self, key):
        return self.options.get(key, [])

    def __setitem__(self, key, value):
        self.options[key] = value


_install_dependency_stubs()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import Aceestver


class TestDatabaseInitialization(unittest.TestCase):
    def test_init_db_creates_tables_and_default_admin(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "test.db"
            with patch.object(Aceestver, "DB_NAME", str(db_path)):
                Aceestver.init_db()

            connection = sqlite3.connect(db_path)
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
                self.assertEqual(
                    [row[0] for row in cursor.fetchall()],
                    ["clients", "exercises", "metrics", "progress", "users", "workouts"],
                )
                cursor.execute(
                    "SELECT username, password, role FROM users WHERE username='admin'"
                )
                self.assertEqual(cursor.fetchone(), ("admin", "admin", "Admin"))
            finally:
                connection.close()


class TestACEestApp(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db_patch = patch.object(Aceestver, "DB_NAME", str(self.db_path))
        self.db_patch.start()
        Aceestver.init_db()

        self.patches = []
        self.widgets = []
        for module, name in (
            (Aceestver.tk, "Label"),
            (Aceestver.tk, "Frame"),
            (Aceestver.tk, "Entry"),
            (Aceestver.tk, "Text"),
            (Aceestver.tk, "Toplevel"),
            (Aceestver.ttk, "Combobox"),
            (Aceestver.ttk, "Button"),
            (Aceestver.ttk, "Notebook"),
            (Aceestver.ttk, "Treeview"),
        ):
            active_patch = patch.object(module, name, side_effect=self._make_widget)
            active_patch.start()
            self.patches.append(active_patch)

        for name, default in (("StringVar", ""), ("IntVar", 0), ("DoubleVar", 0.0)):
            active_patch = patch.object(
                Aceestver.tk,
                name,
                side_effect=lambda *args, _default=default, **kwargs: DummyVariable(
                    kwargs.get("value", _default)
                ),
            )
            active_patch.start()
            self.patches.append(active_patch)

        self.root = MagicMock()
        self.app = Aceestver.ACEestApp(self.root)
        self.app.current_role = "Admin"
        self.app.dashboard()

    def tearDown(self):
        if getattr(self.app, "conn", None):
            self.app.conn.close()
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.db_patch.stop()
        self.temp_dir.cleanup()

    def _make_widget(self, *args, **kwargs):
        widget = DummyWidget(*args, **kwargs)
        self.widgets.append(widget)
        return widget

    def _insert_client(self, name="Sam", program="Strength", status="Active", end="2027-01-31"):
        self.app.cur.execute(
            """
            INSERT INTO clients
            (name, age, height, weight, program, calories,
             membership_status, membership_end)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, 35, 175, 70, program, 2450, status, end),
        )
        self.app.conn.commit()
        self.app.current_client = name

    def test_dashboard_sets_up_client_and_workout_views(self):
        self.root.geometry.assert_called_once_with("1400x900")
        self.assertEqual(
            set(self.app.program_templates),
            {"Fat Loss", "Muscle Gain", "Beginner"},
        )
        self.assertTrue(hasattr(self.app, "summary_text"))
        self.assertTrue(hasattr(self.app, "tree_workouts"))

    def test_login_accepts_default_admin_credentials(self):
        self.app.username_var.set("admin")
        self.app.password_var.set("admin")

        self.app.login()

        self.assertEqual(self.app.current_user, "admin")
        self.assertEqual(self.app.current_role, "Admin")
        self.assertTrue(hasattr(self.app, "client_list"))

    def test_login_rejects_invalid_credentials(self):
        self.app.username_var.set("unknown")
        self.app.password_var.set("incorrect")

        with patch.object(Aceestver.messagebox, "showerror") as showerror:
            self.app.login()

        self.assertIsNone(self.app.current_user)
        showerror.assert_called_once_with("Login Failed", "Invalid credentials")

    def test_add_save_client_inserts_active_client(self):
        dialog = types.SimpleNamespace(askstring=MagicMock(return_value="Sam"))
        with patch.object(Aceestver.tk, "simpledialog", dialog, create=True):
            with patch.object(Aceestver.messagebox, "showinfo") as showinfo:
                self.app.add_save_client()

        self.app.cur.execute(
            "SELECT name, membership_status FROM clients WHERE name='Sam'"
        )
        self.assertEqual(self.app.cur.fetchone(), ("Sam", "Active"))
        self.assertEqual(self.app.client_list["values"], ["Sam"])
        showinfo.assert_called_once_with("Saved", "Client Sam saved")

    def test_generate_program_requires_a_client(self):
        with patch.object(Aceestver.messagebox, "showwarning") as showwarning:
            self.app.generate_program()
        showwarning.assert_called_once_with("No Client", "Select a client first")

    def test_generate_program_updates_selected_client_record(self):
        self._insert_client(program="Old Plan")
        with patch.object(
            Aceestver.random,
            "choice",
            side_effect=["Muscle Gain", "Push/Pull/Legs"],
        ):
            with patch.object(Aceestver.messagebox, "showinfo") as showinfo:
                self.app.generate_program()

        self.app.cur.execute("SELECT program FROM clients WHERE name='Sam'")
        self.assertEqual(self.app.cur.fetchone()[0], "Push/Pull/Legs")
        showinfo.assert_called_once_with(
            "Program Generated", "Program for Sam: Push/Pull/Legs"
        )

    def test_check_membership_shows_status_and_renewal_date(self):
        self._insert_client(status="Active", end="2027-01-31")
        with patch.object(Aceestver.messagebox, "showinfo") as showinfo:
            self.app.check_membership()
        showinfo.assert_called_once_with(
            "Membership", "Membership: Active\nRenewal Date: 2027-01-31"
        )

    def test_membership_check_returns_if_client_is_not_selected(self):
        with patch.object(Aceestver.messagebox, "showinfo") as showinfo:
            self.app.check_membership()
        showinfo.assert_not_called()

    def test_refresh_summary_shows_membership_fields(self):
        self._insert_client()

        self.app.refresh_summary()

        summary = self.app.summary_text.insert.call_args.args[1]
        self.assertIn("Name: Sam", summary)
        self.assertIn("Program: Strength", summary)
        self.assertIn("Membership: Active", summary)

    def test_load_client_refreshes_summary_workouts_and_charts(self):
        self._insert_client()
        self.app.client_list.set("Sam")
        with (
            patch.object(self.app, "refresh_summary") as refresh_summary,
            patch.object(self.app, "refresh_workouts") as refresh_workouts,
            patch.object(self.app, "plot_charts") as plot_charts,
        ):
            self.app.load_client()

        self.assertEqual(self.app.current_client, "Sam")
        refresh_summary.assert_called_once_with()
        refresh_workouts.assert_called_once_with()
        plot_charts.assert_called_once_with()

    def test_generate_pdf_exports_selected_client(self):
        self._insert_client()
        pdf = MagicMock()
        with patch.object(Aceestver, "FPDF", return_value=pdf):
            with patch.object(Aceestver.messagebox, "showinfo") as showinfo:
                self.app.generate_pdf()

        pdf.add_page.assert_called_once_with()
        pdf.cell.assert_any_call(0, 10, "ACEest Client Report - Sam", ln=True)
        pdf.output.assert_called_once_with("Sam_report.pdf")
        showinfo.assert_called_once_with("PDF Generated", "Sam_report.pdf created")

    def test_generate_pdf_without_client_shows_warning(self):
        with patch.object(Aceestver.messagebox, "showwarning") as showwarning:
            self.app.generate_pdf()
        showwarning.assert_called_once_with("No Client", "Select a client first")
