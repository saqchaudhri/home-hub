"""Run the Home Hub wizard end to end and check the dashboards it builds."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import esprima
import pytest

from homeassistant import config_entries
from homeassistant.components import frontend
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.home_hub.const import DOMAIN

ANSWERS: dict[str, dict[str, Any]] = {
    "user": {"house_name": "Khan house", "owner_name": "Adam"},
    "people": {"people": ["person.adam", "person.sara"]},
    "lights": {"lights": ["light.kitchen", "light.hallway", "switch.porch_socket"]},
    "heating": {"climates": ["climate.lounge"]},
    "cameras": {
        "driveway_camera": "camera.front_garden",
        "doorbell_camera": "camera.ring_doorbell",
        "battery_sensors": ["sensor.ring_battery"],
    },
    "info": {
        "weather": "weather.home",
        "calendar": "calendar.khan_family",
        "bin_calendar": "calendar.leeds_bins",
        "prayer_times": True,
    },
    "media": {"speaker": "media_player.kitchen_speaker", "white_noise": True, "extra_media": ["media_player.lounge_tv"]},
    "doorbell": {"doorbell_sensor": "binary_sensor.ring_ding", "doorbell_tablet": "tablet-123", "doorbell_seconds": 30},
    "azan": {
        "azan": True,
        "azan_prayers": ["dhuhr", "asr", "maghrib", "isha"],
        "azan_sound": "http://example.com/adhan.mp3",
        "azan_phones": ["mobile_app_adams_phone"],
    },
    "schedules": {
        "night_mode": True,
        "night_start": "23:00:00",
        "night_end": "06:00:00",
        "outdoor_lights": ["switch.porch_socket"],
    },
    "dashboards": {
        "wall_dashboard": True,
        "phone_dashboard": True,
        "screensaver_photos": True,
        "office_door": "binary_sensor.study_door",
    },
}
# Anything from the original house must never leak into another family's dashboards.
# The original house's entity ids are read from its private dashboard exports in
# reference/ (never published) when they're present; these always apply.
_REFERENCE = Path(__file__).resolve().parent.parent / "reference"
_ORIGINAL_ENTITIES = sorted(
    {
        entity
        for export in _REFERENCE.glob("*.yaml")
        for entity in re.findall(r"\b(?:[a-z_]+)\.[a-z0-9_]+\b", export.read_text())
        if entity.split(".")[0] in {"person", "light", "switch", "camera", "sensor", "binary_sensor",
                                     "media_player", "calendar", "input_boolean", "input_select", "script"}
        # leave out actions such as media_player.play_media, which every house shares
        and not re.fullmatch(r"[a-z_]+\.(turn_on|turn_off|toggle|play_media|media_\w+|volume_\w+|select_option|reload)", entity)
    }
)
ORIGINAL_HOUSE = re.compile(
    "|".join([r"192_168", r"input_boolean\.", r"input_select\.", r"script\.stop_azan", r"kiosk_mode",
              *(re.escape(e) + r"\b" for e in _ORIGINAL_ENTITIES)]),
    re.I,
)


async def _run_wizard(hass: HomeAssistant, answers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    for step, data in answers.items():
        assert result["type"] is FlowResultType.FORM, result
        assert result["step_id"] == step
        result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    await hass.async_block_till_done()
    return result


async def _dashboard(hass: HomeAssistant, url_path: str) -> dict[str, Any]:
    return await hass.data[LOVELACE_DATA].dashboards[url_path].async_load(False)


def _all_js(obj: Any) -> list[str]:
    """Every button-card JavaScript template in a dashboard."""
    found = []
    if isinstance(obj, dict):
        for value in obj.values():
            found += _all_js(value)
    elif isinstance(obj, list):
        for value in obj:
            found += _all_js(value)
    elif isinstance(obj, str) and obj.strip().startswith("[[["):
        found.append(obj)
    return found


def _entities(obj: Any) -> set[str]:
    return set(re.findall(r"\b(?:light|switch|climate|camera|calendar|weather|media_player|person|sensor|binary_sensor)\.[a-z0-9_]+", json.dumps(obj)))


async def test_wizard_builds_both_dashboards(house: HomeAssistant) -> None:
    result = await _run_wizard(house, ANSWERS)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Khan house"

    panels = house.data[frontend.DATA_PANELS]
    assert panels["home-hub-wall"].sidebar_title == "Wall tablet"
    assert panels["home-hub-phone"].sidebar_title == "Phone"

    wall = await _dashboard(house, "home-hub-wall")
    phone = await _dashboard(house, "home-hub-phone")

    for dash in (wall, phone):
        text = json.dumps(dash)
        assert not ORIGINAL_HOUSE.search(text), ORIGINAL_HOUSE.search(text)
        assert "__" not in text.replace("window.__homeHub", ""), "a template placeholder was left unfilled"
        used = _entities(dash)
        for wanted in ("light.kitchen", "light.hallway", "switch.porch_socket", "climate.lounge",
                       "camera.front_garden", "calendar.khan_family", "weather.home",
                       "person.adam", "sensor.islamic_prayer_times_fajr_prayer"):
            assert wanted in used, f"{wanted} missing"

    # Wall tablet: three columns, screensaver with photos and the ON AIR sign wired to the study door
    view = wall["views"][0]
    assert view["max_columns"] == 3 and len(view["sections"]) == 3
    panel = wall["wallpanel"]
    assert panel["image_url"] == "media-source://media_source/local/"
    screensaver_js = panel["cards"][0]["custom_fields"]["block"]
    assert '"binary_sensor.study_door"' in screensaver_js and '"Adam"' in screensaver_js
    assert ".onair{" in panel["cards"][0]["extra_styles"]

    # Phone: the TV is only on the phone; calendar colours use the people's first names
    assert "media_player.lounge_tv" in _entities(phone)
    assert "media_player.lounge_tv" not in _entities(wall)
    calendar_js = next(js for js in _all_js(phone) if "calendars/" in js)
    assert '["adam", ' in calendar_js and '["sara", ' in calendar_js
    assert '"calendar.leeds_bins"' in calendar_js


async def test_generated_javascript_is_valid(house: HomeAssistant) -> None:
    await _run_wizard(house, ANSWERS)
    scripts = _all_js(await _dashboard(house, "home-hub-wall")) + _all_js(await _dashboard(house, "home-hub-phone"))
    assert len(scripts) >= 8
    for js in scripts:
        body = js.strip()[3:-3]  # drop [[[ ]]]
        esprima.parseScript("function card(states, entity, hass) {" + body + "}")


async def test_minimal_house(house: HomeAssistant) -> None:
    """A house with only a couple of lights and no extras still gets working dashboards."""
    answers = {step: {} for step in ANSWERS}
    answers["user"] = {"house_name": "Flat"}
    answers["lights"] = {"lights": ["light.kitchen"]}
    answers["info"] = {"prayer_times": False}
    answers["media"] = {"white_noise": False}
    answers["azan"] = {"azan": False}
    answers["schedules"] = {"night_mode": False}
    answers["dashboards"] = {"wall_dashboard": True, "phone_dashboard": True, "screensaver_photos": False}
    result = await _run_wizard(house, answers)
    assert result["type"] is FlowResultType.CREATE_ENTRY

    wall = await _dashboard(house, "home-hub-wall")
    phone = await _dashboard(house, "home-hub-phone")
    assert _entities(wall) == {"light.kitchen"}
    assert "profile_entity" not in wall["wallpanel"]
    assert "prayer" not in json.dumps(phone).lower()
    assert wall["wallpanel"]["show_images"] is False
    for dash in (wall, phone):
        for section in dash["views"][0]["sections"]:
            assert section["cards"], "empty sections should be left out"
        for js in _all_js(dash):
            esprima.parseScript("function card(states, entity, hass) {" + js.strip()[3:-3] + "}")


async def test_must_choose_a_dashboard(house: HomeAssistant) -> None:
    answers = dict(ANSWERS)
    answers["dashboards"] = {"wall_dashboard": False, "phone_dashboard": False}
    result = await _run_wizard(house, answers)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_dashboard"}


async def test_prayer_times_need_sensors(house: HomeAssistant) -> None:
    for prayer in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
        house.states.async_remove(f"sensor.islamic_prayer_times_{prayer}_prayer")
    answers = {k: v for k, v in ANSWERS.items() if k in ("user", "people", "lights", "heating", "cameras", "info")}
    result = await _run_wizard(house, answers)
    assert result["step_id"] == "info"
    assert result["errors"] == {"prayer_times": "no_prayer_sensors"}


async def test_reconfigure_rebuilds_and_removes(house: HomeAssistant) -> None:
    await _run_wizard(house, ANSWERS)
    entry = house.config_entries.async_entries(DOMAIN)[0]

    # Someone edits the phone dashboard by hand; a restart must keep the edit
    phone_store = house.data[LOVELACE_DATA].dashboards["home-hub-phone"]
    edited = await phone_store.async_load(False)
    edited["views"][0]["title"] = "Edited by hand"
    await phone_store.async_save(edited)
    assert await house.config_entries.async_reload(entry.entry_id)
    await house.async_block_till_done()
    assert (await _dashboard(house, "home-hub-phone"))["views"][0]["title"] == "Edited by hand"

    # Run the wizard again: swap the lights and drop the phone dashboard
    result = await house.config_entries.options.async_init(entry.entry_id)
    changes = {"lights": {"lights": ["switch.porch_socket"]}, "dashboards": {**ANSWERS["dashboards"], "phone_dashboard": False}}
    for step in ANSWERS:
        assert result["step_id"] == step
        # Untouched pages are submitted with what the form was prefilled with
        data = changes.get(step, ANSWERS[step])
        result = await house.config_entries.options.async_configure(result["flow_id"], data)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await house.async_block_till_done()

    wall_entities = _entities(await _dashboard(house, "home-hub-wall"))
    assert "switch.porch_socket" in wall_entities
    assert "light.kitchen" not in wall_entities
    assert "home-hub-phone" not in house.data[LOVELACE_DATA].dashboards
    assert "home-hub-phone" not in house.data[frontend.DATA_PANELS]


async def test_reconfigure_form_is_prefilled(house: HomeAssistant) -> None:
    await _run_wizard(house, ANSWERS)
    entry = house.config_entries.async_entries(DOMAIN)[0]
    result = await house.config_entries.options.async_init(entry.entry_id)
    result = await house.config_entries.options.async_configure(result["flow_id"], ANSWERS["user"])
    result = await house.config_entries.options.async_configure(result["flow_id"], ANSWERS["people"])
    schema = result["data_schema"].schema
    lights_key = next(k for k in schema if k == "lights")
    assert lights_key.description["suggested_value"] == ANSWERS["lights"]["lights"]


async def test_existing_dashboard_is_never_overwritten(house: HomeAssistant) -> None:
    """If the house already has a dashboard at the same address, Home Hub leaves it alone."""
    frontend.async_register_built_in_panel(house, "lovelace", frontend_url_path="home-hub-wall", config={"mode": "storage"})
    result = await _run_wizard(house, ANSWERS)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "home-hub-wall" not in house.data[LOVELACE_DATA].dashboards
    assert "home-hub-phone" in house.data[LOVELACE_DATA].dashboards


async def test_only_one_setup(house: HomeAssistant) -> None:
    await _run_wizard(house, ANSWERS)
    result = await house.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_removing_home_hub_deletes_its_dashboards(house: HomeAssistant) -> None:
    await _run_wizard(house, ANSWERS)
    entry = house.config_entries.async_entries(DOMAIN)[0]
    assert await house.config_entries.async_remove(entry.entry_id)
    await house.async_block_till_done()
    assert "home-hub-wall" not in house.data[frontend.DATA_PANELS]
    assert "home-hub-wall" not in house.data[LOVELACE_DATA].dashboards


async def test_rerunning_wizard_unchanged_still_rebuilds(house: HomeAssistant) -> None:
    """Running Configure again without changing anything puts back a hand-edited dashboard."""
    await _run_wizard(house, ANSWERS)
    entry = house.config_entries.async_entries(DOMAIN)[0]

    async def rerun() -> None:
        result = await house.config_entries.options.async_init(entry.entry_id)
        for step in ANSWERS:
            result = await house.config_entries.options.async_configure(result["flow_id"], ANSWERS[step])
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await house.async_block_till_done()

    await rerun()  # the answers move into the entry's options
    store = house.data[LOVELACE_DATA].dashboards["home-hub-wall"]
    edited = await store.async_load(False)
    edited["views"][0]["title"] = "Edited by hand"
    await store.async_save(edited)

    await rerun()  # same answers again
    assert (await _dashboard(house, "home-hub-wall"))["views"][0]["title"] == "Home"
