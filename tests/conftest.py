"""Shared test setup: a pretend house with its own devices."""

from __future__ import annotations

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component

pytest_plugins = ["pytest_homeassistant_custom_component"]

# A pretend house with its own names and entity ids.
HOUSE_STATES = {
    "person.adam": ("home", {"friendly_name": "Adam Khan"}),
    "person.sara": ("not_home", {"friendly_name": "Sara Khan"}),
    "light.kitchen": ("off", {"friendly_name": "Kitchen"}),
    "light.hallway": ("on", {"friendly_name": "Hallway"}),
    "switch.porch_socket": ("off", {"friendly_name": "Porch"}),
    "climate.lounge": ("heat", {"friendly_name": "Lounge", "current_temperature": 20}),
    "camera.front_garden": ("idle", {"friendly_name": "Front garden"}),
    "camera.ring_doorbell": ("idle", {"friendly_name": "Ring doorbell"}),
    "sensor.ring_battery": ("88", {"friendly_name": "Ring battery", "device_class": "battery"}),
    "weather.home": ("sunny", {"friendly_name": "Home", "temperature": 14}),
    "calendar.khan_family": ("off", {"friendly_name": "Khan family"}),
    "calendar.leeds_bins": ("off", {"friendly_name": "Leeds bins"}),
    "media_player.kitchen_speaker": ("idle", {"friendly_name": "Kitchen speaker"}),
    "media_player.lounge_tv": ("off", {"friendly_name": "Lounge TV"}),
    "binary_sensor.study_door": ("on", {"friendly_name": "Study door", "device_class": "door"}),
    "binary_sensor.ring_ding": ("off", {"friendly_name": "Ring ding"}),
    "sun.sun": ("above_horizon", {}),
}
PRAYER_STATES = {
    f"sensor.islamic_prayer_times_{p}_prayer": ("2026-11-06T12:00:00+00:00", {}) for p in ("fajr", "dhuhr", "asr", "maghrib", "isha")
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load custom_components/home_hub."""
    return


@pytest.fixture
async def house(hass: HomeAssistant, calls: dict[str, list]) -> HomeAssistant:
    """Home Assistant with dashboards support and the pretend house's devices."""
    # The real frontend package isn't installed for tests; dashboards don't need it.
    hass.config.components.add("frontend")
    assert await async_setup_component(hass, "lovelace", {})
    for entity_id, (state, attrs) in {**HOUSE_STATES, **PRAYER_STATES}.items():
        hass.states.async_set(entity_id, state, attrs)
    # The wall tablet, as browser_mod registers it
    browser_mod = MockConfigEntry(domain="browser_mod")
    browser_mod.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=browser_mod.entry_id, identifiers={("browser_mod", "tablet-123")}, name="Hallway iPad"
    )
    return hass


@pytest.fixture
def calls(hass: HomeAssistant) -> dict[str, list]:
    """Pretend services the features call, recording each call."""
    services = {
        "notify": ["mobile_app_adams_phone"],
        "browser_mod": ["popup", "javascript", "close_popup"],
        "media_player": ["turn_on", "play_media", "media_stop"],
        "homeassistant": ["turn_on", "turn_off"],
    }
    return {f"{d}.{s}": async_mock_service(hass, d, s) for d, names in services.items() for s in names}
