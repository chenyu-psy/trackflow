"""Configuration objects and EyeLink setting helpers for gaze runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .runtime import _normalize_hex, _should_use_dark_text

DEFAULT_TRACKING_SETTINGS = {
    "automatic_calibration_pacing": 1000,
    "background_color": "#000000",
    "calibration_area_proportion": (0.5, 0.5),
    "calibration_type": "HV9",
    "elcl_configuration": "BTABLER",
    "enable_automatic_calibration": "YES",
    "error_sound": "",
    "foreground_color": "#FFFFFF",
    "good_sound": "",
    "preamble_text": None,
    "pupil_size_diameter": "NO",
    "saccade_acceleration_threshold": 9500,
    "saccade_motion_threshold": 0.15,
    "saccade_pursuit_fixup": 60,
    "saccade_velocity_threshold": 30,
    "sample_rate": 1000,
    "target_sound": "",
    "validation_area_proportion": (0.5, 0.5),
}


@dataclass
class GazeConfig:
    """Configuration for EyeLink setup and realtime gaze monitoring.

    Parameters
    ----------
    tracked_eye : str, optional
        EyeLink eye selection: ``"LEFT"``, ``"RIGHT"``, or ``"BOTH"``.
    calibration_type : str, optional
        EyeLink calibration layout, such as ``"HV9"``.
    calibration_area : tuple[float, float], optional
        Proportion of screen width and height used for calibration and
        validation. Smaller values focus calibration precision on a central
        stimulus area.
    max_dist_deg : float, optional
        Allowed gaze distance from fixation in visual degrees.
    bg_color : str, optional
        HEX background color used for normal gaze/calibration pages and
        EyeLink calibration background.
    eyelink_settings : dict, optional
        Advanced EyeLink command overrides for settings not exposed as public
        top-level fields.

    Notes
    -----
    This object describes how gaze is configured when eye tracking is used.
    Session choices such as whether eye tracking is enabled, the EDF filename,
    and debug mode belong in the experiment/session setup code.
    """

    tracked_eye: str = "BOTH"
    calibration_type: str = "HV9"
    calibration_area: Tuple[float, float] = (0.5, 0.5)
    max_dist_deg: float = 1.25
    bg_color: str = "#7F7F7F"
    eyelink_settings: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize and validate gaze settings after construction."""
        self.tracked_eye = str(self.tracked_eye).upper()
        if self.tracked_eye not in ("LEFT", "RIGHT", "BOTH"):
            raise ValueError("tracked_eye must be LEFT, RIGHT, or BOTH.")
        if len(self.calibration_area) != 2:
            raise ValueError("calibration_area must contain width and height proportions.")
        self.calibration_area = (float(self.calibration_area[0]), float(self.calibration_area[1]))
        for value in self.calibration_area:
            if value <= 0 or value > 1:
                raise ValueError("calibration_area values must be greater than 0 and at most 1.")
        self.max_dist_deg = float(self.max_dist_deg)
        self.bg_color = _normalize_hex(self.bg_color)


def _make_tracking_settings(
    cfg: GazeConfig,
    calibration_type: Optional[str] = None,
    calibration_area: Optional[Tuple[float, float]] = None,
) -> Dict[str, Any]:
    """Build EyeLink command settings from a gaze configuration.

    Parameters
    ----------
    cfg : GazeConfig
        Public gaze settings for the session.
    calibration_type : str | None, optional
        Per-call calibration type override.
    calibration_area : tuple[float, float] | None, optional
        Per-call calibration area override.

    Returns
    -------
    dict
        EyeLink settings dictionary. Validation area is always matched to the
        calibration area so users do not accidentally validate a different
        region from the one they calibrated.
    """
    area = cfg.calibration_area if calibration_area is None else (float(calibration_area[0]), float(calibration_area[1]))
    if len(area) != 2:
        raise ValueError("calibration_area must contain width and height proportions.")
    for value in area:
        if value <= 0 or value > 1:
            raise ValueError("calibration_area values must be greater than 0 and at most 1.")

    settings = dict(DEFAULT_TRACKING_SETTINGS)
    settings.update(cfg.eyelink_settings)
    settings["background_color"] = cfg.bg_color
    settings["foreground_color"] = _readable_text_color(cfg.bg_color)
    settings["calibration_type"] = calibration_type or cfg.calibration_type
    settings["calibration_area_proportion"] = area
    settings["validation_area_proportion"] = area
    return settings


def _readable_text_color(bg_color: str) -> str:
    """Return a readable text color for a normalized background color."""
    if _should_use_dark_text(bg_color):
        return "#000000"
    return "#FFFFFF"


def _validate_edf_name(edf_name: str) -> None:
    """Validate the short EDF filename used on the EyeLink host.

    Parameters
    ----------
    edf_name : str
        EDF filename opened on the EyeLink host.

    Returns
    -------
    None
        Raises if the filename does not fit EyeLink host constraints.
    """
    if len(edf_name) > 12:
        raise ValueError("EDF filename must be at most 12 characters long including the extension.")
    if not edf_name.endswith(".edf"):
        raise ValueError("edf_name must include the .edf extension.")
