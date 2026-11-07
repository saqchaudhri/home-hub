"""Build the Home Hub dashboards from the wizard's answers.

Everything here is plain data in, plain data out, so it can be tested without
a running Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import html
import json
from pathlib import Path
from typing import Any

from .const import (
    CONF_BATTERY_SENSORS,
    CONF_BIN_CALENDAR,
    CONF_CALENDAR,
    CONF_CLIMATES,
    CONF_DOORBELL_CAMERA,
    CONF_DRIVEWAY_CAMERA,
    CONF_EXTRA_MEDIA,
    CONF_HOUSE_NAME,
    CONF_LIGHTS,
    CONF_OFFICE_DOOR,
    CONF_OWNER_NAME,
    CONF_PEOPLE,
    CONF_PRAYER_TIMES,
    CONF_SCREENSAVER_PHOTOS,
    CONF_SPEAKER,
    CONF_WEATHER,
    CONF_WHITE_NOISE,
    WHITE_NOISE_URL,
)

CARDS_DIR = Path(__file__).parent / "cards"
TEMPLATE_FILES = ("clock.js", "prayer.js", "weather.js", "calendar.js", "screensaver.js", "nightclock.js", "onair.css")

BACKGROUND = (
    "radial-gradient(1100px 700px at 0% 0%, #1b2742 0%, rgba(27,39,66,0) 60%), "
    "radial-gradient(900px 700px at 100% 100%, #33210f 0%, rgba(51,33,15,0) 55%), #0a0c11"
)
# The design is dark glass whatever theme the household uses, so every card
# carries dark-theme colours of its own.
DARK_VARS = {
    "--primary-text-color": "#F4F5F7",
    "--secondary-text-color": "rgba(244,245,247,0.62)",
    "--disabled-text-color": "rgba(244,245,247,0.38)",
    # Mushroom works these out on its outer element, so they must be set too
    "--card-primary-color": "#F4F5F7",
    "--card-secondary-color": "rgba(244,245,247,0.62)",
    "--title-color": "#F4F5F7",
    "--subtitle-color": "rgba(244,245,247,0.62)",
    "--secondary-background-color": "rgba(255,255,255,0.08)",
    "--divider-color": "rgba(255,255,255,0.12)",
    "--chip-background": "rgba(255,255,255,0.08)",
    "--ha-card-background": "rgba(255,255,255,0.06)",
    "color": "#F4F5F7",
}
DARK_CSS = "ha-card { " + " ".join(f"{k}: {v};" for k, v in DARK_VARS.items()) + " } "
GLASS_CSS = DARK_CSS + (
    "ha-card { background: rgba(255,255,255,0.06) !important; -webkit-backdrop-filter: blur(20px); "
    "backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.09) !important; "
    "border-radius: 22px !important; box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important; overflow: hidden; }"
)
CAMERA_CSS = DARK_CSS + (
    "ha-card {  -webkit-backdrop-filter: blur(20px); backdrop-filter: blur(20px); "
    "border: 1px solid rgba(255,255,255,0.09) !important; border-radius: 22px !important; "
    "box-shadow: 0 8px 24px rgba(0,0,0,0.35) !important; overflow: hidden; }"
)
# Colours for calendar entries that mention a family member's name
PERSON_COLOURS = ("#63B3ED", "#F687B3", "#B794F6", "#4FD1C5", "#68D391", "#FC8181")


@dataclass
class HouseInfo:
    """What the builder needs to know about the house besides the wizard answers."""

    # (display name, entity id) for each prayer, in order; empty if none found
    prayers: list[tuple[str, str]] = field(default_factory=list)
    # entity id -> first name, for people chips and calendar colours
    person_names: dict[str, str] = field(default_factory=dict)
    # Home Hub's own entities, when their feature is turned on
    azan_playing: str | None = None
    stop_azan: str | None = None
    tablet_mode: str | None = None


def load_templates() -> dict[str, str]:
    """Read the card templates from disk (blocking, run in an executor)."""
    return {name: (CARDS_DIR / name).read_text(encoding="utf-8") for name in TEMPLATE_FILES}


def _fill(template: str, **values: Any) -> str:
    """Replace __NAME__ placeholders with JSON-encoded values (safe inside JS)."""
    out = template.strip("\n")
    for key, value in values.items():
        out = out.replace(f"__{key}__", value if key == "ROW_STYLE" else json.dumps(value))
    return out


def _glass_button_styles(padding: str) -> dict[str, Any]:
    return {
        "card": [
            {"background": "rgba(255,255,255,0.06)"},
            {"-webkit-backdrop-filter": "blur(20px)"},
            {"backdrop-filter": "blur(20px)"},
            {"border": "1px solid rgba(255,255,255,0.09)"},
            {"border-radius": "22px"},
            {"box-shadow": "0 8px 24px rgba(0,0,0,0.35)"},
            {"padding": padding},
            *({k: v} for k, v in DARK_VARS.items()),
        ],
        "grid": [{"grid-template-areas": '"block"'}, {"grid-template-columns": "1fr"}],
        "custom_fields": {"block": [{"justify-self": "stretch"}, {"width": "100%"}]},
    }


def _block_card(block: str, padding: str, **extra: Any) -> dict[str, Any]:
    """A button-card that just renders one HTML block, in the glass style."""
    return {
        "type": "custom:button-card",
        "triggers_update": "all",
        "show_icon": False,
        "show_name": False,
        "show_state": False,
        **extra,
        "styles": _glass_button_styles(padding),
        "custom_fields": {"block": block},
    }


def _heading(text: str, icon: str) -> dict[str, Any]:
    return {"type": "heading", "heading": text, "icon": icon, "heading_style": "title", "card_mod": {"style": DARK_CSS}}


def _light_tile(entity_id: str) -> dict[str, Any]:
    return {
        "type": "tile",
        "entity": entity_id,
        "color": "amber",
        "tap_action": {"action": "toggle"},
        "icon_tap_action": {"action": "toggle"},
        "hold_action": {"action": "more-info"},
        "grid_options": {"columns": 6, "rows": 1},
        "card_mod": {"style": GLASS_CSS},
    }


def _climate_tile(entity_id: str) -> dict[str, Any]:
    return {
        "type": "tile",
        "entity": entity_id,
        "color": "deep-orange",
        "state_content": ["hvac_action", "current_temperature"],
        "features": [{"type": "target-temperature"}],
        "features_position": "inline",
        "grid_options": {"columns": 12, "rows": "auto"},
        "card_mod": {"style": GLASS_CSS},
    }


def _camera_card(entity_id: str, name: str, live: bool, columns: int, rows: int) -> dict[str, Any]:
    return {
        "type": "picture-entity",
        "entity": entity_id,
        "name": name,
        "camera_view": "live" if live else "auto",
        "fit_mode": "cover",
        "show_name": True,
        "show_state": False,
        "grid_options": {"columns": columns, "rows": rows},
        "card_mod": {"style": CAMERA_CSS},
    }


def _media_card(entity_id: str) -> dict[str, Any]:
    return {
        "type": "custom:mushroom-media-player-card",
        "entity": entity_id,
        "use_media_info": True,
        "show_volume_level": False,
        "media_controls": ["play_pause_stop", "previous", "next"],
        "volume_controls": ["volume_set"],
        "collapsible_controls": False,
        "grid_options": {"columns": 12},
        "card_mod": {"style": GLASS_CSS},
    }


def _white_noise_card(speaker: str) -> dict[str, Any]:
    return {
        "type": "custom:mushroom-template-card",
        "primary": "White noise",
        "secondary": "Play on the speaker",
        "icon": "mdi:sleep",
        "icon_color": "indigo",
        "grid_options": {"columns": 12},
        "card_mod": {"style": GLASS_CSS},
        "tap_action": {
            "action": "perform-action",
            "perform_action": "media_player.play_media",
            "target": {"entity_id": speaker},
            "data": {"media_content_id": WHITE_NOISE_URL, "media_content_type": "music"},
        },
    }


def _chips(cfg: dict[str, Any], show_state: bool) -> dict[str, Any] | None:
    chips: list[dict[str, Any]] = [
        {"type": "entity", "entity": p, "use_entity_picture": True, "content_info": "state" if show_state else "none"}
        for p in cfg.get(CONF_PEOPLE) or []
    ]
    for sensor in cfg.get(CONF_BATTERY_SENSORS) or []:
        level = f"states('{sensor}')"
        chips.append(
            {
                "type": "template",
                "entity": sensor,
                "icon": "mdi:battery",
                "content": "{{ " + level + " }}%",
                "icon_color": "{{ 'red' if " + level + "|int(0) < 20 else 'green' }}",
                "tap_action": {"action": "more-info"},
            }
        )
    if not chips:
        return None
    return {"type": "custom:mushroom-chips-card", "alignment": "start", "chips": chips, "card_mod": {"style": DARK_CSS}}


def _prayer_card(templates: dict[str, str], house: HouseInfo, phone: bool) -> dict[str, Any]:
    row = "padding:9px 12px;border-radius:12px;font-size:16px" if phone else "padding:6px 12px;border-radius:10px;font-size:15px"
    block = _fill(templates["prayer.js"], PRAYERS=[list(p) for p in house.prayers], ROW_STYLE=row)
    return _block_card(
        block,
        "20px 22px" if phone else "16px 20px",
        tap_action={"action": "more-info", "entity": house.prayers[0][1]},
    )


def _weather_card(templates: dict[str, str], weather: str) -> dict[str, Any]:
    card = _block_card(
        _fill(templates["weather.js"], WEATHER=weather),
        "12px 16px",
        name="Weather",
        entity=weather,
        tap_action={"action": "more-info"},
    )
    return {
        "type": "conditional",
        "conditions": [{"condition": "state", "entity": weather, "state_not": "unavailable"}],
        "card": card,
    }


def _calendar_card(templates: dict[str, str], cfg: dict[str, Any], house: HouseInfo, cap: int) -> dict[str, Any]:
    colours = [
        [name.lower(), PERSON_COLOURS[i % len(PERSON_COLOURS)]]
        for i, name in enumerate(house.person_names.get(p, "") for p in cfg.get(CONF_PEOPLE) or [])
        if name
    ]
    block = _fill(
        templates["calendar.js"],
        CALENDAR=cfg[CONF_CALENDAR],
        BIN_CALENDAR=cfg.get(CONF_BIN_CALENDAR) or None,
        COLOURS=colours,
        CAP=cap,
    )
    return _block_card(
        block,
        "20px 18px",
        name="Family calendar",
        tap_action={"action": "more-info", "entity": cfg[CONF_CALENDAR]},
        grid_options={"columns": 12},
    )


def _cameras(cfg: dict[str, Any], phone: bool) -> list[dict[str, Any]]:
    cols, rows = (12, 4) if phone else (6, 3)
    cams = []
    if driveway := cfg.get(CONF_DRIVEWAY_CAMERA):
        cams.append(_camera_card(driveway, "Driveway", True, cols, rows))
    if doorbell := cfg.get(CONF_DOORBELL_CAMERA):
        cams.append(_camera_card(doorbell, "Doorbell", False, cols, rows))
    return [_heading("Cameras", "mdi:cctv"), *cams] if cams else []


def _lights(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    lights = cfg.get(CONF_LIGHTS) or []
    return [_heading("Lights", "mdi:lightbulb-group"), *map(_light_tile, lights)] if lights else []


def _heating(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    climates = cfg.get(CONF_CLIMATES) or []
    return [_heading("Heating", "mdi:fire"), *map(_climate_tile, climates)] if climates else []


def _section(cards: list[dict[str, Any] | None]) -> dict[str, Any] | None:
    cards = [c for c in cards if c]
    return {"type": "grid", "cards": cards} if cards else None


def _view(sections: list[dict[str, Any] | None], max_columns: int) -> dict[str, Any]:
    return {
        "title": "Home",
        "path": "home",
        "type": "sections",
        "max_columns": max_columns,
        "dense_section_placement": False,
        "background": BACKGROUND,
        "sections": [s for s in sections if s],
    }


AMBER_STYLES = {
    "card": [
        {"background": "rgba(245,165,36,0.18)"},
        {"border": "1px solid rgba(245,165,36,0.55)"},
        {"box-shadow": "0 0 24px rgba(245,165,36,0.25)"},
    ],
    "icon": [{"color": "#F5A524"}],
    "name": [{"color": "#F5A524"}],
    "label": [{"color": "#F5A524"}, {"opacity": "0.9"}],
}


def _stop_azan_card(house: HouseInfo, phone: bool) -> dict[str, Any] | None:
    """Stop azan: always shown on the phone (amber while playing), only while playing on the tablet."""
    if not (house.azan_playing and house.stop_azan):
        return None
    glass = _glass_button_styles("14px 18px")["card"]
    card: dict[str, Any] = {
        "type": "custom:button-card",
        "name": "Stop azan",
        "entity": house.azan_playing,
        "icon": "mdi:volume-off",
        "show_state": False,
        "tap_action": {"action": "perform-action", "perform_action": "button.press", "target": {"entity_id": house.stop_azan}},
        "grid_options": {"columns": 12},
    }
    if not phone:
        card["styles"] = {
            "card": [*glass, *AMBER_STYLES["card"]],
            "grid": [{"grid-template-areas": '"i n"'}, {"grid-template-columns": "min-content 1fr"}, {"column-gap": "14px"}],
            "icon": [{"width": "30px"}, *AMBER_STYLES["icon"]],
            "name": [{"justify-self": "start"}, {"font-size": "18px"}, {"font-weight": "700"}, *AMBER_STYLES["name"]],
        }
        return {
            "type": "conditional",
            "conditions": [{"condition": "state", "entity": house.azan_playing, "state": "on"}],
            "card": card,
        }
    card |= {
        "show_label": True,
        "label": "[[[ return entity.state === 'on' ? 'Azan playing now, tap to stop' : 'Tap to stop the azan while it plays'; ]]]",
        "styles": {
            "card": glass,
            "grid": [{"grid-template-areas": '"i n" "i l"'}, {"grid-template-columns": "min-content 1fr"}, {"column-gap": "14px"}],
            "icon": [{"width": "26px"}, {"color": "rgba(255,255,255,0.55)"}],
            "name": [{"justify-self": "start"}, {"font-size": "16px"}, {"font-weight": "600"}],
            "label": [{"justify-self": "start"}, {"font-size": "12px"}, {"opacity": "0.6"}],
        },
        "state": [{"value": "on", "styles": AMBER_STYLES}],
    }
    return card


def _info_cards(templates: dict[str, str], cfg: dict[str, Any], house: HouseInfo, phone: bool) -> list[dict[str, Any]]:
    cards = []
    if cfg.get(CONF_PRAYER_TIMES) and house.prayers:
        cards.append(_prayer_card(templates, house, phone))
    if phone and (stop := _stop_azan_card(house, phone=True)):
        cards.append(stop)
    if weather := cfg.get(CONF_WEATHER):
        cards.append(_weather_card(templates, weather))
    return cards


def build_wall(templates: dict[str, str], cfg: dict[str, Any], house: HouseInfo) -> dict[str, Any]:
    """The landscape wall-tablet dashboard, with the photo screensaver."""
    speaker = cfg.get(CONF_SPEAKER)
    left = [
        _chips(cfg, show_state=False),
        _stop_azan_card(house, phone=False),
        _block_card(_fill(templates["clock.js"]), "18px 22px"),
        *_info_cards(templates, cfg, house, phone=False),
    ]
    if speaker:
        left += [_heading("Music", "mdi:speaker"), _media_card(speaker)]
        if cfg.get(CONF_WHITE_NOISE):
            left.append(_white_noise_card(speaker))
    right = []
    if cfg.get(CONF_CALENDAR):
        right.append(_calendar_card(templates, cfg, house, cap=6))
    right += _cameras(cfg, phone=False)

    dashboard: dict[str, Any] = {
        "views": [_view([_section(left), _section([*_heating(cfg), *_lights(cfg)]), _section(right)], 3)]
    }
    dashboard["wallpanel"] = _screensaver(templates, cfg, house)
    return dashboard


def _screensaver(templates: dict[str, str], cfg: dict[str, Any], house: HouseInfo) -> dict[str, Any]:
    owner = (cfg.get(CONF_OWNER_NAME) or "").strip()
    prayers = [list(p) for p in house.prayers] if cfg.get(CONF_PRAYER_TIMES) else []
    block = _fill(
        templates["screensaver.js"],
        PRAYERS=prayers,
        DOOR=cfg.get(CONF_OFFICE_DOOR) or None,
        OWNER=html.escape(owner),
    )
    card = {
        "type": "custom:button-card",
        "triggers_update": "all",
        "show_icon": False,
        "show_name": False,
        "show_state": False,
        "styles": {
            "card": [
                {"background": "rgba(10,12,17,0.62)"},
                {"-webkit-backdrop-filter": "blur(14px)"},
                {"backdrop-filter": "blur(14px)"},
                {"border": "1px solid rgba(255,255,255,0.12)"},
                {"border-radius": "24px"},
                {"padding": "18px 26px"},
                {"box-shadow": "none"},
                {"color": "white"},
            ],
            "grid": [{"grid-template-areas": '"block"'}, {"grid-template-columns": "1fr"}],
            "custom_fields": {"block": [{"justify-self": "start"}]},
        },
        "custom_fields": {"block": block},
        "extra_styles": templates["onair.css"],
    }
    panel: dict[str, Any] = {
        "enabled": True,
        "idle_time": 60,
        "display_time": 15,
        "crossfade_time": 3,
        "media_order": "random",
        "image_fit_landscape": "cover",
        "image_fit_portrait": "contain",
        "show_image_info": False,
        "fullscreen": False,
        "disable_screensaver_on_browser_mod_popup": True,
        "cards": [card],
        "style": {
            "wallpanel-screensaver-info-box": {
                "--wp-card-width": "auto",
                "width": "auto",
                "max-width": "520px",
                "left": "40px",
                "bottom": "40px",
                "top": "auto",
                "right": "auto",
                "background-color": "transparent",
            }
        },
    }
    if cfg.get(CONF_SCREENSAVER_PHOTOS, True):
        panel["image_url"] = "media-source://media_source/local/"
    else:
        panel["show_images"] = False
    if house.tablet_mode:
        panel["profile_entity"] = house.tablet_mode
        panel["profiles"] = {"day": {}, "night": _night_profile(templates, prayers)}
    return panel


def _night_profile(templates: dict[str, str], prayers: list[list[str]]) -> dict[str, Any]:
    """At night the screensaver is a black screen with a dim clock in the middle."""
    clock = {
        "type": "custom:button-card",
        "triggers_update": "all",
        "show_icon": False,
        "show_name": False,
        "show_state": False,
        "styles": {
            "card": [{"background": "none"}, {"box-shadow": "none"}, {"border": "none"}, {"padding": "calc(50vh - 125px) 0 0 0"}],
            "grid": [{"grid-template-areas": '"block"'}, {"grid-template-columns": "1fr"}],
            "custom_fields": {"block": [{"justify-self": "center"}]},
        },
        "custom_fields": {"block": _fill(templates["nightclock.js"], PRAYERS=prayers)},
    }
    return {
        "idle_time": 30,
        "show_images": False,
        "cards": [clock],
        "style": {
            "wallpanel-screensaver-container": {"background-color": "#000"},
            "wallpanel-screensaver-info-box": {
                "top": "0",
                "left": "0",
                "right": "0",
                "bottom": "0",
                "width": "100%",
                "height": "100%",
                "max-width": "none",
                "display": "flex",
                "align-items": "center",
                "justify-content": "center",
                "background-color": "transparent",
            },
        },
    }


def build_phone(templates: dict[str, str], cfg: dict[str, Any], house: HouseInfo) -> dict[str, Any]:
    """The portrait phone dashboard."""
    speaker = cfg.get(CONF_SPEAKER)
    greeting = {
        "type": "custom:mushroom-title-card",
        "title": "{% set h = now().hour %}{{ 'Good morning' if h < 12 else 'Good afternoon' if h < 18 else 'Good evening' }}",
        "subtitle": "{{ now().strftime('%A %-d %B') }}",
        "alignment": "start",
        "card_mod": {
            "style": DARK_CSS + "ha-card { padding: 4px 4px 0 !important; } .title { font-size: 26px !important; "
            "font-weight: 700 !important; } .subtitle { color: #F5A524 !important; letter-spacing: 1px; }"
        },
    }
    media = []
    if speaker or cfg.get(CONF_EXTRA_MEDIA):
        media = [_heading("Media", "mdi:speaker")]
        media += [_media_card(e) for e in [speaker, *(cfg.get(CONF_EXTRA_MEDIA) or [])] if e]
    sections = [
        _section([greeting, _chips(cfg, show_state=True)]),
        _section([_white_noise_card(speaker)] if speaker and cfg.get(CONF_WHITE_NOISE) else []),
        _section(_lights(cfg)),
        _section(_heating(cfg)),
        _section(_info_cards(templates, cfg, house, phone=True)),
        _section([_calendar_card(templates, cfg, house, cap=10)] if cfg.get(CONF_CALENDAR) else []),
        _section(_cameras(cfg, phone=True)),
        _section(media),
    ]
    return {"views": [_view(sections, 2)]}


def house_title(cfg: dict[str, Any]) -> str:
    """Return the house name, for logging and titles."""
    return (cfg.get(CONF_HOUSE_NAME) or "Home").strip()
