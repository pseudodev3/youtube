from __future__ import annotations

import renderer_enhanced as enhanced
import native_map_runtime as native

W = enhanced.W
H = enhanced.H

_CURRENT_EPISODE = 0
_NATIVE_ACTIVE = native.is_available()

# Keep exact references so every patch can fall back to the already-working
# Python implementation if the native engine is unavailable for any reason.
_ORIG_WORLD_HORIZON = enhanced._world_horizon
_ORIG_WORLD_GROUND = enhanced._world_ground
_ORIG_DECORATE = enhanced._base._decorate

_ORIG_COUNTRY = enhanced._base._country
_ORIG_MOUNTAIN = enhanced._base._mountain
_ORIG_CITY = enhanced._base._city
_ORIG_COAST = enhanced._base._coast
_ORIG_CANYON = enhanced._base._canyon
_ORIG_DESERT = enhanced._base._desert
_ORIG_FOREST = enhanced._base._forest
_ORIG_STREET = enhanced._base._street
_ORIG_TUNNEL = enhanced._base._tunnel


def _episode() -> int:
    return int(_CURRENT_EPISODE)


def _scene_ok(key: str) -> bool:
    return _NATIVE_ACTIVE and native.has_scene(key, _episode())


def _world_horizon(draw, key: str) -> None:
    if _NATIVE_ACTIVE and native.draw_horizon(draw, key, _episode()):
        return
    _ORIG_WORLD_HORIZON(draw, key)


def _world_ground(draw, key: str) -> None:
    if _NATIVE_ACTIVE and native.draw_ground(draw, key, _episode()):
        return
    _ORIG_WORLD_GROUND(draw, key)


def _country(draw, frame) -> None:
    if _scene_ok("country"):
        return
    _ORIG_COUNTRY(draw, frame)


def _mountain(draw, frame, alpine: bool = False) -> None:
    key = "alpine" if alpine else "mountain"
    if _scene_ok(key):
        return
    _ORIG_MOUNTAIN(draw, frame, alpine=alpine)


def _city(draw, frame, neon: bool = False) -> None:
    key = "neon_rain" if neon else "night_city"
    if _scene_ok(key):
        return
    _ORIG_CITY(draw, frame, neon=neon)


def _coast(draw, frame) -> None:
    if _scene_ok("coast"):
        return
    _ORIG_COAST(draw, frame)


def _canyon(draw, extreme: bool = False) -> None:
    key = "extreme_canyon" if extreme else "canyon"
    if _scene_ok(key):
        return
    _ORIG_CANYON(draw, extreme=extreme)


def _desert(draw, frame) -> None:
    if _scene_ok("desert"):
        return
    _ORIG_DESERT(draw, frame)


def _forest(draw, frame) -> None:
    if _scene_ok("forest"):
        return
    _ORIG_FOREST(draw, frame)


def _street(draw, frame) -> None:
    if _scene_ok("street"):
        return
    _ORIG_STREET(draw, frame)


def _tunnel(draw) -> None:
    if _scene_ok("tunnel"):
        return
    _ORIG_TUNNEL(draw)


def _decorate(img, frame, frame_no: int):
    # Run the existing renderer first. Its map-specific geometry helpers above
    # become no-ops only when native data is actually available, while tints,
    # rain/snow, HUD-safe effects and all existing polish remain intact.
    out = _ORIG_DECORATE(img, frame, frame_no)
    if _NATIVE_ACTIVE:
        key = enhanced._road_key(frame)
        native.draw_roadside(out, key, _episode(), frame_no)
    return out


if _NATIVE_ACTIVE:
    enhanced._world_horizon = _world_horizon
    enhanced._world_ground = _world_ground
    enhanced._base._country = _country
    enhanced._base._mountain = _mountain
    enhanced._base._city = _city
    enhanced._base._coast = _coast
    enhanced._base._canyon = _canyon
    enhanced._base._desert = _desert
    enhanced._base._forest = _forest
    enhanced._base._street = _street
    enhanced._base._tunnel = _tunnel
    enhanced._base._decorate = _decorate
    print("GRIDLOOP map engine: native C++ terrain + roadside scenery active")
else:
    print("GRIDLOOP map engine: C++ binary unavailable; using Python map fallback")


def render_frame(frame, episode: int, skill: float, frame_no: int):
    global _CURRENT_EPISODE
    _CURRENT_EPISODE = int(episode)
    return enhanced.render_frame(frame, episode=episode, skill=skill, frame_no=frame_no)
