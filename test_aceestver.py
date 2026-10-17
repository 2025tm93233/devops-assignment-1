import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _install_external_dependency_stubs():
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = MagicMock(return_value=(MagicMock(), MagicMock()))
    for name in (
        "figure",
        "plot",
        "title",
        "xlabel",
        "ylabel",
        "ylim",
        "grid",
        "xticks",
        "tight_layout",
        "show",
    ):
        setattr(pyplot, name, MagicMock())

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

    backend_tkagg.FigureCanvasTkAgg = FigureCanvasTkAgg

    class FPDF:
        def __init__(self):
            self.add_page = MagicMock()
            self.set_font = MagicMock()
            self.cell = MagicMock()
            self.ln = MagicMock()
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
        self.withdraw = MagicMock()
        self.deiconify = MagicMock()
        self.protocol = MagicMock()
        self.transient = MagicMock()
        self.grab_set = MagicMock()
        self.grab_release = MagicMock()
        self.focus_set = MagicMock()
        self.heading = MagicMock()
        self.column = MagicMock()
        self.get_children = MagicMock(return_value=[])

    def get(self, *args):
        return self.value

    def set(self, value):
        self.value = value

    def __getitem__(self, key):
        return self.options.get(key, [])

    def __setitem__(self, key, value):
        self.options[key] = value


_install_external_dependency_stubs()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import Aceestver


class TestACEestApp(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test_aceest_fitness.db"
        self.patches = [patch.object(Aceestver, "DB_NAME", str(db_path))]
        self.widgets = []
        self.variables = {"StringVar": [], "IntVar": [], "DoubleVar": []}

        for module, name in (
            (Aceestver.tk, "Label"),
            (Aceestver.tk, "Frame"),
            (Aceestver.tk, "LabelFrame"),
            (Aceestver.tk, "Entry"),
            (Aceestver.tk, "Text"),
            (Aceestver.tk, "Toplevel"),
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
                side_effect=lambda *args, _name=name, _default=default, **kwargs: (
                    self._make_variable(_name, kwargs.get("value", _default))
                ),
            )
            active_patch.start()
            self.patches.append(active_patch)

        self.root = MagicMock()
        self.app = Aceestver.ACEestApp(self.root)
        self.app.username_var.set("admin")
        self.app.password_var.set("admin")
        self.app.login_user()

    def tearDown(self):
        if getattr(self.app, "conn", None):
            self.app.conn.close()
        for active_patch in reversed(self.patches):
            active_patch.stop()
        self.temp_dir.cleanup()

    def _make_widget(self, *args, **kwargs):
        widget = DummyWidget(*args, **kwargs)
        self.widgets.append(widget)
        return widget

    def _make_variable(self, name, value):
        variable = DummyVariable(value)
        self.variables[name].append(variable)
        return variable

    def _insert_client(
        self, name="Sam", program="Beginner (BG)", membership="2027-01-31"
    ):
        self.app.cur.execute(
            """
            INSERT INTO clients
            (name, age, height, weight, program, calories, membership_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, 35, 175, 70, program, 1820, membership),
        )
        self.app.conn.commit()
        self.app.current_client = name

    def test_startup_creates_schema_and_default_admin(self):
        self.root.geometry.assert_called_once_with("1400x900")
        self.root.withdraw.assert_called_once_with()
        self.app.login_win.title.assert_called_once_with("Login")
        self.assertEqual(self.app.current_user, "admin")
        self.assertEqual(self.app.user_role, "Admin")
        self.root.deiconify.assert_called_once_with()

        self.app.cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        self.assertEqual(
            [row[0] for row in self.app.cur.fetchall()],
            ["clients", "exercises", "metrics", "progress", "users", "workouts"],
        )
        self.app.cur.execute(
            "SELECT username, role FROM users WHERE username='admin'"
        )
        self.assertEqual(self.app.cur.fetchone(), ("admin", "Admin"))
        self.assertIn("membership_expiry", {
            row[1] for row in self.app.cur.execute("PRAGMA table_info(clients)")
        })

    @patch("Aceestver.messagebox.showerror")
    def test_invalid_login_reports_error_without_authenticating(self, showerror):
        self.app.current_user = None
        self.app.user_role = None
        self.app.username_var.set("unknown")
        self.app.password_var.set("wrong")

        self.app.login_user()

        self.assertIsNone(self.app.current_user)
        self.assertIsNone(self.app.user_role)
        showerror.assert_called_once_with(
            "Login Failed", "Invalid credentials\nTry admin / admin"
        )

    def test_login_close_exits_application(self):
        self.app.on_login_close()

        self.root.destroy.assert_called_once_with()

    def test_save_client_requires_a_name(self):
        with patch.object(Aceestver.messagebox, "showerror") as showerror:
            self.app.save_client()
        showerror.assert_called_once_with("Error", "Name required")
        self.app.cur.execute("SELECT COUNT(*) FROM clients")
        self.assertEqual(self.app.cur.fetchone()[0], 0)

    @patch("Aceestver.messagebox.showinfo")
    def test_save_client_persists_profile_membership_and_calories(self, showinfo):
        self.app.name.set(" Sam ")
        self.app.age.set(35)
        self.app.height.set(175)
        self.app.weight.set(70)
        self.app.program.set("Muscle Gain (MG) – PPL")
        self.app.membership_var.set("2027-12-31")

        self.app.save_client()

        self.app.cur.execute(
            "SELECT name, age, height, weight, program, calories, membership_expiry "
            "FROM clients"
        )
        self.assertEqual(
            self.app.cur.fetchone(),
            ("Sam", 35, 175.0, 70.0, "Muscle Gain (MG) – PPL", 2450, "2027-12-31"),
        )
        self.assertEqual(self.app.current_client, "Sam")
        self.assertEqual(self.app.client_list["values"], ["Sam"])
        self.assertEqual(self.app.status_var.get(), "Saved client: Sam")
        showinfo.assert_called_once_with("Saved", "Client data saved")

    def test_load_client_populates_profile_and_summary(self):
        self._insert_client()

        self.app.load_client()

        self.assertEqual(self.app.name.get(), "Sam")
        self.assertEqual(self.app.age.get(), 35)
        self.assertEqual(self.app.height.get(), 175)
        self.assertEqual(self.app.weight.get(), 70)
        self.assertEqual(self.app.program.get(), "Beginner (BG)")
        self.assertEqual(self.app.membership_var.get(), "2027-01-31")
        summary = self.app.summary.insert.call_args.args[1]
        self.assertIn("Name: Sam", summary)
        self.assertIn("Membership Expiry: 2027-01-31", summary)

    def test_load_client_with_no_selection_does_nothing(self):
        self.app.load_client()

        self.app.summary.insert.assert_not_called()
        self.assertIsNone(self.app.current_client)

    @patch("Aceestver.messagebox.showinfo")
    @patch("Aceestver.simpledialog.askstring", return_value="beginner")
    def test_generate_ai_program_creates_beginner_weekly_plan(
        self, askstring, showinfo
    ):
        self._insert_client()
        tree = self.app.program_tree

        with patch.object(Aceestver.random, "sample", side_effect=lambda values, k: values[:k]):
            with patch.object(Aceestver.random, "randint", side_effect=[2, 8] * 9):
                self.app.generate_ai_program()

        self.assertEqual(tree.insert.call_count, 9)
        first_plan_item = tree.insert.call_args_list[0].kwargs["values"]
        self.assertEqual(first_plan_item[0], "Monday")
        self.assertEqual(first_plan_item[2:], (2, 8))
        self.assertEqual(self.app.status_var.get(), "AI program generated for Sam")
        askstring.assert_called_once()
        showinfo.assert_called_once_with(
            "Generated", "AI workout program generated!"
        )

    @patch("Aceestver.messagebox.showerror")
    @patch("Aceestver.simpledialog.askstring", return_value="expert")
    def test_generate_ai_program_rejects_invalid_experience(
        self, askstring, showerror
    ):
        self._insert_client()

        self.app.generate_ai_program()

        askstring.assert_called_once()
        showerror.assert_called_once_with("Error", "Invalid experience level")
        self.app.program_tree.insert.assert_not_called()

    @patch("Aceestver.messagebox.showerror")
    def test_generate_ai_program_requires_selected_client(self, showerror):
        self.app.generate_ai_program()

        showerror.assert_called_once_with("Error", "Select client first")

    @patch("Aceestver.messagebox.showinfo")
    def test_pdf_report_exports_selected_client_record(self, showinfo):
        self._insert_client()
        pdf = MagicMock()

        with patch.object(Aceestver, "FPDF", return_value=pdf):
            self.app.export_pdf_report()

        pdf.add_page.assert_called_once_with()
        pdf.cell.assert_any_call(0, 10, "Client Report - Sam", ln=True, align="C")
        pdf.cell.assert_any_call(0, 10, "Membership Expiry: 2027-01-31", ln=True)
        pdf.output.assert_called_once_with("Sam_report.pdf")
        showinfo.assert_called_once_with(
            "PDF Exported", "Report saved as Sam_report.pdf"
        )

    def test_pdf_report_without_selected_client_does_nothing(self):
        with patch.object(Aceestver, "FPDF") as pdf_class:
            self.app.export_pdf_report()

        pdf_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
