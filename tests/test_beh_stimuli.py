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
        self.fillColor = kwargs.get("fillColor")
        self.lineColor = kwargs.get("lineColor")
        self.colorSpace = kwargs.get("colorSpace")
        self.pos = kwargs.get("pos")
        self.draw_calls = 0

    def draw(self):
        """Record one draw call."""
        self.draw_calls += 1


class FakeVisual:
    """Fake PsychoPy visual module for fixation tests."""

    ShapeStim = FakeShape
    Circle = FakeShape


class BehaviorStimuliTests(unittest.TestCase):
    """Check behavior stimulus construction without opening PsychoPy."""

    def test_import_exposes_behavior_module(self):
        """The top-level behavior package should expose stimulus namespace."""
        self.assertTrue(hasattr(beh, "stimuli"))
        self.assertTrue(hasattr(beh.stimuli, "make_fixation"))
        self.assertTrue(hasattr(beh.stimuli, "FixationStim"))
        self.assertTrue(hasattr(beh.stimuli, "Timing"))
        self.assertTrue(hasattr(beh.stimuli, "Stimulus"))
        self.assertTrue(hasattr(beh.stimuli, "wrap_stimulus"))
        self.assertFalse(hasattr(beh, "make_fixation"))

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
