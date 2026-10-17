import csv
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _load_app_without_matplotlib_dependency():
    matplotlib = types.ModuleType("matplotlib")
    matplotlib.__path__ = []
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = MagicMock(return_value=(MagicMock(), MagicMock()))

    backends = types.ModuleType("matplotlib.backends")
    backends.__path__ = []
    backend_tkagg = types.ModuleType("matplotlib.backends.backend_tkagg")

    class FigureCanvasTkAgg:
        def __init__(self, *args, **kwargs):
            self.widget = DummyWidget()
            self.draw = MagicMock()

        def get_tk_widget(self):
            return self.widget

    backend_tkagg.FigureCanvasTkAgg = FigureCanvasTkAgg
    fake_modules = {
        "matplotlib": matplotlib,
        "matplotlib.pyplot": pyplot,
        "matplotlib.backends": backends,
        "matplotlib.backends.backend_tkagg": backend_tkagg,
    }
    sys.modules.update(fake_modules)
    project_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(project_root))
    import Aceestver

    return Aceestver


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
        self.pack = MagicMock()
        self.config = MagicMock()
        self.bind = MagicMock()
        self.delete = MagicMock()
        self.insert = MagicMock()
        self.heading = MagicMock()
        self.draw = MagicMock()

    def __getitem__(self, key):
        return self.options[key]


Aceestver = _load_app_without_matplotlib_dependency()


class TestACEestApp(unittest.TestCase):
    def setUp(self):
        self.patches = []

        widget_factories = (
            (Aceestver.tk, "Frame"),
            (Aceestver.tk, "LabelFrame"),
            (Aceestver.tk, "Label"),
            (Aceestver.tk, "Entry"),
            (Aceestver.tk, "Text"),
            (Aceestver.ttk, "Combobox"),
            (Aceestver.ttk, "Scale"),
            (Aceestver.ttk, "Button"),
            (Aceestver.ttk, "Treeview"),
        )
        for module, name in widget_factories:
            self._patch(module, name, side_effect=self._make_widget)

        for name in ("StringVar", "IntVar", "DoubleVar"):
            self._patch(
                Aceestver.tk,
                name,
                side_effect=lambda *args, **kwargs: DummyVariable(
                    kwargs.get("value", "")
                ),
            )

        self.root = MagicMock()
        self.app = Aceestver.ACEestApp(self.root)

    def tearDown(self):
        for active_patch in reversed(self.patches):
            active_patch.stop()

    def _patch(self, target, name, **kwargs):
        active_patch = patch.object(target, name, **kwargs)
        mocked = active_patch.start()
        self.patches.append(active_patch)
        return mocked

    @staticmethod
    def _make_widget(*args, **kwargs):
        return DummyWidget(*args, **kwargs)

    def test_constructor_sets_window_and_client_program_data(self):
        self.root.title.assert_called_once_with("ACEest Fitness & Performance")
        self.root.geometry.assert_called_once_with("1250x820")
        self.root.configure.assert_called_once_with(bg="#1a1a1a")
        self.assertEqual(self.app.clients, [])
        self.assertEqual(
            set(self.app.programs),
            {"Fat Loss (FL)", "Muscle Gain (MG)", "Beginner (BG)"},
        )
        for program in self.app.programs.values():
            self.assertTrue(
                {"workout", "diet", "color", "calorie_factor"}.issubset(program)
            )

    def test_program_selection_updates_plans_and_calorie_estimate(self):
        self.app.program_var.set("Muscle Gain (MG)")
        self.app.weight_var.set(70)

        self.app.update_program()

        program = self.app.programs["Muscle Gain (MG)"]
        self.app.workout_text.insert.assert_called_once_with("end", program["workout"])
        self.app.workout_text.config.assert_any_call(
            fg=program["color"], state="disabled"
        )
        self.app.diet_text.insert.assert_called_once_with("end", program["diet"])
        self.app.diet_text.config.assert_any_call(fg="white", state="disabled")
        self.app.calorie_label.config.assert_called_once_with(
            text="Estimated Calories: 2450 kcal"
        )

    def test_program_selection_without_program_does_nothing(self):
        self.app.update_program()

        self.app.workout_text.insert.assert_not_called()
        self.app.diet_text.insert.assert_not_called()
        self.app.calorie_label.config.assert_not_called()

    @patch("Aceestver.messagebox.showwarning")
    def test_save_client_warns_when_required_fields_are_missing(self, showwarning):
        self.app.save_client()

        showwarning.assert_called_once_with(
            "Incomplete", "Please fill client name and program."
        )
        self.assertEqual(self.app.clients, [])

    @patch("Aceestver.messagebox.showinfo")
    def test_save_client_stores_record_updates_table_and_chart(self, showinfo):
        self.app.name_var.set("Sam")
        self.app.age_var.set(35)
        self.app.weight_var.set(70)
        self.app.program_var.set("Fat Loss (FL)")
        self.app.progress_var.set(80)
        self.app.notes_var.set("Good progress")

        with patch.object(self.app, "update_chart") as update_chart:
            self.app.save_client()

        client = ("Sam", 35, 70, "Fat Loss (FL)", 80, "Good progress")
        self.assertEqual(self.app.clients, [client])
        self.app.client_table.insert.assert_called_once_with("", "end", values=client)
        update_chart.assert_called_once_with()
        showinfo.assert_called_once_with("Saved", "Client Sam saved successfully.")

    @patch("Aceestver.messagebox.showwarning")
    def test_export_csv_warns_if_no_clients_exist(self, showwarning):
        self.app.export_csv()

        showwarning.assert_called_once_with("No Data", "No clients to export.")

    @patch("Aceestver.messagebox.showinfo")
    @patch("Aceestver.filedialog.asksaveasfilename")
    def test_export_csv_writes_headers_and_client_rows(self, ask_filename, showinfo):
        client = ("Sam", 35, 70, "Fat Loss (FL)", 80, "Good progress")
        self.app.clients.append(client)

        with tempfile.TemporaryDirectory() as directory:
            output_path = str(Path(directory) / "clients.csv")
            ask_filename.return_value = output_path

            self.app.export_csv()

            with open(output_path, newline="", encoding="utf-8") as output:
                rows = list(csv.reader(output))

        self.assertEqual(
            rows,
            [
                ["Name", "Age", "Weight", "Program", "Adherence", "Notes"],
                ["Sam", "35", "70", "Fat Loss (FL)", "80", "Good progress"],
            ],
        )
        showinfo.assert_called_once_with(
            "Exported", f"Client data exported to {output_path}"
        )

    def test_update_chart_plots_client_adherence_and_draws(self):
        self.app.clients = [
            ("Sam", 35, 70, "Fat Loss (FL)", 80, "Good progress"),
            ("Lee", 29, 65, "Beginner (BG)", 60, ""),
        ]

        self.app.update_chart()

        self.app.ax.clear.assert_called_once_with()
        self.app.ax.bar.assert_called_once_with(
            ["Sam", "Lee"], [80, 60], color="#d4af37"
        )
        self.app.ax.set_ylabel.assert_called_once_with("Adherence %")
        self.app.ax.set_title.assert_called_once_with("Client Progress")
        self.app.canvas.draw.assert_called_once_with()

    def test_reset_clears_form_and_resets_display(self):
        self.app.name_var.set("Sam")
        self.app.age_var.set(35)
        self.app.weight_var.set(70)
        self.app.program_var.set("Muscle Gain (MG)")
        self.app.progress_var.set(80)
        self.app.notes_var.set("Good progress")

        self.app.reset()

        self.assertEqual(self.app.name_var.get(), "")
        self.assertEqual(self.app.age_var.get(), 0)
        self.assertEqual(self.app.weight_var.get(), 0)
        self.assertEqual(self.app.program_var.get(), "")
        self.assertEqual(self.app.progress_var.get(), 0)
        self.assertEqual(self.app.notes_var.get(), "")
        self.app.workout_text.insert.assert_called_once_with("end", "")
        self.app.diet_text.insert.assert_called_once_with("end", "")
        self.app.calorie_label.config.assert_called_once_with(
            text="Estimated Calories: --"
        )


if __name__ == "__main__":
    unittest.main()
