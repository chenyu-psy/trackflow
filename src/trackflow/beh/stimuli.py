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
    "make_circle",
    "make_fixation",
    "make_image",
    "make_line",
    "make_rect",
    "make_text",
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
) -> Any:
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
    object
        Timed drawable wrapper that can be passed to
        ``timeline.make_screen(...)``.

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


def _line_color_kwargs(color: str) -> dict:
    """Build PsychoPy color keyword arguments for line stimuli."""
    kwargs = {"lineColor": str(color)}
    if _is_hex_color(str(color)):
        kwargs["colorSpace"] = "hex"
    return kwargs


def _merge_stim_kwargs(base: dict, stim_kwargs: dict) -> dict:
    """Return constructor kwargs with explicit user passthrough values applied."""
    kwargs = dict(base)
    kwargs.update(stim_kwargs)
    return kwargs


def _text_stim_kwargs(text: Any, stim_kwargs: dict) -> dict:
    """Return ``TextStim`` constructor kwargs with HEX color handling."""
    kwargs = _merge_stim_kwargs({"text": str(text)}, stim_kwargs)
    if "color" in kwargs and "colorSpace" not in kwargs and _is_hex_color(str(kwargs["color"])):
        kwargs["colorSpace"] = "hex"
    return kwargs


def _set_color_space(drawable: Any, color: str) -> None:
    """Update ``colorSpace`` when a mutable param changes a color."""
    if _is_hex_color(str(color)):
        setattr(drawable, "colorSpace", "hex")
    elif hasattr(drawable, "colorSpace"):
        setattr(drawable, "colorSpace", None)


def _stim_label(label: Optional[str], default: str) -> str:
    """Return an explicit label or the built-in type label."""
    if label is None:
        return default
    return str(label)


def _get_drawable_value(drawable: Any, name: str, default: Any = None) -> Any:
    """Read a value from a PsychoPy-like object or its recorded kwargs."""
    if hasattr(drawable, name):
        return getattr(drawable, name)
    kwargs = getattr(drawable, "kwargs", None)
    if isinstance(kwargs, dict):
        return kwargs.get(name, default)
    return default


class TextParams:
    """Editable core parameters for a built-in text stimulus."""

    def __init__(self, drawable: Any) -> None:
        """Connect the parameter object to a PsychoPy ``TextStim``."""
        self._drawable = drawable

    @property
    def text(self) -> str:
        """Return the text string."""
        return _get_drawable_value(self._drawable, "text")

    @text.setter
    def text(self, value: Any) -> None:
        """Set the text string."""
        setattr(self._drawable, "text", str(value))

    @property
    def pos(self) -> Any:
        """Return the text position."""
        return _get_drawable_value(self._drawable, "pos")

    @pos.setter
    def pos(self, value: Sequence[float]) -> None:
        """Set the text position."""
        setattr(self._drawable, "pos", _validate_pos(value))

    @property
    def color(self) -> Any:
        """Return the text color."""
        return _get_drawable_value(self._drawable, "color")

    @color.setter
    def color(self, value: str) -> None:
        """Set the text color and matching color space."""
        color = str(value)
        setattr(self._drawable, "color", color)
        _set_color_space(self._drawable, color)

    @property
    def height(self) -> Any:
        """Return the text height."""
        return _get_drawable_value(self._drawable, "height")

    @height.setter
    def height(self, value: float) -> None:
        """Set the text height."""
        setattr(self._drawable, "height", float(value))

    @property
    def units(self) -> Any:
        """Return the text units."""
        return _get_drawable_value(self._drawable, "units")

    @units.setter
    def units(self, value: str) -> None:
        """Set the text units."""
        setattr(self._drawable, "units", str(value))


class ImageParams:
    """Editable core parameters for a built-in image stimulus."""

    def __init__(self, drawable: Any) -> None:
        """Connect the parameter object to a PsychoPy ``ImageStim``."""
        self._drawable = drawable

    @property
    def image(self) -> Any:
        """Return the image source."""
        return _get_drawable_value(self._drawable, "image")

    @image.setter
    def image(self, value: Any) -> None:
        """Set the image source."""
        setattr(self._drawable, "image", value)

    @property
    def pos(self) -> Any:
        """Return the image position."""
        return _get_drawable_value(self._drawable, "pos")

    @pos.setter
    def pos(self, value: Sequence[float]) -> None:
        """Set the image position."""
        setattr(self._drawable, "pos", _validate_pos(value))

    @property
    def size(self) -> Any:
        """Return the image size."""
        return _get_drawable_value(self._drawable, "size")

    @size.setter
    def size(self, value: Any) -> None:
        """Set the image size."""
        setattr(self._drawable, "size", value)

    @property
    def units(self) -> Any:
        """Return the image units."""
        return _get_drawable_value(self._drawable, "units")

    @units.setter
    def units(self, value: str) -> None:
        """Set the image units."""
        setattr(self._drawable, "units", str(value))


class RectParams:
    """Editable core parameters for a built-in rect stimulus."""

    def __init__(self, drawable: Any) -> None:
        """Connect the parameter object to a PsychoPy ``Rect``."""
        self._drawable = drawable

    @property
    def width(self) -> float:
        """Return the rect width."""
        return _get_drawable_value(self._drawable, "width")

    @width.setter
    def width(self, value: float) -> None:
        """Set the rect width."""
        setattr(self._drawable, "width", _validate_size(value))

    @property
    def height(self) -> float:
        """Return the rect height."""
        return _get_drawable_value(self._drawable, "height")

    @height.setter
    def height(self, value: float) -> None:
        """Set the rect height."""
        setattr(self._drawable, "height", _validate_size(value))

    @property
    def pos(self) -> Any:
        """Return the rect position."""
        return _get_drawable_value(self._drawable, "pos")

    @pos.setter
    def pos(self, value: Sequence[float]) -> None:
        """Set the rect position."""
        setattr(self._drawable, "pos", _validate_pos(value))

    @property
    def color(self) -> Any:
        """Return the rect fill color."""
        return _get_drawable_value(self._drawable, "fillColor")

    @color.setter
    def color(self, value: str) -> None:
        """Set rect fill and line color."""
        color = str(value)
        setattr(self._drawable, "fillColor", color)
        setattr(self._drawable, "lineColor", color)
        _set_color_space(self._drawable, color)

    @property
    def units(self) -> Any:
        """Return the rect units."""
        return _get_drawable_value(self._drawable, "units")

    @units.setter
    def units(self, value: str) -> None:
        """Set the rect units."""
        setattr(self._drawable, "units", str(value))


class CircleParams:
    """Editable core parameters for a built-in circle stimulus."""

    def __init__(self, drawable: Any) -> None:
        """Connect the parameter object to a PsychoPy ``Circle``."""
        self._drawable = drawable

    @property
    def radius(self) -> float:
        """Return the circle radius."""
        return _get_drawable_value(self._drawable, "radius")

    @radius.setter
    def radius(self, value: float) -> None:
        """Set the circle radius."""
        radius = _validate_size(value)
        setattr(self._drawable, "radius", radius)

    @property
    def pos(self) -> Any:
        """Return the circle position."""
        return _get_drawable_value(self._drawable, "pos")

    @pos.setter
    def pos(self, value: Sequence[float]) -> None:
        """Set the circle position."""
        setattr(self._drawable, "pos", _validate_pos(value))

    @property
    def color(self) -> Any:
        """Return the circle fill color."""
        return _get_drawable_value(self._drawable, "fillColor")

    @color.setter
    def color(self, value: str) -> None:
        """Set circle fill and line color."""
        color = str(value)
        setattr(self._drawable, "fillColor", color)
        setattr(self._drawable, "lineColor", color)
        _set_color_space(self._drawable, color)

    @property
    def units(self) -> Any:
        """Return the circle units."""
        return _get_drawable_value(self._drawable, "units")

    @units.setter
    def units(self, value: str) -> None:
        """Set the circle units."""
        setattr(self._drawable, "units", str(value))


class LineParams:
    """Editable core parameters for a built-in line stimulus."""

    def __init__(self, drawable: Any) -> None:
        """Connect the parameter object to a PsychoPy ``Line``."""
        self._drawable = drawable

    @property
    def start_pos(self) -> Any:
        """Return the line start position."""
        return _get_drawable_value(self._drawable, "start")

    @start_pos.setter
    def start_pos(self, value: Sequence[float]) -> None:
        """Set the line start position."""
        setattr(self._drawable, "start", _validate_pos(value))

    @property
    def end_pos(self) -> Any:
        """Return the line end position."""
        return _get_drawable_value(self._drawable, "end")

    @end_pos.setter
    def end_pos(self, value: Sequence[float]) -> None:
        """Set the line end position."""
        setattr(self._drawable, "end", _validate_pos(value))

    @property
    def color(self) -> Any:
        """Return the line color."""
        return _get_drawable_value(self._drawable, "lineColor")

    @color.setter
    def color(self, value: str) -> None:
        """Set the line color and matching color space."""
        color = str(value)
        setattr(self._drawable, "lineColor", color)
        _set_color_space(self._drawable, color)

    @property
    def units(self) -> Any:
        """Return the line units."""
        return _get_drawable_value(self._drawable, "units")

    @units.setter
    def units(self, value: str) -> None:
        """Set the line units."""
        setattr(self._drawable, "units", str(value))


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


def make_text(
    win: Any,
    text: Any,
    *,
    start: Optional[float] = None,
    end: Optional[float] = None,
    label: Optional[str] = None,
    **stim_kwargs: Any,
) -> Any:
    """Create a timed PsychoPy ``TextStim`` wrapper.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window where the text will be drawn.
    text : object
        Text displayed by the stimulus.
    start, end : float, optional
        Screen-relative visibility timing.
    label : str, optional
        Optional researcher-facing label. Defaults to ``"text"``.
    **stim_kwargs
        Additional keyword arguments forwarded to
        ``psychopy.visual.TextStim``.

    Returns
    -------
    object
        Timed drawable text wrapper for ``timeline.make_screen(...)``.
    """
    visual = _load_psychopy_visual()
    kwargs = _text_stim_kwargs(text, stim_kwargs)
    drawable = visual.TextStim(win, **kwargs)
    return Stimulus(
        drawable=drawable,
        timing=Timing(start=start, end=end),
        params=TextParams(drawable),
        label=_stim_label(label, "text"),
    )


def make_image(
    win: Any,
    image: Any,
    *,
    start: Optional[float] = None,
    end: Optional[float] = None,
    label: Optional[str] = None,
    **stim_kwargs: Any,
) -> Any:
    """Create a timed PsychoPy ``ImageStim`` wrapper.

    Parameters
    ----------
    win : psychopy.visual.Window
        PsychoPy window where the image will be drawn.
    image : object
        Image source forwarded to PsychoPy.
    start, end : float, optional
        Screen-relative visibility timing.
    label : str, optional
        Optional researcher-facing label. Defaults to ``"image"``.
    **stim_kwargs
        Additional keyword arguments forwarded to
        ``psychopy.visual.ImageStim``.

    Returns
    -------
    object
        Timed drawable image wrapper for ``timeline.make_screen(...)``.
    """
    visual = _load_psychopy_visual()
    kwargs = _merge_stim_kwargs({"image": image}, stim_kwargs)
    drawable = visual.ImageStim(win, **kwargs)
    return Stimulus(
        drawable=drawable,
        timing=Timing(start=start, end=end),
        params=ImageParams(drawable),
        label=_stim_label(label, "image"),
    )


def make_rect(
    win: Any,
    width: float = 0.5,
    height: float = 0.5,
    *,
    pos: Sequence[float] = (0.0, 0.0),
    color: str = "#000000",
    units: str = "deg",
    start: Optional[float] = None,
    end: Optional[float] = None,
    label: Optional[str] = None,
    **stim_kwargs: Any,
) -> Any:
    """Create a timed PsychoPy ``Rect`` wrapper."""
    visual = _load_psychopy_visual()
    kwargs = _merge_stim_kwargs(
        {
            "width": _validate_size(width),
            "height": _validate_size(height),
            "pos": _validate_pos(pos),
            "units": str(units),
            **_color_kwargs(color),
        },
        stim_kwargs,
    )
    drawable = visual.Rect(win, **kwargs)
    return Stimulus(
        drawable=drawable,
        timing=Timing(start=start, end=end),
        params=RectParams(drawable),
        label=_stim_label(label, "rect"),
    )


def make_circle(
    win: Any,
    radius: float = 0.25,
    *,
    pos: Sequence[float] = (0.0, 0.0),
    color: str = "#000000",
    units: str = "deg",
    start: Optional[float] = None,
    end: Optional[float] = None,
    label: Optional[str] = None,
    **stim_kwargs: Any,
) -> Any:
    """Create a timed PsychoPy ``Circle`` wrapper."""
    visual = _load_psychopy_visual()
    validated_radius = _validate_size(radius)
    kwargs = _merge_stim_kwargs(
        {
            "radius": validated_radius,
            "pos": _validate_pos(pos),
            "units": str(units),
            **_color_kwargs(color),
        },
        stim_kwargs,
    )
    drawable = visual.Circle(win, **kwargs)
    return Stimulus(
        drawable=drawable,
        timing=Timing(start=start, end=end),
        params=CircleParams(drawable),
        label=_stim_label(label, "circle"),
    )


def make_line(
    win: Any,
    start_pos: Sequence[float],
    end_pos: Sequence[float],
    *,
    color: str = "#000000",
    units: str = "deg",
    start: Optional[float] = None,
    end: Optional[float] = None,
    label: Optional[str] = None,
    **stim_kwargs: Any,
) -> Any:
    """Create a timed PsychoPy ``Line`` wrapper."""
    visual = _load_psychopy_visual()
    kwargs = _merge_stim_kwargs(
        {
            "start": _validate_pos(start_pos),
            "end": _validate_pos(end_pos),
            "units": str(units),
            **_line_color_kwargs(color),
        },
        stim_kwargs,
    )
    drawable = visual.Line(win, **kwargs)
    return Stimulus(
        drawable=drawable,
        timing=Timing(start=start, end=end),
        params=LineParams(drawable),
        label=_stim_label(label, "line"),
    )


def make_fixation(
    win: Any,
    size: float = 0.5,
    pos: Sequence[float] = (0.0, 0.0),
    color: str = "#000000",
    units: str = "deg",
    start: Optional[float] = None,
    end: Optional[float] = None,
    label: Optional[str] = None,
) -> Any:
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
    object
        Timed drawable fixation wrapper that can be passed to
        ``timeline.make_screen(...)``.

    Examples
    --------
    >>> fix = make_fixation(win, size=0.5, color="#FFFFFF", start=0, end=0.5)
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
