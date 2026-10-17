import unittest
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
        self.config = MagicMock()
        self.bind = MagicMock()
        self.delete = MagicMock()
        self.insert = MagicMock()


class TestACEestApp(unittest.TestCase):
    def setUp(self):
        self.patches = []
        self.variables = []

        widget_factories = (
            (Aceestver.tk, "Frame"),
            (Aceestver.tk, "LabelFrame"),
            (Aceestver.tk, "Label"),
            (Aceestver.tk, "Entry"),
            (Aceestver.tk, "Text"),
            (Aceestver.ttk, "Combobox"),
            (Aceestver.ttk, "Scale"),
            (Aceestver.ttk, "Button"),
        )
        for module, name in widget_factories:
            self._patch(module, name, side_effect=self._make_widget)

        self._patch(Aceestver.ttk, "Style", side_effect=self._make_style)
        for name in ("StringVar", "IntVar", "DoubleVar"):
            self._patch(
                Aceestver.tk,
                name,
                side_effect=self._make_variable,
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
        return DummyWidget()

    @staticmethod
    def _make_style(*args, **kwargs):
        style = MagicMock()
        return style

    def _make_variable(self, *args, **kwargs):
        variable = DummyVariable(kwargs.get("value", ""))
        self.variables.append(variable)
        return variable

    def test_constructor_sets_window_and_program_data(self):
        self.root.title.assert_called_once_with("ACEest Fitness & Performance")
        self.root.geometry.assert_called_once_with("1150x780")
        self.root.configure.assert_called_once_with(bg="#1a1a1a")

        self.assertEqual(
            set(self.app.programs),
            {"Fat Loss (FL)", "Muscle Gain (MG)", "Beginner (BG)"},
        )
        for program in self.app.programs.values():
            self.assertIn("workout", program)
            self.assertIn("diet", program)
            self.assertIn("color", program)
            self.assertIn("calorie_factor", program)

    def test_program_selection_updates_plans_and_calorie_estimate(self):
        self.app.program_var.set("Muscle Gain (MG)")
        self.app.weight_var.set(70)

        self.app.update_program()

        program = self.app.programs["Muscle Gain (MG)"]
        self.app.workout_text.delete.assert_called_once_with("1.0", "end")
        self.app.workout_text.insert.assert_called_once_with("end", program["workout"])
        self.app.workout_text.config.assert_any_call(fg=program["color"], state="disabled")
        self.app.diet_text.insert.assert_called_once_with("end", program["diet"])
        self.app.diet_text.config.assert_any_call(fg="white", state="disabled")
        self.app.calorie_label.config.assert_called_once_with(
            text="Estimated Calories: 2450 kcal"
        )

    def test_program_selection_without_positive_weight_does_not_estimate_calories(self):
        self.app.program_var.set("Beginner (BG)")
        self.app.weight_var.set(0)

        self.app.update_program()

        self.app.calorie_label.config.assert_not_called()

    def test_program_combobox_is_bound_to_update_handler(self):
        self.app.program_box.bind.assert_called_once_with(
            "<<ComboboxSelected>>", self.app.update_program
        )

    @patch("Aceestver.messagebox.showwarning")
    def test_save_client_warns_when_required_fields_are_missing(self, showwarning):
        self.app.save_client()

        showwarning.assert_called_once_with(
            "Incomplete", "Please fill client name and program."
        )

    @patch("Aceestver.messagebox.showinfo")
    def test_save_client_shows_success_message(self, showinfo):
        self.app.name_var.set("Sam")
        self.app.program_var.set("Fat Loss (FL)")
        self.app.progress_var.set(80)

        self.app.save_client()

        showinfo.assert_called_once_with(
            "Saved",
            "Client Sam saved successfully.\nAdherence: 80%",
        )

    def test_reset_clears_client_data_and_display(self):
        self.app.name_var.set("Sam")
        self.app.age_var.set(35)
        self.app.weight_var.set(70)
        self.app.program_var.set("Muscle Gain (MG)")
        self.app.progress_var.set(80)

        self.app.reset()

        self.assertEqual(self.app.name_var.get(), "")
        self.assertEqual(self.app.age_var.get(), 0)
        self.assertEqual(self.app.weight_var.get(), 0)
        self.assertEqual(self.app.program_var.get(), "")
        self.assertEqual(self.app.progress_var.get(), 0)
        self.app.workout_text.insert.assert_called_once_with("end", "")
        self.app.diet_text.insert.assert_called_once_with("end", "")
        self.app.calorie_label.config.assert_called_once_with(
            text="Estimated Calories: --"
        )


if __name__ == "__main__":
    unittest.main()
