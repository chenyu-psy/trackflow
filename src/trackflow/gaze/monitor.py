"""Realtime gaze monitoring helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence, Tuple

from .runtime import (
    _has_gaze_xy,
    _load_psychopy_module,
    _should_use_dark_text,
    _wait_for_continue,
)


@dataclass
class GazeBreakError(Exception):
    """Raised when gaze leaves the allowed fixation radius."""

    message: str
    x: float
    y: float
    left: Any = None
    right: Any = None

    def __post_init__(self) -> None:
        """Initialize Exception state after dataclass field assignment."""
        Exception.__init__(self, self.message)

    @property
    def pos(self) -> Tuple[float, float]:
        """Return the screen-centered gaze offset.

        Returns
        -------
        tuple[float, float]
            ``(x, y)`` in pixels relative to screen center.
        """
        return self.x, self.y


class GazeMonitor:
    """Realtime gaze monitoring helper.

    The monitor checks gaze against a fixation radius but does not decide
    whether a trial should be retried, excluded, or saved. Those decisions
    belong in the experiment script or behavior helpers.
    """

    def __init__(
        self,
        tracker: Any,
        win: Any,
        monitor: Any = None,
        max_dist_deg: Optional[float] = None,
        pix_radius: Optional[float] = None,
        fixation: Any = None,
        enabled: bool = True,
        time_func: Optional[Callable[[], float]] = None,
        sleep_func: Optional[Callable[[float], None]] = None,
    ):
        """Create a realtime gaze monitor.

        Parameters
        ----------
        tracker : object
            Tracker wrapper returned by `setup_tracker`.
        win : psychopy.visual.Window
            Window used for size and feedback drawing.
        monitor : psychopy.monitors.Monitor | None, optional
            Monitor used to convert visual degrees to pixels when
            ``pix_radius`` is not provided.
        max_dist_deg : float | None, optional
            Allowed fixation radius in visual degrees. Defaults to
            ``tracker.cfg.max_dist_deg`` when available, otherwise 1.25.
        pix_radius : float | None, optional
            Precomputed radius in pixels. Use this in tests or nonstandard
            display setups.
        fixation : object | None, optional
            Optional fixation stimulus with ``draw`` or ``set_color`` methods.
        enabled : bool, optional
            Whether gaze monitoring can run.
        time_func : callable | None, optional
            Test hook returning current time in seconds.
        sleep_func : callable | None, optional
            Test hook used instead of PsychoPy ``core.wait``.
        """
        tracker_cfg = getattr(tracker, "cfg", None)
        if max_dist_deg is None:
            max_dist_deg = getattr(tracker_cfg, "max_dist_deg", 1.25)

        self.tracker = tracker
        self.win = win
        self.monitor = monitor
        self.max_dist_deg = float(max_dist_deg)
        self.pix_radius = float(pix_radius) if pix_radius is not None else self._deg_to_pix(self.max_dist_deg)
        self.fixation = fixation
        self.enabled = bool(enabled)
        self.active = False
        self.time_func = time_func
        self.sleep_func = sleep_func
        self.rejection_streak = 0
        self.last_error: Optional[GazeBreakError] = None

    def _deg_to_pix(self, value: float) -> float:
        """Convert degrees to pixels using PsychoPy monitor tools.

        Parameters
        ----------
        value : float
            Visual degrees.

        Returns
        -------
        float
            Pixel value.

        Raises
        ------
        ValueError
            If no monitor is available for conversion.
        """
        if self.monitor is None:
            raise ValueError("Either monitor or pix_radius must be provided.")
        tools = _load_psychopy_module("tools")
        return float(tools.monitorunittools.deg2pix(value, self.monitor))

    def _time(self) -> float:
        """Return current time in seconds.

        Returns
        -------
        float
            Current time from the test hook or PsychoPy.
        """
        if self.time_func is not None:
            return float(self.time_func())
        core = _load_psychopy_module("core")
        return float(core.getTime())

    def _sleep(self, duration: float) -> None:
        """Wait for a short duration.

        Parameters
        ----------
        duration : float
            Seconds to wait.

        Returns
        -------
        None
            Uses the test hook or PsychoPy.
        """
        if self.sleep_func is not None:
            self.sleep_func(float(duration))
            return
        core = _load_psychopy_module("core")
        core.wait(float(duration))

    def start_tracking(self) -> None:
        """Start realtime fixation tracking.

        Returns
        -------
        None
            Enables checks when the monitor and tracker are available. This
            does not start EyeLink recording.
        """
        self.active = self.enabled and self.tracker is not None

    def stop_tracking(self) -> None:
        """Stop realtime fixation tracking.

        Returns
        -------
        None
            Disables checks. This does not stop EyeLink recording.
        """
        self.active = False

    def check_fixation(self) -> bool:
        """Check the newest gaze sample against the fixation radius.

        Returns
        -------
        bool
            ``False`` when monitoring is inactive or the sample is acceptable.

        Raises
        ------
        GazeBreakError
            If gaze is farther than the allowed radius from screen center.
        """
        if not self.active:
            return False
        if self.tracker is None or not hasattr(self.tracker, "gaze_data_both"):
            return False

        left, right = self.tracker.gaze_data_both
        has_left = _has_gaze_xy(left)
        has_right = _has_gaze_xy(right)
        if has_left and has_right:
            x = (float(left[0]) + float(right[0])) / 2.0
            y = (float(left[1]) + float(right[1])) / 2.0
        elif has_left:
            x, y = float(left[0]), float(left[1])
        elif has_right:
            x, y = float(right[0]), float(right[1])
        else:
            return False

        win_width, win_height = self.win.size
        x -= float(win_width) / 2.0
        y -= float(win_height) / 2.0
        dist = ((x * x) + (y * y)) ** 0.5
        if dist > self.pix_radius:
            if hasattr(self.tracker, "stop_recording"):
                self.tracker.stop_recording()
            error = GazeBreakError(f"Eye movement detected at {x},{y}", x=x, y=y, left=left, right=right)
            self.last_error = error
            self.rejection_streak += 1
            raise error
        return False

    def wait(self, duration: float, sample_interval: float = 0.01) -> bool:
        """Wait for a fixed duration while checking gaze.

        Parameters
        ----------
        duration : float
            Seconds to wait.
        sample_interval : float, optional
            Seconds between gaze checks.

        Returns
        -------
        bool
            ``False`` when no gaze break occurs.

        Raises
        ------
        GazeBreakError
            If any sample breaks fixation.
        """
        if not self.active:
            self._sleep(duration)
            return False
        start_time = self._time()
        while self._time() < start_time + float(duration):
            self.check_fixation()
            self._sleep(sample_interval)
        return False

    def show_feedback(
        self,
        error: Optional[GazeBreakError] = None,
        continue_keys: Sequence[str] = ("space",),
    ) -> None:
        """Show gaze-break feedback and wait for a continue response.

        Parameters
        ----------
        error : GazeBreakError | None, optional
            Gaze error to display. Defaults to the most recent error.
        continue_keys : sequence[str], optional
            PsychoPy key names plus optional supported mouse tokens.

        Returns
        -------
        None
            Draws the feedback page and waits for a response.
        """
        err = error or self.last_error
        if err is None:
            return
        tracker_cfg = getattr(self.tracker, "cfg", None)
        bg_color = getattr(tracker_cfg, "bg_color", getattr(self.win, "color", "#FFFFFF"))
        text_color = "#000000" if _should_use_dark_text(bg_color) else "#FFFFFF"
        visual = _load_psychopy_module("visual")
        visual.Rect(self.win, units="norm", width=2, height=2, fillColor=bg_color, colorSpace="hex").draw()
        visual.TextStim(
            win=self.win,
            text=(
                "Eye position was outside the center area.\n\n"
                "Please look at the center.\n\n"
                "Press the space bar to continue."
            ),
            pos=[0, 1],
            color=text_color,
            colorSpace="hex",
        ).draw()
        if self.fixation is not None:
            if hasattr(self.fixation, "set_color"):
                self.fixation.set_color("#000000")
            if hasattr(self.fixation, "draw"):
                self.fixation.draw()
        visual.Circle(
            win=self.win,
            radius=8,
            pos=err.pos,
            fillColor="#FF0000",
            colorSpace="hex",
            units="pix",
        ).draw()
        self.win.flip()
        _wait_for_continue(self.win, continue_keys)

    def get_rejection_streak(self) -> int:
        """Return the number of consecutive gaze rejection events.

        Returns
        -------
        int
            Current count of gaze breaks since the last reset.
        """
        return int(self.rejection_streak)

    def reset_rejections(self) -> None:
        """Reset consecutive gaze rejection state.

        Returns
        -------
        None
            Clears the rejection streak and most recent error.
        """
        self.rejection_streak = 0
        self.last_error = None
