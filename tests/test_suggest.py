"""The wizard's first-run guesses about which devices are which."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from custom_components.home_hub.const import DOMAIN
from custom_components.home_hub.suggest import suggest


def _add(hass: HomeAssistant, eid: str, state: str, area: str | None = None, device: str | None = None, **attrs) -> None:
    """Add an entity as an integration would: in the registry, optionally on a device in a room."""
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    device_id = None
    if device or area:
        dev = dr.async_get(hass).async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={("test", device or eid)}, name=device or eid
        )
        if area:
            area_id = (ar.async_get(hass).async_get_area_by_name(area) or ar.async_get(hass).async_create(area)).id
            dr.async_get(hass).async_update_device(dev.id, area_id=area_id)
        device_id = dev.id
    domain, object_id = eid.split(".")
    er.async_get(hass).async_get_or_create(
        domain, "test", eid, suggested_object_id=object_id, config_entry=entry, device_id=device_id
    )
    hass.states.async_set(eid, state, attrs)


async def test_guesses_a_typical_house(hass: HomeAssistant) -> None:
    _add(hass, "person.yusuf", "home", friendly_name="Yusuf Ahmed")
    _add(hass, "light.kitchen_ceiling", "off", "Kitchen", friendly_name="Kitchen ceiling")
    _add(hass, "light.lounge_lamp", "on", "Lounge", friendly_name="Lounge lamp")
    _add(hass, "light.all_downstairs", "on", friendly_name="Downstairs", entity_id=["light.kitchen_ceiling"])  # a group
    _add(hass, "switch.porch_plug", "off", "Porch", device_class="outlet", friendly_name="Porch plug")
    _add(hass, "switch.dishwasher_child_lock", "off", friendly_name="Dishwasher child lock")  # not a light
    _add(hass, "climate.hive", "heat", friendly_name="Hive")
    _add(hass, "camera.front_drive", "idle", friendly_name="Front drive")
    _add(hass, "camera.ring_doorbell", "idle", device="Ring", friendly_name="Ring doorbell")
    _add(hass, "sensor.ring_battery", "70", device="Ring", device_class="battery")
    _add(hass, "sensor.phone_battery", "50", device="Phone", device_class="battery")  # not a camera's
    _add(hass, "weather.forecast_home", "sunny")
    _add(hass, "calendar.uk_holidays", "off", friendly_name="UK holidays")
    _add(hass, "calendar.bin_collection", "off", friendly_name="Bin collection")
    _add(hass, "calendar.ahmed_family", "off", friendly_name="Ahmed family")
    _add(hass, "media_player.living_room_tv", "off", device_class="tv", friendly_name="Living room TV")
    _add(hass, "media_player.kitchen_speaker", "idle", friendly_name="Kitchen speaker", supported_features=512)
    _add(hass, "media_player.lounge_speaker", "idle", friendly_name="Lounge speaker", supported_features=0)  # can't play a web address
    for prayer in ("fajr", "dhuhr", "asr", "maghrib", "isha"):
        _add(hass, f"sensor.islamic_prayer_times_{prayer}_prayer", "2026-11-07T12:00:00+00:00")
    _add(hass, "binary_sensor.ring_ding", "off", friendly_name="Ring ding")
    _add(hass, "binary_sensor.monitoring_active", "on", friendly_name="Monitoring active")  # "ring" inside a word
    _add(hass, "binary_sensor.study_door", "on", device_class="door", friendly_name="Study door")

    guesses = suggest(hass)
    v = guesses.values
    assert v["people"] == ["person.yusuf"]
    assert v["lights"] == ["light.kitchen_ceiling", "light.lounge_lamp", "switch.porch_plug"]
    assert v["climates"] == ["climate.hive"]
    assert v["driveway_camera"] == "camera.front_drive"
    assert v["doorbell_camera"] == "camera.ring_doorbell"
    assert v["battery_sensors"] == ["sensor.ring_battery"]
    assert v["weather"] == "weather.forecast_home"
    assert v["calendar"] == "calendar.ahmed_family"
    assert v["bin_calendar"] == "calendar.bin_collection"
    assert v["speaker"] == "media_player.kitchen_speaker"
    assert v["azan"] is True
    assert v["extra_media"] == ["media_player.living_room_tv"]
    assert v["doorbell_sensor"] == "binary_sensor.ring_ding"
    assert v["office_door"] == "binary_sensor.study_door"
    assert v["outdoor_lights"] == ["switch.porch_plug"]
    assert guesses.notes["lights"].startswith("Found 3 lights and sockets in Kitchen, Lounge and Porch")


async def test_empty_house_guesses_nothing(hass: HomeAssistant) -> None:
    assert suggest(hass).values == {}


async def test_wizard_starts_with_the_guesses(house: HomeAssistant) -> None:
    """The first page says it has filled things in, and later pages arrive prefilled."""
    result = await house.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert "best guesses" in result["description_placeholders"]["found"]
    result = await house.config_entries.flow.async_configure(result["flow_id"], {"house_name": "Khan house"})
    assert result["step_id"] == "people"
    people = next(k for k in result["data_schema"].schema if k == "people")
    assert people.description["suggested_value"] == ["person.adam", "person.sara"]
    result = await house.config_entries.flow.async_configure(result["flow_id"], {"people": ["person.adam"]})
    lights = next(k for k in result["data_schema"].schema if k == "lights")
    assert "light.kitchen" in lights.description["suggested_value"]
    assert result["description_placeholders"]["found"].startswith("Found")
