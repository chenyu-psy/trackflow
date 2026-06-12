# Behavior Stimuli API

Reference for `trackflow.beh.stimuli`, which creates timed drawable objects
for `timeline.make_screen(...)`.

## Shared timing fields

Timing is screen-relative. It does not change screen duration or response
windows.

| Field | Description |
| --- | --- |
| `start` | Seconds after screen onset when drawing begins. `None` means visible from screen start. |
| `end` | Seconds after screen onset when drawing stops. `None` means visible until screen end. |
| `label` | Optional researcher-facing label. |
| Return | A drawable wrapper with `draw()` and timing-aware visibility. |

## Wrapping existing drawables

### `wrap_stimulus(...)`

Wrap an existing PsychoPy or custom drawable object.

| Argument | Description |
| --- | --- |
| `drawable` | Object with a callable `draw()` method. |
| `start`, `end`, `label` | Shared timing fields. |
| Return | Timed drawable wrapper for `timeline.make_screen(...)`. |

```python
ready_text = beh.stimuli.wrap_stimulus(text_stim, start=0.0, end=1.0)
```

## Text and image stimuli

### `make_text(...)`

Create a timed wrapper around PsychoPy `TextStim`.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window. |
| `text` | Text displayed by the stimulus. |
| `**stim_kwargs` | Additional keyword arguments forwarded to `TextStim`. |
| Editable params | `text`, `pos`, `color`, `height`, and `units`. |

```python
label = beh.stimuli.make_text(win, "Ready?", height=0.7, color="white")
```

### `make_image(...)`

Create a timed wrapper around PsychoPy `ImageStim`.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window. |
| `image` | Image source forwarded to PsychoPy. |
| `**stim_kwargs` | Additional keyword arguments forwarded to `ImageStim`. |
| Editable params | `image`, `pos`, `size`, and `units`. |

```python
picture = beh.stimuli.make_image(win, "sample.png", size=(4, 4))
```

## Shape stimuli

### `make_rect(...)`

Create a timed wrapper around PsychoPy `Rect`.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window. |
| `width`, `height` | Rect size. Defaults to `0.5` by `0.5`. |
| `pos`, `color`, `units` | Rect position, fill/line color, and PsychoPy units. |
| `**stim_kwargs` | Additional keyword arguments forwarded to `Rect`. |
| Editable params | `width`, `height`, `pos`, `color`, and `units`. |

```python
box = beh.stimuli.make_rect(win, width=2, height=1, color="#FFFFFF")
```

### `make_circle(...)`

Create a timed wrapper around PsychoPy `Circle`.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window. |
| `radius` | Circle radius. Defaults to `0.25`. |
| `pos`, `color`, `units` | Circle position, fill/line color, and PsychoPy units. |
| `**stim_kwargs` | Additional keyword arguments forwarded to `Circle`. |
| Editable params | `radius`, `pos`, `color`, and `units`. |

```python
dot = beh.stimuli.make_circle(win, radius=0.15, color="#000000")
```

### `make_line(...)`

Create a timed wrapper around PsychoPy `Line`.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window. |
| `start_pos`, `end_pos` | Line endpoints. |
| `color`, `units` | Line color and PsychoPy units. |
| `**stim_kwargs` | Additional keyword arguments forwarded to `Line`. |
| Editable params | `start_pos`, `end_pos`, `color`, and `units`. |

```python
line = beh.stimuli.make_line(win, start_pos=(-1, 0), end_pos=(1, 0))
```

## Fixation

### `make_fixation(...)`

Create the built-in fixed-ratio fixation stimulus.

| Argument | Description |
| --- | --- |
| `win` | PsychoPy window. |
| `size` | Full outer diameter. Defaults to `0.5`. |
| `pos`, `color`, `units` | Fixation center, visible color, and PsychoPy units. |
| `start`, `end`, `label` | Shared timing fields. |
| Editable params | `size`, `pos`, `color`, and `units`. |

```python
fix = beh.stimuli.make_fixation(win, size=0.5, color="#000000")
```
