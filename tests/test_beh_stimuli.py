"""Tests for behavior stimulus helpers."""

import math
import unittest
from unittest import mock

from trackflow import beh
from trackflow.beh import stimuli as beh_stimuli


class FakeShape:
    """Small PsychoPy shape stand-in that records constructor values."""

    def __init__(self, *args, **kwargs):
        """Store shape arguments and initialize draw count."""
        self.args = args
        self.kwargs = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.fillColor = kwargs.get("fillColor")
        self.lineColor = kwargs.get("lineColor")
        self.color = kwargs.get("color")
        self.colorSpace = kwargs.get("colorSpace")
        self.pos = kwargs.get("pos")
        self.draw_calls = 0

    def draw(self):
        """Record one draw call."""
        self.draw_calls += 1


class FakeVisual:
    """Fake PsychoPy visual module for fixation tests."""

    TextStim = FakeShape
    ImageStim = FakeShape
    Rect = FakeShape
    ShapeStim = FakeShape
    Circle = FakeShape
    Line = FakeShape


class BehaviorStimuliTests(unittest.TestCase):
    """Check behavior stimulus construction without opening PsychoPy."""

    def test_import_exposes_behavior_module(self):
        """The top-level behavior package should expose stimulus namespace."""
        self.assertTrue(hasattr(beh, "stimuli"))
        self.assertTrue(hasattr(beh.stimuli, "make_fixation"))
        self.assertTrue(hasattr(beh.stimuli, "make_text"))
        self.assertTrue(hasattr(beh.stimuli, "make_image"))
        self.assertTrue(hasattr(beh.stimuli, "make_rect"))
        self.assertTrue(hasattr(beh.stimuli, "make_circle"))
        self.assertTrue(hasattr(beh.stimuli, "make_line"))
        self.assertTrue(hasattr(beh.stimuli, "FixationStim"))
        self.assertTrue(hasattr(beh.stimuli, "Timing"))
        self.assertTrue(hasattr(beh.stimuli, "Stimulus"))
        self.assertTrue(hasattr(beh.stimuli, "wrap_stimulus"))
        self.assertFalse(hasattr(beh, "make_fixation"))
        self.assertFalse(hasattr(beh, "make_text"))

    def test_stimulus_wraps_drawable_with_timing(self):
        """Timed stimuli should accept any object with ``draw()``."""
        obj = FakeShape()
        stim = beh.stimuli.wrap_stimulus(drawable=obj, start=0.2, end=1.0, label="target")

        self.assertEqual(stim.timing.start, 0.2)
        self.assertEqual(stim.timing.end, 1.0)
        self.assertEqual(stim.label, "target")
        self.assertFalse(stim.is_visible(0.1))
        self.assertTrue(stim.is_visible(0.2))
        self.assertTrue(stim.is_visible(0.9))
        self.assertFalse(stim.is_visible(1.0))

        stim.draw()
        self.assertEqual(obj.draw_calls, 1)

    def test_stimulus_defaults_are_full_screen(self):
        """Missing start/end should mean visible for the full screen."""
        stim = beh.stimuli.wrap_stimulus(drawable=FakeShape())

        self.assertIsNone(stim.timing.start)
        self.assertIsNone(stim.timing.end)
        self.assertTrue(stim.is_visible(0.0))
        self.assertTrue(stim.is_visible(10.0))

    def test_make_fixation_uses_trackneuact_ratios(self):
        """Fixation geometry should preserve the current template proportions."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            stim = beh.stimuli.make_fixation("win", size=0.5, color="#FFFFFF", start=0.1, end=0.6)

        self.assertIsInstance(stim, beh.stimuli.Stimulus)
        self.assertEqual(stim.label, "fixation")
        self.assertEqual(stim.timing.start, 0.1)
        self.assertEqual(stim.timing.end, 0.6)

        fix = stim.drawable
        self.assertIs(stim.params._fixation, fix)
        self.assertEqual(len(fix.quarters), 4)
        self.assertEqual(len(fix.parts), 5)
        self.assertAlmostEqual(fix.center.kwargs["radius"], 0.075)

        first_vertices = fix.quarters[0].kwargs["vertices"]
        self.assertAlmostEqual(first_vertices[0][0], 0.08)
        self.assertAlmostEqual(first_vertices[0][1], 0.08)
        self.assertAlmostEqual(first_vertices[1][1], 0.08)
        self.assertAlmostEqual(math.hypot(*first_vertices[1]), 0.25)

    def test_make_fixation_allows_explicit_label(self):
        """Explicit fixation labels should override the default type label."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            stim = beh.stimuli.make_fixation("win", label="cue_fix")

        self.assertEqual(stim.label, "cue_fix")

    def test_simple_helpers_forward_psychopy_kwargs_and_timing(self):
        """Simple helpers should forward extra PsychoPy constructor options."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            text = beh.stimuli.make_text(
                "win",
                "Ready",
                height=0.12,
                wrapWidth=1.4,
                start=0.1,
                end=0.8,
            )
            image = beh.stimuli.make_image("win", "face.png", size=(4, 3), interpolate=True, label="sample")
            rect = beh.stimuli.make_rect("win", width=1.5, height=0.75, opacity=0.5, lineWidth=2)
            circle = beh.stimuli.make_circle("win", radius=0.75, edges=64)
            line = beh.stimuli.make_line("win", (-1, 0), (1, 0), lineWidth=4)

        self.assertIsInstance(text, beh.stimuli.Stimulus)
        self.assertEqual(text.label, "text")
        self.assertEqual(text.timing.start, 0.1)
        self.assertEqual(text.timing.end, 0.8)
        self.assertEqual(text.drawable.kwargs["text"], "Ready")
        self.assertEqual(text.drawable.kwargs["height"], 0.12)
        self.assertEqual(text.drawable.kwargs["wrapWidth"], 1.4)

        self.assertEqual(image.label, "sample")
        self.assertEqual(image.drawable.kwargs["image"], "face.png")
        self.assertEqual(image.drawable.kwargs["size"], (4, 3))
        self.assertTrue(image.drawable.kwargs["interpolate"])

        self.assertEqual(rect.label, "rect")
        self.assertEqual(rect.drawable.kwargs["width"], 1.5)
        self.assertEqual(rect.drawable.kwargs["height"], 0.75)
        self.assertEqual(rect.drawable.kwargs["opacity"], 0.5)
        self.assertEqual(rect.drawable.kwargs["lineWidth"], 2)

        self.assertEqual(circle.label, "circle")
        self.assertEqual(circle.drawable.kwargs["radius"], 0.75)
        self.assertEqual(circle.drawable.kwargs["edges"], 64)

        self.assertEqual(line.label, "line")
        self.assertEqual(line.drawable.kwargs["start"], (-1.0, 0.0))
        self.assertEqual(line.drawable.kwargs["end"], (1.0, 0.0))
        self.assertEqual(line.drawable.kwargs["lineWidth"], 4)

    def test_simple_helper_params_update_core_fields(self):
        """Editable params should update the underlying PsychoPy-like object."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            text = beh.stimuli.make_text("win", "Ready", pos=(0, 0), color="#FFFFFF", height=0.1, units="deg")
            image = beh.stimuli.make_image("win", "old.png", pos=(0, 0), size=(2, 2), units="pix")
            rect = beh.stimuli.make_rect("win", width=1.0, height=0.5, pos=(0, 0), color="#FFFFFF")
            circle = beh.stimuli.make_circle("win", radius=0.5, pos=(0, 0), color="#FFFFFF")
            line = beh.stimuli.make_line("win", (0, 0), (1, 1), color="#FFFFFF")

        text.params.text = "Go"
        text.params.pos = (1, -1)
        text.params.color = "red"
        text.params.height = 0.2
        text.params.units = "pix"
        self.assertEqual(text.drawable.text, "Go")
        self.assertEqual(text.drawable.pos, (1.0, -1.0))
        self.assertEqual(text.drawable.color, "red")
        self.assertIsNone(text.drawable.colorSpace)
        self.assertEqual(text.drawable.height, 0.2)
        self.assertEqual(text.drawable.units, "pix")

        image.params.image = "new.png"
        image.params.pos = (2, 3)
        image.params.size = (3, 4)
        image.params.units = "deg"
        self.assertEqual(image.drawable.image, "new.png")
        self.assertEqual(image.drawable.pos, (2.0, 3.0))
        self.assertEqual(image.drawable.size, (3, 4))
        self.assertEqual(image.drawable.units, "deg")

        rect.params.width = 2.0
        rect.params.height = 1.0
        rect.params.pos = (-1, 1)
        rect.params.color = "blue"
        rect.params.units = "pix"
        self.assertEqual(rect.drawable.width, 2.0)
        self.assertEqual(rect.drawable.height, 1.0)
        self.assertEqual(rect.drawable.pos, (-1.0, 1.0))
        self.assertEqual(rect.drawable.fillColor, "blue")
        self.assertEqual(rect.drawable.lineColor, "blue")
        self.assertIsNone(rect.drawable.colorSpace)
        self.assertEqual(rect.drawable.units, "pix")

        circle.params.radius = 0.25
        circle.params.pos = (1, 2)
        circle.params.color = "#000000"
        circle.params.units = "height"
        self.assertEqual(circle.drawable.radius, 0.25)
        self.assertEqual(circle.drawable.pos, (1.0, 2.0))
        self.assertEqual(circle.drawable.fillColor, "#000000")
        self.assertEqual(circle.drawable.lineColor, "#000000")
        self.assertEqual(circle.drawable.colorSpace, "hex")
        self.assertEqual(circle.drawable.units, "height")

        line.params.start_pos = (-2, 0)
        line.params.end_pos = (2, 0)
        line.params.color = "green"
        line.params.units = "norm"
        self.assertEqual(line.drawable.start, (-2.0, 0.0))
        self.assertEqual(line.drawable.end, (2.0, 0.0))
        self.assertEqual(line.drawable.lineColor, "green")
        self.assertIsNone(line.drawable.colorSpace)
        self.assertEqual(line.drawable.units, "norm")

    def test_simple_helpers_support_color_space_passthrough(self):
        """Explicit colorSpace kwargs should override HEX defaults."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            text = beh.stimuli.make_text("win", "Ready", color="#FFFFFF", colorSpace="rgb")
            rect = beh.stimuli.make_rect("win", color="#FFFFFF", colorSpace="rgb")
            line = beh.stimuli.make_line("win", (0, 0), (1, 1), color="#FFFFFF", colorSpace="rgb")

        self.assertEqual(text.drawable.kwargs["colorSpace"], "rgb")
        self.assertEqual(rect.drawable.kwargs["colorSpace"], "rgb")
        self.assertEqual(line.drawable.kwargs["colorSpace"], "rgb")

    def test_simple_helpers_reject_invalid_geometry(self):
        """Built-in helper geometry should fail early when invalid."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            with self.assertRaises(ValueError):
                beh.stimuli.make_rect("win", width=0)
            with self.assertRaises(ValueError):
                beh.stimuli.make_rect("win", height=0)
            with self.assertRaises(ValueError):
                beh.stimuli.make_circle("win", radius=0)
            with self.assertRaises(ValueError):
                beh.stimuli.make_rect("win", pos=(0, 1, 2))
            with self.assertRaises(ValueError):
                beh.stimuli.make_line("win", (0,), (1, 1))

    def test_fixation_draws_and_updates_color(self):
        """The composite fixation should draw and recolor every visible part."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            stim = beh.stimuli.make_fixation("win", size=0.5, color="#FFFFFF")

        fix = stim.drawable
        stim.draw()
        self.assertTrue(all(part.draw_calls == 1 for part in fix.parts))

        stim.params.color = "#FF0000"
        self.assertTrue(all(part.fillColor == "#FF0000" for part in fix.parts))
        self.assertTrue(all(part.lineColor == "#FF0000" for part in fix.parts))
        self.assertTrue(all(part.kwargs["colorSpace"] == "hex" for part in fix.parts))

        stim.params.color = "red"
        self.assertTrue(all(part.fillColor == "red" for part in fix.parts))
        self.assertTrue(all(part.lineColor == "red" for part in fix.parts))
        self.assertTrue(all("colorSpace" not in part.kwargs for part in fix.parts))

    def test_fixation_params_update_size_and_pos(self):
        """Editable fixation params should update the underlying PsychoPy parts."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            stim = beh.stimuli.make_fixation("win", size=0.5, pos=(0, 0), color="#FFFFFF")

        fix = stim.drawable
        stim.params.size = 0.6
        self.assertEqual(stim.params.size, 0.6)
        self.assertAlmostEqual(fix.center.kwargs["radius"], 0.09)
        first_vertices = fix.quarters[0].kwargs["vertices"]
        self.assertAlmostEqual(first_vertices[0][0], 0.096)
        self.assertAlmostEqual(first_vertices[0][1], 0.096)

        stim.params.pos = (1, -1)
        self.assertEqual(stim.params.pos, (1.0, -1.0))
        self.assertTrue(all(part.pos == (1.0, -1.0) for part in fix.parts))

    def test_stimulus_rejects_invalid_input(self):
        """Stimuli should fail early when timing or drawability is invalid."""
        with self.assertRaises(TypeError):
            beh.stimuli.wrap_stimulus(drawable=object())

        with self.assertRaises(ValueError):
            beh.stimuli.wrap_stimulus(drawable=FakeShape(), start=-0.1)

        with self.assertRaises(ValueError):
            beh.stimuli.wrap_stimulus(drawable=FakeShape(), start=1.0, end=0.5)

        timing = beh.stimuli.Timing(start=0.2, end=1.0)
        with self.assertRaises(ValueError):
            timing.end = 0.1
        with self.assertRaises(ValueError):
            timing.start = 1.1

    def test_make_fixation_rejects_invalid_size(self):
        """Fixation size should be positive."""
        with mock.patch.object(beh_stimuli, "_load_psychopy_visual", return_value=FakeVisual):
            with self.assertRaises(ValueError):
                beh.stimuli.make_fixation("win", size=0)


if __name__ == "__main__":
    unittest.main()
