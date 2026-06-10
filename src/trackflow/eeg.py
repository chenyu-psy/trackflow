"""Parallel-port EEG marker helpers.

This module keeps PsychoPy imports lazy so importing ``trackflow.eeg`` does not
touch hardware. Real parallel-port setup requires an explicit port address.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EEGConfig:
    """Configuration for parallel-port EEG marker sending.

    Parameters
    ----------
    port_address : int
        Parallel-port address for the EEG trigger channel.
    pulse_width : float, optional
        Seconds to hold the marker code before resetting the port to zero.
    code : dict, optional
        User-defined EEG code dictionary for experiment scripts.

    Returns
    -------
    EEGConfig
        Validated parallel-port configuration.
    """

    port_address: int
    pulse_width: float = 0.005
    code: Optional[Dict[str, int]] = None

    def __post_init__(self) -> None:
        """Validate the configured port address and pulse width."""
        self.port_address = _validate_port_address(self.port_address)
        self.pulse_width = _validate_pulse_width(self.pulse_width)
        self.code = _validate_code_dict(self.code)


class ParallelPortMarkerSender:
    """Send EEG marker pulses through a PsychoPy parallel port.

    Parameters
    ----------
    port : object
        Object with a ``setData(code)`` method.
    core : object
        Object with a ``wait(seconds)`` method.
    pulse_width : float, optional
        Seconds to hold the marker code before resetting to zero.
    code : dict, optional
        User-defined EEG code dictionary for experiment scripts.
    """

    def __init__(self, port: Any, core: Any, pulse_width: float = 0.005, code: Optional[Dict[str, int]] = None) -> None:
        """Store the port and timing helper used for marker pulses."""
        if not hasattr(port, "setData") or not callable(port.setData):
            raise TypeError("EEG port must provide a callable setData(code) method.")
        if not hasattr(core, "wait") or not callable(core.wait):
            raise TypeError("PsychoPy core object must provide a callable wait(seconds) method.")
        self.port = port
        self.core = core
        self.pulse_width = _validate_pulse_width(pulse_width)
        self.code = _validate_code_dict(code)

    def send(self, code: int) -> None:
        """Send one EEG marker pulse and reset the port to zero.

        Parameters
        ----------
        code : int
            Marker code in the 8-bit parallel-port range ``1..255``.

        Returns
        -------
        None
            Writes ``code``, waits ``pulse_width`` seconds, then writes ``0``.
        """
        marker_code = _validate_marker_code(code)
        self.port.setData(marker_code)
        self.core.wait(self.pulse_width)
        self.port.setData(0)


@dataclass
class DebugMarkerSender:
    """Record marker sends without opening EEG hardware.

    Parameters
    ----------
    pulse_width : float, optional
        Stored for parity with real marker sender configuration.
    code : dict, optional
        User-defined EEG code dictionary for experiment scripts.
    sent_codes : list[int], optional
        Mutable record of marker codes sent during a debug run.
    """

    pulse_width: float = 0.005
    code: Optional[Dict[str, int]] = None
    sent_codes: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate debug pulse-width metadata."""
        self.pulse_width = _validate_pulse_width(self.pulse_width)
        self.code = _validate_code_dict(self.code)

    def send(self, code: int) -> None:
        """Record one marker code without touching hardware.

        Parameters
        ----------
        code : int
            Marker code in the 8-bit parallel-port range ``1..255``.

        Returns
        -------
        None
            Appends the validated code to ``sent_codes``.
        """
        self.sent_codes.append(_validate_marker_code(code))


def setup_port(
    cfg: Optional[EEGConfig] = None,
    *,
    port_address: Optional[int] = None,
    pulse_width: Optional[float] = None,
    code: Optional[Dict[str, int]] = None,
    debug: bool = False,
    port: Optional[Any] = None,
    core: Optional[Any] = None,
) -> Any:
    """Create an EEG marker sender for real or debug use.

    Parameters
    ----------
    cfg : EEGConfig, optional
        Explicit EEG configuration.
    port_address : int, optional
        Parallel-port address used when ``cfg`` is omitted.
    pulse_width : float, optional
        Marker pulse width. Defaults to ``cfg.pulse_width`` or ``0.005``.
    code : dict, optional
        User-defined EEG code dictionary. Defaults to ``cfg.code`` or ``{}``.
    debug : bool, optional
        If ``True``, return a debug sender and do not import PsychoPy.
    port, core : object, optional
        Existing port/core objects, mainly for tests or already-open hardware.

    Returns
    -------
    ParallelPortMarkerSender or DebugMarkerSender
        Sender with a ``send(code)`` method.
    """
    resolved_width = _resolve_pulse_width(cfg, pulse_width)
    resolved_code = _resolve_code_dict(cfg, code)
    if debug:
        return DebugMarkerSender(pulse_width=resolved_width, code=resolved_code)

    if port is None:
        resolved_address = _resolve_port_address(cfg, port_address)
        parallel = _load_psychopy_parallel()
        port = parallel.ParallelPort(address=resolved_address)
    if core is None:
        core = _load_psychopy_core()
    return ParallelPortMarkerSender(port=port, core=core, pulse_width=resolved_width, code=resolved_code)


def _resolve_port_address(cfg: Optional[EEGConfig], port_address: Optional[int]) -> int:
    """Return the explicit port address used for real hardware setup."""
    if port_address is not None:
        return _validate_port_address(port_address)
    if cfg is not None:
        return _validate_port_address(cfg.port_address)
    raise ValueError("port_address is required for EEG parallel-port setup.")


def _resolve_pulse_width(cfg: Optional[EEGConfig], pulse_width: Optional[float]) -> float:
    """Return the configured pulse width with the 0.1.0 default."""
    if pulse_width is not None:
        return _validate_pulse_width(pulse_width)
    if cfg is not None:
        return _validate_pulse_width(cfg.pulse_width)
    return 0.005


def _resolve_code_dict(cfg: Optional[EEGConfig], code: Optional[Dict[str, int]]) -> Dict[str, int]:
    """Return the explicit EEG code dictionary for runtime lookup."""
    if code is not None:
        return _validate_code_dict(code)
    if cfg is not None:
        return _validate_code_dict(cfg.code)
    return {}


def _validate_port_address(port_address: int) -> int:
    """Return ``port_address`` as a non-negative integer."""
    if isinstance(port_address, bool):
        raise ValueError("port_address must be an integer parallel-port address.")
    try:
        value = int(port_address)
    except (TypeError, ValueError):
        raise ValueError("port_address must be an integer parallel-port address.")
    if value < 0:
        raise ValueError("port_address must be greater than or equal to 0.")
    return value


def _validate_pulse_width(pulse_width: float) -> float:
    """Return ``pulse_width`` as a positive float in seconds."""
    try:
        value = float(pulse_width)
    except (TypeError, ValueError):
        raise ValueError("pulse_width must be a positive number of seconds.")
    if value <= 0:
        raise ValueError("pulse_width must be greater than 0.")
    return value


def _validate_marker_code(code: int) -> int:
    """Return ``code`` as an 8-bit non-zero marker code."""
    if isinstance(code, bool):
        raise ValueError("EEG marker code must be an integer from 1 to 255.")
    try:
        value = int(code)
    except (TypeError, ValueError):
        raise ValueError("EEG marker code must be an integer from 1 to 255.")
    if value < 1 or value > 255:
        raise ValueError("EEG marker code must be an integer from 1 to 255.")
    return value


def _validate_code_dict(code: Optional[Dict[str, int]]) -> Dict[str, int]:
    """Return a string-keyed EEG code dictionary with validated marker codes."""
    if code is None:
        return {}
    if not isinstance(code, dict):
        raise TypeError("EEG code must be a dictionary mapping names to integer marker codes.")
    out: Dict[str, int] = {}
    for key, value in code.items():
        out[str(key)] = _validate_marker_code(value)
    return out


def _load_psychopy_parallel() -> Any:
    """Import ``psychopy.parallel`` only when real EEG hardware is opened."""
    try:
        return __import__("psychopy.parallel", fromlist=["parallel"])
    except Exception as exc:
        raise RuntimeError("psychopy.parallel is required for EEG parallel-port setup.") from exc


def _load_psychopy_core() -> Any:
    """Import ``psychopy.core`` only when real EEG timing is needed."""
    try:
        return __import__("psychopy.core", fromlist=["core"])
    except Exception as exc:
        raise RuntimeError("psychopy.core is required for EEG marker pulse timing.") from exc


__all__: Tuple[str, ...] = (
    "DebugMarkerSender",
    "EEGConfig",
    "ParallelPortMarkerSender",
    "setup_port",
)
