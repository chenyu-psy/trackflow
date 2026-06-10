"""Stimulus helpers for behavior screens.

This module provides small PsychoPy-native stimulus constructors. The helpers
return timed stimulus wrappers with a ``draw()`` method. Built-in stimuli expose
their timing through ``stim.timing`` and editable stimulus settings through
``stim.params``.
"""

from __future__ import annotations

import math
from typing import Any, List, Optional, Sequence, Tuple


Point = Tuple[float, float]

__all__ = [
    "FixationParams",
    "FixationStim",
    "Stimulus",
    "Timing",
    "make_fixation",
    "wrap_stimulus",
]


class Timing:
    """Screen-relative timing for one stimulus.

    Parameters
    ----------
    start : float, optional
        Time in seconds after screen onset when this stimulus should first be
        drawn. ``None`` means draw from the beginning of the screen.
    end : float, optional
        Time in seconds after screen onset when this stimulus should stop being
        drawn. ``None`` means draw until the screen ends.

    Examples
    --------
    >>> timing = Timing(start=0.2, end=1.0)
    >>> timing.start = 0.3
    """

    def __init__(self, start: Optional[float] = None, end: Optional[float] = None) -> None:
        """Create a timing object and validate the initial values."""
        self._start: Optional[float] = None
        self._end: Optional[float] = None
        self.start = start
        self.end = end

    @property
    def start(self) -> Optional[float]:
        """Return the stimulus onset time in seconds, or ``None``."""
        return self._start

    @start.setter
    def start(self, value: Optional[float]) -> None:
        """Set the stimulus onset time and keep timing valid."""
        start = _validate_optional_time(value, "start")
        if start is not None and self._end is not None and self._end < start:
            raise ValueError("start must be less than or equal to end.")
        self._start = start

    @property
    def end(self) -> Optional[float]:
        """Return the stimulus offset time in seconds, or ``None``."""
        return self._end

    @end.setter
    def end(self, value: Optional[float]) -> None:
        """Set the stimulus offset time and keep timing valid."""
        end = _validate_optional_time(value, "end")
        if self._start is not None and end is not None and end < self._start:
            raise ValueError("end must be greater than or equal to start.")
        self._end = end


class Stimulus:
    """Wrap a drawable object with timing, optional params, and a label.

    Parameters
    ----------
    drawable : object
        Any object with a callable ``draw()`` method. This can be a PsychoPy
        stimulus, a built-in ``trackflow.beh`` drawing object, or a user-defined
        stimulus class.
    timing : Timing, optional
        Screen-relative timing object. If omitted, the stimulus is visible for
        the full screen.
    params : object, optional
        Built-in stimulus parameter object, such as ``FixationParams``.
    label : str, optional
        Researcher-facing label for debugging or future data records.

    Examples
    --------
    >>> stim = Stimulus(drawable=psychopy_text, timing=Timing(0.2, 1.0))
    >>> stim.draw()
    """

    def __init__(
        self,
        drawable: Any,
        timing: Optional[Timing] = None,
        params: Optional[Any] = None,
        label: Optional[str] = None,
    ) -> None:
        """Create the wrapper and validate the drawable object.

        Returns
        -------
        None
            Stores the drawable, timing, params, and optional label.

        Raises
        ------
        TypeError
            If ``drawable`` does not provide a callable ``draw()`` method.
        """
        if not hasattr(drawable, "draw") or not callable(drawable.draw):
            raise TypeError("drawable must have a callable draw() method.")
        if timing is not None and not isinstance(timing, Timing):
            raise TypeError("timing must be a Timing object.")

        self.drawable = drawable
        self.timing = timing
        if self.timing is None:
            self.timing = Timing()
        self.params = params
        self.label = label
        if self.label is not None:
            self.label = str(self.label)

    def draw(self) -> None:
        """Draw the wrapped stimulus without flipping the window.

        Returns
        -------
        None
            Delegates drawing to the wrapped object.
        """
        self.drawable.draw()

    def is_visible(self, elapsed: float) -> bool:
        """Return whether this stimulus should be drawn at ``elapsed`` seconds.

        Parameters
        ----------
        elapsed : float
            Seconds since the current screen began.

        Returns
        -------
        bool
            ``True`` when the stimulus is inside its ``start``/``end`` window.
        """
        t = float(elapsed)
        start = 0.0
        if self.timing.start is not None:
            start = self.timing.start

        if t < start:
            return False
        if self.timing.end is not None and t >= self.timing.end:
            return False
        return True

    @property
    def start(self) -> Optional[float]:
        """Return ``timing.start`` for compact inspection."""
        return self.timing.start

    @start.setter
    def start(self, value: Optional[float]) -> None:
        """Set ``timing.start`` for users who prefer direct access."""
        self.timing.start = value

    @property
    def end(self) -> Optional[float]:
        """Return ``timing.end`` for compact inspection."""
        return self.timing.end

    @end.setter
    def end(self, value: Optional[float]) -> None:
        """Set ``timing.end`` for users who prefer direct access."""
        self.timing.end = value


def wrap_stimulus(
    drawable: Any,
    start: Optional[float] = None,
    end: Optional[float] = None,
    label: Optional[str] = None,
) -> Stimulus:
    """Wrap a native PsychoPy or custom stimulus with timing.

    Parameters
    ----------
    drawable : object
        Any object with a callable ``draw()`` method.
    start : float, optional
        Time in seconds after screen onset when the stimulus should appear.
    end : float, optional
        Time in seconds after screen onset when the stimulus should disappear.
    label : str, optional
        Optional researcher-facing label.

    Returns
    -------
    Stimulus
        Timed wrapper around ``drawable``.

    Examples
    --------
    >>> stim = wrap_stimulus(text_stim, start=0.2, end=1.0)
    >>> stim.draw()
    """
    return Stimulus(
        drawable=drawable,
        timing=Timing(start=start, end=end),
        params=None,
        label=label,
    )


def _validate_optional_time(value: Optional[float], name: str) -> Optional[float]:
    """Return a non-negative timing value or ``None``.

    Parameters
    ----------
    value : float, optional
        Timing value supplied by the user.
    name : str
        Field name used in error messages.

    Returns
    -------
    float or None
        Validated timing value.
    """
    if value is None:
        return None
    t = float(value)
    if t < 0:
        raise ValueError(f"{name} must be greater than or equal to 0.")
    return t


def _load_psychopy_visual() -> Any:
    """Import ``psychopy.visual`` only when a stimulus helper needs it.

    Returns
    -------
    module
        The PsychoPy visual module.

    Raises
    ------
    RuntimeError
        If PsychoPy cannot be imported in the current environment.
    """
    try:
        module = __import__("psychopy.visual", fromlist=["visual"])
    except Exception as exc:
        raise RuntimeError("psychopy.visual is required for this stimulus helper.") from exc
    return module


def _validate_size(size: float) -> float:
    """Return ``size`` as a positive float.

    Parameters
    ----------
    size : float
        Full outer diameter of the fixation stimulus in the requested units.

    Returns
    -------
    float
        Positive size value.
    """
    value = float(size)
    if value <= 0:
        raise ValueError("size must be greater than 0.")
    return value


def _validate_pos(pos: Sequence[float]) -> Point:
    """Return ``pos`` as a two-value float tuple.

    Parameters
    ----------
    pos : sequence[float]
        Stimulus center position.

    Returns
    -------
    tuple[float, float]
        Validated ``(x, y)`` position.
    """
    if len(pos) != 2:
        raise ValueError("pos must contain exactly two values.")
    return (float(pos[0]), float(pos[1]))


def _is_hex_color(color: str) -> bool:
    """Return whether ``color`` looks like a HEX color string.

    Parameters
    ----------
    color : str
        Color value supplied by the user.

    Returns
    -------
    bool
        ``True`` for values like ``#000000`` or ``#FFF``.
    """
    text = str(color)
    if not text.startswith("#"):
        return False
    digits = text[1:]
    if len(digits) not in (3, 6):
        return False
    return all(ch in "0123456789abcdefABCDEF" for ch in digits)


def _color_kwargs(color: str) -> dict:
    """Build PsychoPy color keyword arguments for shapes.

    Parameters
    ----------
    color : str
        HEX color or PsychoPy-supported color name.

    Returns
    -------
    dict
        Keyword arguments for ``fillColor`` and ``lineColor``.
    """
    kwargs = {
        "fillColor": str(color),
        "lineColor": str(color),
    }
    if _is_hex_color(str(color)):
        kwargs["colorSpace"] = "hex"
    return kwargs


def _quadrant_vertices(outer_r: float, half_gap: float, sign_x: int, sign_y: int, edges: int) -> List[Point]:
    """Build one transparent-cross quadrant from the old fixation ratios.

    Parameters
    ----------
    outer_r : float
        Outer radius of the fixation disk.
    half_gap : float
        Half width of the transparent cross gap.
    sign_x, sign_y : int
        Signs that mirror the top-right quadrant into the four quadrants.
    edges : int
        Number of points used to approximate the circular arc.

    Returns
    -------
    list[tuple[float, float]]
        Polygon vertices for one quadrant piece.

    Notes
    -----
    The old template drew a full circle and then covered a cross-shaped region
    with the background color. These vertices draw only the visible parts of
    that circle, so the cross gap is genuinely transparent.
    """
    if half_gap >= outer_r:
        raise ValueError("The fixation cross gap must be smaller than the outer radius.")
    n_edges = max(8, int(edges))
    start_angle = math.asin(half_gap / outer_r)
    end_angle = math.acos(half_gap / outer_r)
    lower_x = math.sqrt((outer_r * outer_r) - (half_gap * half_gap))
    left_y = lower_x

    points: List[Point] = [
        (half_gap, half_gap),
        (lower_x, half_gap),
    ]
    for idx in range(n_edges + 1):
        angle = start_angle + ((end_angle - start_angle) * idx / n_edges)
        points.append((outer_r * math.cos(angle), outer_r * math.sin(angle)))
    points.append((half_gap, left_y))

    return [(sign_x * x, sign_y * y) for x, y in points]


class FixationParams:
    """Editable parameters for a fixed-ratio fixation stimulus.

    Parameters
    ----------
    fixation : FixationStim
        Underlying fixation drawing object whose PsychoPy parts should update
        when a parameter changes.

    Examples
    --------
    >>> fix.params.size = 0.6
    >>> fix.params.pos = (1, 0)
    >>> fix.params.color = "red"
    """

    def __init__(self, fixation: "FixationStim") -> None:
        """Connect the parameter object to a fixation drawing object."""
        self._fixation = fixation

    @property
    def size(self) -> float:
        """Return the full outer fixation diameter."""
        return self._fixation.size

    @size.setter
    def size(self, value: float) -> None:
        """Set fixation size and rebuild the fixed-ratio geometry."""
        self._fixation.set_size(value)

    @property
    def pos(self) -> Point:
        """Return the fixation center position."""
        return self._fixation.pos

    @pos.setter
    def pos(self, value: Sequence[float]) -> None:
        """Set fixation position and update every visible part."""
        self._fixation.set_pos(value)

    @property
    def color(self) -> str:
        """Return the visible fixation color."""
        return self._fixation.color

    @color.setter
    def color(self, value: str) -> None:
        """Set fixation color and rebuild parts when color space changes."""
        self._fixation.set_color(value)

    @property
    def units(self) -> str:
        """Return the PsychoPy units used for the fixation geometry."""
        return self._fixation.units

    @units.setter
    def units(self, value: str) -> None:
        """Set PsychoPy units and rebuild the fixation geometry."""
        self._fixation.set_units(value)


class FixationStim:
    """Fixed-ratio Thaler-style fixation stimulus.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window where the fixation will be drawn.
    size : float
        Full outer diameter of the fixation in ``units``. The internal
        proportions are fixed to match the migrated ``trackNeuAct`` fixation.
    pos : sequence[float], optional
        Fixation center position.
    color : str, optional
        HEX color used for all visible fixation parts.
    units : str, optional
        PsychoPy units for the fixation geometry.
    edges : int, optional
        Arc resolution for each quadrant.

    Examples
    --------
    >>> fix = FixationStim(win, size=0.5, color="#FFFFFF")
    >>> fix.draw()

    Notes
    -----
    The transparent cross gap is not drawn. This avoids the historical problem
    where a background-colored mask only looked transparent on matching
    backgrounds.
    """

    def __init__(
        self,
        win: Any,
        size: float = 0.5,
        pos: Sequence[float] = (0.0, 0.0),
        color: str = "#000000",
        units: str = "deg",
        edges: int = 32,
    ) -> None:
        """Create the fixation component stimuli."""
        self.visual = _load_psychopy_visual()
        self.win = win
        self.size = _validate_size(size)
        self.pos = _validate_pos(pos)
        self.color = str(color)
        self.units = str(units)
        self.edges = max(8, int(edges))
        self.quarters: List[Any] = []
        self.center: Any = None
        self.parts: List[Any] = []
        self._build_parts()

    def _build_parts(self) -> None:
        """Build or rebuild the PsychoPy parts for the current parameters.

        Returns
        -------
        None
            Replaces the quadrant and center stimulus objects.
        """
        outer_r = self.size / 2.0
        half_gap = self.size * 0.16
        center_r = self.size * 0.15
        color_kwargs = _color_kwargs(self.color)

        self.quarters = []
        for sign_x, sign_y in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            vertices = _quadrant_vertices(
                outer_r=outer_r,
                half_gap=half_gap,
                sign_x=sign_x,
                sign_y=sign_y,
                edges=self.edges,
            )
            self.quarters.append(
                self.visual.ShapeStim(
                    self.win,
                    vertices=vertices,
                    closeShape=True,
                    units=self.units,
                    pos=self.pos,
                    **color_kwargs,
                )
            )

        self.center = self.visual.Circle(
            self.win,
            radius=center_r,
            units=self.units,
            pos=self.pos,
            edges=max(32, self.edges * 2),
            **color_kwargs,
        )
        self.parts = [*self.quarters, self.center]

    def draw(self) -> None:
        """Draw all fixation parts without flipping the window.

        Returns
        -------
        None
            Draws the fixation components on the current PsychoPy frame.
        """
        for part in self.parts:
            part.draw()

    def set_color(self, color: str) -> None:
        """Update the visible fixation color.

        Parameters
        ----------
        color : str
            HEX color or PsychoPy-supported color name.

        Returns
        -------
        None
            Rebuilds the underlying PsychoPy parts with the correct color
            space. Rebuilding avoids leaving a previous HEX color space active
            when the new color is a PsychoPy color name.
        """
        self.color = str(color)
        self._build_parts()

    def set_pos(self, pos: Sequence[float]) -> None:
        """Update the fixation center position.

        Parameters
        ----------
        pos : sequence[float]
            New ``(x, y)`` position.

        Returns
        -------
        None
            Updates every visible PsychoPy part in place.
        """
        self.pos = _validate_pos(pos)
        for part in self.parts:
            part.pos = self.pos

    def set_size(self, size: float) -> None:
        """Update fixation size and rebuild the fixed-ratio geometry.

        Parameters
        ----------
        size : float
            New full outer diameter in ``units``.

        Returns
        -------
        None
            Rebuilds the underlying PsychoPy parts using the same proportions.
        """
        self.size = _validate_size(size)
        self._build_parts()

    def set_units(self, units: str) -> None:
        """Update PsychoPy units and rebuild the fixation geometry.

        Parameters
        ----------
        units : str
            PsychoPy units name, such as ``"deg"``.

        Returns
        -------
        None
            Rebuilds the underlying PsychoPy parts using the new units.
        """
        self.units = str(units)
        self._build_parts()


def make_fixation(
    win: Any,
    size: float = 0.5,
    pos: Sequence[float] = (0.0, 0.0),
    color: str = "#000000",
    units: str = "deg",
    start: Optional[float] = None,
    end: Optional[float] = None,
    label: Optional[str] = None,
) -> Stimulus:
    """Create a timed fixed-ratio fixation stimulus.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window where the fixation will be drawn.
    size : float, optional
        Full outer diameter of the fixation in ``units``. The default ``0.5``
        preserves the original ``trackNeuAct`` outer diameter in degrees.
    pos : sequence[float], optional
        Center position of the fixation.
    color : str, optional
        HEX color for the visible fixation parts.
    units : str, optional
        PsychoPy units used for the stimulus geometry.
    start : float, optional
        Time in seconds after screen onset when fixation should appear.
        ``None`` means appear from the beginning of the screen.
    end : float, optional
        Time in seconds after screen onset when fixation should disappear.
        ``None`` means remain visible until the screen ends.
    label : str, optional
        Optional researcher-facing label for logs or debugging.

    Returns
    -------
    Stimulus
        Timed wrapper around a ``FixationStim``. The drawing object is stored
        as ``stim.drawable`` and editable settings are exposed through
        ``stim.params``.

    Examples
    --------
    >>> fix = make_fixation(win, size=0.5, color="#FFFFFF", start=0, end=0.5)
    >>> fix.params.size = 0.6
    >>> fix.draw()
    """
    fixation = FixationStim(
        win=win,
        size=size,
        pos=pos,
        color=color,
        units=units,
    )
    stim_label = label
    if stim_label is None:
        stim_label = "fixation"
    return Stimulus(
        drawable=fixation,
        timing=Timing(start=start, end=end),
        params=FixationParams(fixation),
        label=stim_label,
    )
