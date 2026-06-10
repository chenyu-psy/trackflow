"""PsychoPy-backed EyeLink calibration display helpers."""

from __future__ import annotations

import array
import string
import warnings
from typing import Any, List, Tuple

from .runtime import _load_psychopy_module, _load_pylink, _should_use_dark_text


class EyeLinkDisplay:
    """Small PsychoPy display adapter for pylink calibration graphics.

    This class is adapted from `trackNeuAct/src/utils/eyelink_display.py`.
    It is intentionally minimal here: pylink calls these methods during
    calibration, and they draw directly to the PsychoPy window.
    """

    def __init__(self, win: Any, tracker: Any):
        """Create a calibration display adapter.

        Parameters
        ----------
        win : psychopy.visual.Window
            PsychoPy window used by the experiment.
        tracker : pylink.EyeLink
            Connected EyeLink tracker handle.

        Returns
        -------
        None
            Stores display state for pylink callbacks.
        """
        self.win = win
        self.tracker = tracker
        self._pylink = _load_pylink()
        self._event = _load_psychopy_module("event")
        self._visual = _load_psychopy_module("visual")

    def setup_cal_display(self) -> None:
        """Clear the calibration display.

        Returns
        -------
        None
            Flips the PsychoPy window.
        """
        self.win.flip()

    def exit_cal_display(self) -> None:
        """Close the calibration display.

        Returns
        -------
        None
            Flips the PsychoPy window.
        """
        self.win.flip()

    def clear_cal_display(self) -> None:
        """Clear the calibration target display.

        Returns
        -------
        None
            Flips the PsychoPy window.
        """
        self.win.flip()

    def erase_cal_target(self) -> None:
        """Erase the current calibration target.

        Returns
        -------
        None
            Flips the PsychoPy window.
        """
        self.win.flip()

    def draw_cal_target(self, x: float, y: float) -> None:
        """Draw one calibration target.

        Parameters
        ----------
        x : float
            Target x coordinate in pixels.
        y : float
            Target y coordinate in pixels.

        Returns
        -------
        None
            Draws the target and flips the window.
        """
        self._visual.Circle(
            self.win,
            units="pix",
            radius=18,
            pos=(x - self.win.size[0] / 2, self.win.size[1] / 2 - y),
            lineColor="#000000",
            fillColor="#FFFFFF",
            colorSpace="hex",
        ).draw()
        self._visual.Circle(
            self.win,
            units="pix",
            radius=6,
            pos=(x - self.win.size[0] / 2, self.win.size[1] / 2 - y),
            lineColor="#000000",
            fillColor="#000000",
            colorSpace="hex",
        ).draw()
        self.win.flip()

    def get_input_key(self) -> List[Any]:
        """Return keys from PsychoPy in pylink format.

        Returns
        -------
        list
            Empty list when no key is available. This keeps pylink's setup
            loop polling without blocking the PsychoPy window.
        """
        return []

    def play_beep(self, beep_id: int) -> None:
        """Ignore EyeLink calibration beeps.

        Parameters
        ----------
        beep_id : int
            pylink beep code.

        Returns
        -------
        None
            Sound feedback is intentionally left to EyeLink defaults.
        """
        return None


def _make_eyelink_display(win: Any, tracker: Any) -> Any:
    """Create the full pylink custom display at EyeLink runtime.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window used for EyeLink setup graphics.
    tracker : pylink.EyeLink
        Connected EyeLink tracker handle.

    Returns
    -------
    pylink.EyeLinkCustomDisplay
        Display object adapted from `trackNeuAct`.

    Notes
    -----
    The subclass is defined inside this function so importing `trackflow.gaze`
    does not require pylink or PsychoPy.
    """
    pylink = _load_pylink()
    event = _load_psychopy_module("event")
    visual = _load_psychopy_module("visual")
    monitor_tools = __import__("psychopy.tools.monitorunittools", fromlist=["convertToPix"])
    convert_to_pix = monitor_tools.convertToPix

    class _RuntimeEyeLinkDisplay(pylink.EyeLinkCustomDisplay):
        """Psychopy-backed custom display for the EyeLink pylink API."""

        def __init__(self, window: Any, tracker_handle: Any):
            """Create the display object used by pylink setup routines."""
            pylink.EyeLinkCustomDisplay.__init__(self)
            self.window = window
            self.window_adj = [value / 2 for value in self.window.size]
            self.tracker = tracker_handle
            self.pal = []
            self.image_buffer = array.array("I")
            self.text_color = "#000000" if _should_use_dark_text(self.window.color) else "#FFFFFF"
            self.colors = {
                pylink.CR_HAIR_COLOR: "#FFFFFF",
                pylink.PUPIL_HAIR_COLOR: "#FFFFFF",
                pylink.PUPIL_BOX_COLOR: "#00FF00",
                pylink.SEARCH_LIMIT_BOX_COLOR: "#FF0000",
                pylink.MOUSE_CURSOR_COLOR: "#FF0000",
            }
            self.keys = {
                "f1": pylink.F1_KEY,
                "f2": pylink.F2_KEY,
                "f3": pylink.F3_KEY,
                "f4": pylink.F4_KEY,
                "f5": pylink.F5_KEY,
                "f6": pylink.F6_KEY,
                "f7": pylink.F7_KEY,
                "f8": pylink.F8_KEY,
                "f9": pylink.F9_KEY,
                "f10": pylink.F10_KEY,
                "pageup": pylink.PAGE_UP,
                "pagedown": pylink.PAGE_DOWN,
                "up": pylink.CURS_UP,
                "down": pylink.CURS_DOWN,
                "left": pylink.CURS_LEFT,
                "right": pylink.CURS_RIGHT,
                "return": pylink.ENTER_KEY,
                "escape": pylink.ESC_KEY,
                "num_add": 43,
                "equal": 43,
                "num_subtract": 45,
                "minus": 45,
                "backspace": ord("\b"),
                "space": ord(" "),
                "tab": ord("\t"),
            }
            self.mouse = event.Mouse(visible=False)
            self.image_title_object = visual.TextStim(
                self.window,
                text="",
                pos=(0, -200),
                height=20,
                units="pix",
                color=self.text_color,
                colorSpace="hex",
            )
            self.cal_target_outer = visual.Circle(
                self.window,
                units="pix",
                radius=18,
                lineColor="#000000",
                fillColor="#FFFFFF",
                colorSpace="hex",
            )
            self.cal_target_inner = visual.Circle(
                self.window,
                units="pix",
                radius=6,
                lineColor="#000000",
                fillColor="#000000",
                colorSpace="hex",
            )

        def setup_cal_display(self) -> None:
            """Prepare the calibration display."""
            visual.TextStim(
                self.window,
                text="C: calibrate, V: Validate, O: output/record, ESC: exit",
                pos=(100, 100),
                units="pix",
            ).draw()
            self.window.flip()

        def exit_cal_display(self) -> None:
            """Clear the calibration display."""
            self.window.flip()

        def record_abort_hide(self) -> None:
            """No-op placeholder required by the pylink interface."""
            return None

        def setup_image_display(self, width: int, height: int) -> None:
            """Prepare the camera image display."""
            event.Mouse(visible=True)
            self.window.flip()

        def image_title(self, title: str) -> None:
            """Update the camera image title text."""
            self.image_title_object.text = title

        def draw_image_line(self, width: int, line: int, totlines: int, buff: Any) -> None:
            """Accumulate image scanlines and draw the full camera image."""
            for item in buff:
                if item >= len(self.pal):
                    self.image_buffer.append(self.pal[-1])
                else:
                    self.image_buffer.append(self.pal[item])
            if line == totlines:
                try:
                    from PIL import Image
                except Exception as exc:
                    raise RuntimeError("Pillow is required for EyeLink camera image display.") from exc
                buffer_value = self.image_buffer.tobytes()
                image = Image.frombytes("RGBX", (width, totlines), buffer_value)
                psychopy_image = visual.ImageStim(self.window, image=image)
                psychopy_image.draw()
                self.draw_cross_hair()
                self.image_title_object.draw()
                self.window.flip()
                self.image_buffer = array.array("I")

        def set_image_palette(self, r: Any, g: Any, b: Any) -> None:
            """Set the RGB palette used to decode camera image scanlines."""
            self.pal = []
            for red, green, blue in zip(r, g, b):
                self.pal.append((blue << 16) | green << 8 | red)

        def exit_image_display(self) -> None:
            """Tear down the camera image display."""
            event.Mouse(visible=False)
            self.window.flip()

        def clear_cal_display(self) -> None:
            """Clear any calibration graphics."""
            self.window.flip()

        def erase_cal_target(self) -> None:
            """Erase a single calibration target."""
            self.window.flip()

        def draw_cal_target(self, x: float, y: float) -> None:
            """Draw a calibration target at tracker pixel coordinates."""
            self.cal_target_outer.pos = (x - self.window_adj[0], y - self.window_adj[1])
            self.cal_target_inner.pos = (x - self.window_adj[0], y - self.window_adj[1])
            self.cal_target_outer.draw()
            self.cal_target_inner.draw()
            self.window.flip()

        def play_beep(self, beepid: int) -> None:
            """Disable optional audio feedback."""
            return None

        def get_input_key(self) -> List[Any]:
            """Collect PsychoPy key events and map them to pylink key codes."""
            keys = []
            for keycode, modifiers in event.getKeys(modifiers=True):
                if keycode in self.keys:
                    key = self.keys[keycode]
                elif keycode in string.ascii_letters:
                    key = ord(keycode)
                else:
                    key = pylink.JUNK_KEY
                mod = 256 if modifiers["alt"] else 0
                keys.append(pylink.KeyInput(key, mod))
            return keys

        def alert_printf(self, msg: str) -> None:
            """Emit a warning without aborting the session."""
            warnings.warn(msg, RuntimeWarning)

        def draw_line(self, x1: float, y1: float, x2: float, y2: float, colorindex: int) -> None:
            """Draw crosshair lines on the camera image overlay."""
            if x1 < 0:
                x1, x2 = x1 + 767, x2 + 767
                y1, y2 = y1 + 639, y2 + 639
            color = self.colors.get(colorindex, "#000000")
            x1, x2 = x1 - 96, x2 - 96
            y1, y2 = (160 - y1 - 80), (160 - y2 - 80)
            visual.Line(
                self.window,
                units="pix",
                lineColor=color,
                colorSpace="hex",
                start=(x1, y1),
                end=(x2, y2),
            ).draw()

        def draw_lozenge(self, x: float, y: float, width: float, height: float, colorindex: int) -> None:
            """Draw an oval on the camera image overlay."""
            color = self.colors.get(colorindex, "#000000")
            x = round(x + (0.5 * width)) - 96
            y = round((160 - y) - (0.5 * height)) - 80
            visual.Circle(
                self.window,
                units="pix",
                lineColor=color,
                colorSpace="hex",
                pos=(x, y),
                size=(width, height),
            ).draw()

        def get_mouse_state(self) -> Tuple[Tuple[float, float], int]:
            """Return mouse position and button state in tracker coordinates."""
            mouse_pos = self.mouse.getPos()
            mouse_pos = convert_to_pix(mouse_pos, [0, 0], self.window.units, self.window)
            mouse_pos = (mouse_pos[0] + 96, (160 - mouse_pos[1]) - 80)
            pressed = self.mouse.getPressed()
            left_pressed = pressed[0] if pressed else 0
            mouse_click = 1 if left_pressed else 0
            return mouse_pos, mouse_click

    return _RuntimeEyeLinkDisplay(win, tracker)

