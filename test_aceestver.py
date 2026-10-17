import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

import Aceestver


class DummyWidget:
    def __init__(self, *args, **kwargs):
        self.pack = MagicMock()
        self.config = MagicMock()
        self.bind = MagicMock()


class TestACEestApp(unittest.TestCase):

    @patch("Aceestver.tk.StringVar", return_value=MagicMock())
    @patch("Aceestver.ttk.Combobox", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.LabelFrame", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.Label", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.Frame", side_effect=lambda *args, **kwargs: DummyWidget())
    def test_constructor_sets_window_and_program_data(self, *_):
        root = MagicMock()

        app = Aceestver.ACEestApp(root)

        root.title.assert_called_once_with("ACEest Fitness and Gym")
        root.geometry.assert_called_once_with("1100x750")
        root.configure.assert_called_once_with(bg="#1a1a1a")

        self.assertEqual(
            set(app.programs.keys()),
            {"Fat Loss (FL)", "Muscle Gain (MG)", "Beginner (BG)"},
        )
        self.assertIn("workout", app.programs["Fat Loss (FL)"])
        self.assertIn("diet", app.programs["Muscle Gain (MG)"])
        self.assertIn("color", app.programs["Beginner (BG)"])

    @patch("Aceestver.tk.StringVar", return_value=MagicMock())
    @patch("Aceestver.ttk.Combobox", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.LabelFrame", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.Label", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.Frame", side_effect=lambda *args, **kwargs: DummyWidget())
    def test_update_display_updates_workout_and_diet_labels(self, *_):
        root = MagicMock()
        app = Aceestver.ACEestApp(root)

        app.prog_var.get.return_value = "Muscle Gain (MG)"

        app.update_display(None)

        app.work_label.config.assert_called_once_with(
            text=app.programs["Muscle Gain (MG)"]["workout"],
            fg=app.programs["Muscle Gain (MG)"]["color"],
        )
        app.diet_label.config.assert_called_once_with(
            text=app.programs["Muscle Gain (MG)"]["diet"]
        )

    @patch("Aceestver.tk.StringVar", return_value=MagicMock())
    @patch("Aceestver.ttk.Combobox", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.LabelFrame", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.Label", side_effect=lambda *args, **kwargs: DummyWidget())
    @patch("Aceestver.tk.Frame", side_effect=lambda *args, **kwargs: DummyWidget())
    def test_combobox_is_bound_to_update_display(self, *_):
        root = MagicMock()
        app = Aceestver.ACEestApp(root)

        app.prog_menu.bind.assert_called_once_with(
            "<<ComboboxSelected>>", app.update_display
        )


if __name__ == "__main__":
    unittest.main()
