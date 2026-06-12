# Eye Tracking API

Reference for `trackflow.gaze`, the EyeLink setup and tracker runtime
namespace.

| Page | API area |
| --- | --- |
| [API reference](reference.md) | `GazeConfig`, `setup_tracker(...)`, tracker lifecycle methods, realtime fixation checks, EyeLink messages, and `GazeBreakError`. |

```python
from trackflow import gaze

tracker = gaze.setup_tracker(
    win=win,
    cfg=gaze.GazeConfig(max_dist_deg=1.25),
    edf_name="S01.edf",
    monitor=monitor,
    debug=True,
)
```
