"""The things Home Hub does by itself: azan, doorbell popup, night mode, outdoor lights."""

from __future__ import annotations

from datetime import timedelta
import json
from typing import Any

import esprima
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.sun import get_astral_event_next
from homeassistant.util import dt as dt_util

from custom_components.home_hub.const import AZAN_STOP_ACTION, DOMAIN

from .test_wizard import ANSWERS, _all_js, _dashboard, _run_wizard

AZAN = "binary_sensor.home_hub_azan_playing"
STOP = "button.home_hub_stop_azan"
MODE = "select.home_hub_wall_tablet_mode"


def _answers(until: str, **pages: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The test answers with some pages changed, stopping after page `until`."""
    steps = list(ANSWERS)[: list(ANSWERS).index(until) + 1]
    return {step: {**ANSWERS[step], **pages.get(step, {})} for step in steps}


def _ids(value: str | list[str]) -> list[str]:
    return [value] if isinstance(value, str) else list(value)


async def _later(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **delta: float) -> None:
    freezer.tick(timedelta(**delta))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_dashboards_get_stop_azan_and_night_clock(house: HomeAssistant) -> None:
    await _run_wizard(house, ANSWERS)
    wall = await _dashboard(house, "home-hub-wall")
    phone = await _dashboard(house, "home-hub-phone")

    # Tablet: the Stop azan button only appears while the azan plays
    stop = wall["views"][0]["sections"][0]["cards"][1]
    assert stop["type"] == "conditional"
    assert stop["conditions"] == [{"condition": "state", "entity": AZAN, "state": "on"}]
    assert stop["card"]["tap_action"]["target"] == {"entity_id": STOP}
    # Phone: always there, just under the prayer times
    info = json.dumps(phone["views"][0]["sections"])
    assert f'"entity_id": "{STOP}"' in info

    # Night mode switches the screensaver to the dim clock
    panel = wall["wallpanel"]
    assert panel["profile_entity"] == MODE
    night = panel["profiles"]["night"]
    assert night["show_images"] is False
    clock = night["cards"][0]["custom_fields"]["block"]
    assert "sensor.islamic_prayer_times_dhuhr_prayer" in clock
    for js in _all_js(wall):
        esprima.parseScript("function card(states, entity, hass) {" + js.strip()[3:-3] + "}")


async def test_azan_plays_notifies_and_stops(house: HomeAssistant, calls: dict[str, list], freezer: FrozenDateTimeFactory) -> None:
    await _run_wizard(house, ANSWERS)
    assert house.states.get(AZAN).state == "off"

    soon = dt_util.utcnow() + timedelta(minutes=1)
    house.states.async_set("sensor.islamic_prayer_times_dhuhr_prayer", soon.isoformat())
    await house.async_block_till_done()
    await _later(house, freezer, minutes=1, seconds=1)

    play = calls["media_player.play_media"][-1].data
    assert _ids(play["entity_id"]) == ["media_player.kitchen_speaker"]
    assert play["media_content_id"] == "http://example.com/adhan.mp3"
    note = calls["notify.mobile_app_adams_phone"][-1].data
    assert note["message"] == "It's time for Dhuhr"
    assert note["data"]["actions"][0]["action"] == AZAN_STOP_ACTION
    assert house.states.get(AZAN).state == "on"

    # Tapping "Mute azan" on the phone stops it
    house.bus.async_fire("mobile_app_notification_action", {"action": AZAN_STOP_ACTION})
    await house.async_block_till_done()
    assert _ids(calls["media_player.media_stop"][-1].data["entity_id"]) == ["media_player.kitchen_speaker"]
    assert house.states.get(AZAN).state == "off"


async def test_fajr_is_left_out_by_default(house: HomeAssistant, calls: dict[str, list], freezer: FrozenDateTimeFactory) -> None:
    await _run_wizard(house, ANSWERS)
    house.states.async_set("sensor.islamic_prayer_times_fajr_prayer", (dt_util.utcnow() + timedelta(minutes=1)).isoformat())
    await house.async_block_till_done()
    await _later(house, freezer, minutes=2)
    assert not calls["media_player.play_media"]


async def test_stop_button_only_stops_the_azan(house: HomeAssistant, calls: dict[str, list], freezer: FrozenDateTimeFactory) -> None:
    await _run_wizard(house, ANSWERS)
    # Nothing playing: pressing Stop azan leaves the speaker alone (it might be playing music)
    await house.services.async_call("button", "press", {"entity_id": STOP}, blocking=True)
    assert not calls["media_player.media_stop"]

    features = house.config_entries.async_entries(DOMAIN)[0].runtime_data
    await features.play_azan("Asr")
    await house.async_block_till_done()
    await house.services.async_call("button", "press", {"entity_id": STOP}, blocking=True)
    assert len(calls["media_player.media_stop"]) == 1
    assert house.states.get(AZAN).state == "off"


async def test_azan_finishes_by_itself(house: HomeAssistant, calls: dict[str, list], freezer: FrozenDateTimeFactory) -> None:
    await _run_wizard(house, ANSWERS)
    features = house.config_entries.async_entries(DOMAIN)[0].runtime_data

    # The speaker reports it stopped
    await features.play_azan("Asr")
    house.states.async_set("media_player.kitchen_speaker", "playing")
    await house.async_block_till_done()
    house.states.async_set("media_player.kitchen_speaker", "idle")
    await house.async_block_till_done()
    assert house.states.get(AZAN).state == "off"

    # The speaker never says: give up after 6 minutes
    await features.play_azan("Isha")
    await house.async_block_till_done()
    assert house.states.get(AZAN).state == "on"
    await _later(house, freezer, minutes=6, seconds=1)
    assert house.states.get(AZAN).state == "off"


async def test_doorbell_shows_camera_on_tablet(house: HomeAssistant, calls: dict[str, list], freezer: FrozenDateTimeFactory) -> None:
    await _run_wizard(house, ANSWERS)
    house.states.async_set("binary_sensor.ring_ding", "on")
    await house.async_block_till_done()
    await _later(house, freezer, seconds=1)

    assert calls["browser_mod.javascript"][-1].data["browser_id"] == ["tablet-123"]
    popup = calls["browser_mod.popup"][-1].data
    assert popup["browser_id"] == ["tablet-123"]
    assert popup["content"]["entity"] == "camera.front_garden"
    assert popup["content"]["camera_view"] == "live"
    assert popup["size"] == popup["initial_style"] == "fullscreen"
    assert not calls["browser_mod.close_popup"]

    await _later(house, freezer, seconds=30)
    assert calls["browser_mod.close_popup"][-1].data["browser_id"] == ["tablet-123"]


async def test_night_mode(house: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(dt_util.start_of_local_day() + timedelta(hours=22, minutes=59, seconds=50))
    await _run_wizard(house, ANSWERS)
    assert house.states.get(MODE).state == "day"
    await _later(house, freezer, seconds=11)
    assert house.states.get(MODE).state == "night"
    await _later(house, freezer, hours=7)
    assert house.states.get(MODE).state == "day"


async def test_night_mode_after_restart_at_night(house: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(dt_util.start_of_local_day() + timedelta(hours=2))
    await _run_wizard(house, ANSWERS)
    assert house.states.get(MODE).state == "night"


async def test_outdoor_lights(house: HomeAssistant, calls: dict[str, list], freezer: FrozenDateTimeFactory) -> None:
    await _run_wizard(house, ANSWERS)
    # Daytime when Home Hub starts: put them off
    assert _ids(calls["homeassistant.turn_off"][-1].data["entity_id"]) == ["switch.porch_socket"]

    sunset = get_astral_event_next(house, "sunset")
    freezer.move_to(sunset + timedelta(seconds=1))
    async_fire_time_changed(house, sunset + timedelta(seconds=1))
    await house.async_block_till_done()
    assert _ids(calls["homeassistant.turn_on"][-1].data["entity_id"]) == ["switch.porch_socket"]

    # After a power cut the socket comes back off; at night it goes straight back on
    house.states.async_set("sun.sun", "below_horizon")
    house.states.async_set("switch.porch_socket", "unavailable")
    await house.async_block_till_done()
    count = len(calls["homeassistant.turn_on"])
    house.states.async_set("switch.porch_socket", "off")
    await house.async_block_till_done()
    assert len(calls["homeassistant.turn_on"]) == count + 1


async def test_doorbell_needs_a_tablet(house: HomeAssistant) -> None:
    result = await _run_wizard(house, _answers("doorbell", doorbell={"doorbell_tablet": ""}))
    assert result["step_id"] == "doorbell"
    assert result["errors"] == {"doorbell_tablet": "need_tablet"}


async def test_azan_needs_a_speaker_or_phone(house: HomeAssistant) -> None:
    answers = _answers("azan", azan={"azan_phones": []})
    del answers["media"]["speaker"]
    result = await _run_wizard(house, answers)
    assert result["step_id"] == "azan"
    assert result["errors"] == {"azan": "need_speaker_or_phone"}


async def test_turning_features_off_removes_them(house: HomeAssistant) -> None:
    await _run_wizard(house, ANSWERS)
    entry = house.config_entries.async_entries(DOMAIN)[0]
    result = await house.config_entries.options.async_init(entry.entry_id)
    changes = {"azan": {**ANSWERS["azan"], "azan": False}, "schedules": {**ANSWERS["schedules"], "night_mode": False}}
    for step in ANSWERS:
        result = await house.config_entries.options.async_configure(result["flow_id"], changes.get(step, ANSWERS[step]))
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await house.async_block_till_done()

    registry = er.async_get(house)
    for entity_id in (AZAN, STOP, MODE):
        assert registry.async_get(entity_id) is None
    wall = json.dumps(await _dashboard(house, "home-hub-wall"))
    assert "home_hub_azan" not in wall and "profile_entity" not in wall


async def test_upgrade_prefills_new_pages(house: HomeAssistant) -> None:
    """A Home Hub set up before stage 2 gets sensible starting values on the new pages."""
    stage1 = {k: v for k, v in ANSWERS.items() if k not in ("doorbell", "azan", "schedules")}
    data: dict[str, Any] = {}
    for page in stage1.values():
        data |= page
    entry = MockConfigEntry(domain=DOMAIN, title="Khan house", data=data)
    entry.add_to_hass(house)
    assert await house.config_entries.async_setup(entry.entry_id)
    await house.async_block_till_done()

    result = await house.config_entries.options.async_init(entry.entry_id)
    for step in ANSWERS:
        if step == "azan":
            schema = {str(k): k for k in result["data_schema"].schema}
            assert schema["azan_prayers"].description["suggested_value"] == ["dhuhr", "asr", "maghrib", "isha"]
            assert schema["azan_sound"].description["suggested_value"].startswith("http")
            break
        result = await house.config_entries.options.async_configure(result["flow_id"], {})


async def test_phones_still_told_if_speaker_fails(house: HomeAssistant, calls: dict[str, list]) -> None:
    await _run_wizard(house, ANSWERS)
    house.services.async_remove("media_player", "play_media")  # the speaker can't play it
    features = house.config_entries.async_entries(DOMAIN)[0].runtime_data
    await features.play_azan("Maghrib")
    await house.async_block_till_done()
    note = calls["notify.mobile_app_adams_phone"][-1].data
    assert note["message"] == "It's time for Maghrib"
    assert "data" not in note  # no Mute button when nothing is playing
    assert house.states.get(AZAN).state == "off"
