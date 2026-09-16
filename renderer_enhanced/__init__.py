from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import ImageDraw

# Load the existing enhanced renderer implementation from the sibling module file.
_base_path = Path(__file__).resolve().parent.parent / "renderer_enhanced.py"
_spec = importlib.util.spec_from_file_location("_gridloop_renderer_enhanced_base", _base_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load GRIDLOOP renderer from {_base_path}")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

W = _base.W
H = _base.H


def _country_clean(d: ImageDraw.ImageDraw, frame) -> None:
    """Slim countryside fencing with perspective, gaps and occasional trees."""
    posts_by_side: dict[int, list[tuple[float, float, float]]] = {-1: [], 1: []}

    # Fewer, slimmer posts than the original chunky treatment. Moving slots keep
    # the fence flowing toward the camera while scale handles perspective.
    for i, (_, y, s) in enumerate(_base._moving_slots(frame, 8, 0.050)):
        if y < 520:
            continue
        # Deliberate gaps stop the roadside from looking like a continuous brown wall.
        if i in {2, 6}:
            continue
        for side in (-1, 1):
            x = 78 if side < 0 else W - 78
            # Slight stagger makes the two sides feel less copy-pasted.
            yy = y + (10 * s if side > 0 and i % 2 else 0)
            posts_by_side[side].append((x, yy, s))

    wood_dark = (86, 58, 34, 238)
    wood_mid = (113, 78, 45, 230)
    wood_light = (145, 103, 60, 210)

    for side, posts in posts_by_side.items():
        posts.sort(key=lambda item: item[1])

        # Connect neighboring posts with two thin rails. Their widths grow gently
        # toward the camera, which reads much more clearly as fencing in motion.
        for (x0, y0, s0), (x1, y1, s1) in zip(posts, posts[1:]):
            rail1_a = (x0, y0 - 31 * s0)
            rail1_b = (x1, y1 - 31 * s1)
            rail2_a = (x0, y0 - 16 * s0)
            rail2_b = (x1, y1 - 16 * s1)
            width = max(2, int(2.6 * ((s0 + s1) * 0.5)))
            d.line([rail1_a, rail1_b], fill=wood_mid, width=width)
            d.line([rail2_a, rail2_b], fill=wood_light, width=max(2, width - 1))

        for i, (x, y, s) in enumerate(posts):
            post_w = max(2.0, 2.4 * s)
            post_h = 47 * s
            d.rounded_rectangle(
                [x - post_w, y - post_h, x + post_w, y + 3 * s],
                radius=max(1, int(1.8 * s)),
                fill=wood_dark,
            )

            # Sparse roadside trees keep the scene rural without turning Country
            # into the later Forest map.
            if i % 3 == 1:
                offset = side * (50 + 12 * s)
                _base._tree(d, x + offset, y + 4 * s, s * 0.60)


# Replace only Country's decoration function. Everything else in the renderer,
# including cars, physics-driven framing, HUD and every other map, stays unchanged.
_base._country = _country_clean


def render_frame(frame, episode: int, skill: float, frame_no: int):
    return _base.render_frame(frame, episode=episode, skill=skill, frame_no=frame_no)
