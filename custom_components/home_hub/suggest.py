"""First-run guesses: look through the house's devices and fill in the wizard for them.

Everything here is only a suggestion shown on the wizard pages; the family can
change any of it before carrying on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from .const import (
    CONF_AZAN,
    CONF_AZAN_PHONES,
    CONF_BATTERY_SENSORS,
    CONF_BIN_CALENDAR,
    CONF_CALENDAR,
    CONF_CLIMATES,
    CONF_DOORBELL_CAMERA,
    CONF_DOORBELL_SENSOR,
    CONF_DOORBELL_TABLET,
    CONF_DRIVEWAY_CAMERA,
    CONF_EXTRA_MEDIA,
    CONF_LIGHTS,
    CONF_OFFICE_DOOR,
    CONF_OUTDOOR_LIGHTS,
    CONF_PEOPLE,
    CONF_SPEAKER,
    CONF_WEATHER,
    DOMAIN,
)
from .house import find_phones, find_prayer_sensors, find_tablets

OUTDOOR = re.compile(r"outdoor|outside|driveway|drive|porch|garden|front door|patio|security|flood", re.I)
DOORBELL = re.compile(r"doorbell|door bell|(?<![a-z])(?:ding|ring)(?![a-z])", re.I)
DRIVEWAY = re.compile(r"driveway|drive|front|garden|outdoor|outside|garage|street", re.I)
BINS = re.compile(r"\bbins?\b|waste|refuse|recycl|rubbish|collection", re.I)
NOT_FAMILY = re.compile(r"holiday|birthday|bins?\b|waste|refuse|recycl|collection|prayer|week number", re.I)
OFFICE = re.compile(r"office|study|work", re.I)
SPEAKER = re.compile(r"speaker|living|lounge|kitchen|home|sonos|echo|nest|google", re.I)
LIGHTISH = re.compile(r"light|lamp|socket|plug|bulb|led|strip", re.I)


@dataclass
class Suggestions:
    """Wizard answers guessed from the house, and a note for each page saying what was found."""

    values: dict[str, Any] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)


def _name(state: State) -> str:
    return str(state.attributes.get("friendly_name") or state.entity_id)


def _text(state: State) -> str:
    return f"{state.entity_id} {_name(state)}"


def _list(names: list[str]) -> str:
    if len(names) <= 2:
        return " and ".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


class _House:
    """The house's entities, with the hidden, disabled and Home Hub ones left out."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.entities = er.async_get(hass)
        self.devices = dr.async_get(hass)
        self.areas = ar.async_get(hass)

    def states(self, domain: str) -> list[State]:
        found = []
        for state in self.hass.states.async_all(domain):
            entry = self.entities.async_get(state.entity_id)
            if entry and (entry.hidden_by or entry.disabled_by or entry.platform == DOMAIN):
                continue
            found.append(state)
        return sorted(found, key=lambda s: (self.area(s.entity_id) or "~", _name(s).lower()))

    def area(self, entity_id: str) -> str | None:
        entry = self.entities.async_get(entity_id)
        if entry is None:
            return None
        area_id = entry.area_id
        if not area_id and entry.device_id and (device := self.devices.async_get(entry.device_id)):
            area_id = device.area_id
        area = self.areas.async_get_area(area_id) if area_id else None
        return area.name if area else None

    def device_of(self, entity_id: str) -> str | None:
        entry = self.entities.async_get(entity_id)
        return entry.device_id if entry else None


def _first(states: list[State], pattern: re.Pattern[str] | None = None) -> str | None:
    for state in states:
        if pattern is None or pattern.search(_text(state)):
            return state.entity_id
    return None


def suggest(hass: HomeAssistant) -> Suggestions:
    """Guess the wizard's answers from the devices already in Home Assistant."""
    house = _House(hass)
    out = Suggestions()
    v, notes = out.values, out.notes

    people = house.states("person")
    if people:
        v[CONF_PEOPLE] = [s.entity_id for s in people]
        notes["people"] = f"Found {_list([_name(s) for s in people])}."

    # Lights, plus sockets and switches that look like they run a light
    lights = [s for s in house.states("light") if "entity_id" not in s.attributes]  # not light groups
    sockets = [
        s for s in house.states("switch")
        if s.attributes.get("device_class") == "outlet" or LIGHTISH.search(_text(s))
    ]
    lights_and_sockets = lights + sockets
    if lights_and_sockets:
        v[CONF_LIGHTS] = [s.entity_id for s in lights_and_sockets]
        rooms = sorted({a for s in lights_and_sockets if (a := house.area(s.entity_id))})
        where = f" in {_list(rooms)}" if rooms else ""
        notes["lights"] = (
            f"Found {len(lights_and_sockets)} lights and sockets{where} and ticked them all. "
            "Remove any you don't want on the dashboards."
        )

    climates = house.states("climate")
    if climates:
        v[CONF_CLIMATES] = [s.entity_id for s in climates]
        notes["heating"] = f"Found {_list([_name(s) for s in climates])}."

    cameras = house.states("camera")
    doorbell_cam = _first(cameras, DOORBELL)
    driveway_cam = _first([s for s in cameras if s.entity_id != doorbell_cam], DRIVEWAY) or _first(
        [s for s in cameras if s.entity_id != doorbell_cam]
    )
    if driveway_cam:
        v[CONF_DRIVEWAY_CAMERA] = driveway_cam
    if doorbell_cam:
        v[CONF_DOORBELL_CAMERA] = doorbell_cam
    # Battery levels of the cameras' own devices (battery cameras and doorbells)
    camera_devices = {house.device_of(c) for c in (driveway_cam, doorbell_cam) if c} - {None}
    batteries = [
        s.entity_id
        for s in house.states("sensor")
        if s.attributes.get("device_class") == "battery" and house.device_of(s.entity_id) in camera_devices
    ]
    if batteries:
        v[CONF_BATTERY_SENSORS] = batteries
    if cameras:
        notes["cameras"] = f"Found {len(cameras)} camera{'s' if len(cameras) != 1 else ''} and picked the likeliest ones."

    if weather := _first(house.states("weather"), re.compile("home", re.I)) or _first(house.states("weather")):
        v[CONF_WEATHER] = weather
    calendars = house.states("calendar")
    if bins := _first(calendars, BINS):
        v[CONF_BIN_CALENDAR] = bins
    family = [s for s in calendars if not NOT_FAMILY.search(_text(s))]
    if family_cal := _first(family, re.compile("family|home|house", re.I)) or _first(family):
        v[CONF_CALENDAR] = family_cal

    players = house.states("media_player")
    tvs = [s for s in players if s.attributes.get("device_class") == "tv" or re.search(r"\btv\b|television", _text(s), re.I)]
    speakers = [s for s in players if s not in tvs and "entity_id" not in s.attributes]  # not speaker groups
    # The main speaker has to play a web address, for white noise and the azan
    playable = [s for s in speakers if int(s.attributes.get("supported_features") or 0) & MediaPlayerEntityFeature.PLAY_MEDIA]
    if speaker := _first(playable, SPEAKER) or _first(playable):
        v[CONF_SPEAKER] = speaker
        notes["media"] = f"Picked {_name(hass.states.get(speaker))} as the main speaker."  # type: ignore[arg-type]
    if tvs:
        v[CONF_EXTRA_MEDIA] = [s.entity_id for s in tvs]

    binary = house.states("binary_sensor")
    if doorbell := _first(binary, DOORBELL):
        v[CONF_DOORBELL_SENSOR] = doorbell
    tablets = find_tablets(hass)
    if len(tablets) == 1:
        v[CONF_DOORBELL_TABLET] = next(iter(tablets))
    doors = [s for s in binary if s.attributes.get("device_class") in ("door", "opening")]
    if office := _first(doors, OFFICE):
        v[CONF_OFFICE_DOOR] = office

    if phones := find_phones(hass):
        v[CONF_AZAN_PHONES] = list(phones)
    if find_prayer_sensors(hass) and (speaker or phones):
        v[CONF_AZAN] = True
        notes["azan"] = "Prayer times were found, so the azan is ticked. Untick it if you don't want it."

    outdoor = [s.entity_id for s in lights_and_sockets if OUTDOOR.search(_text(s)) or OUTDOOR.search(house.area(s.entity_id) or "")]
    if outdoor:
        v[CONF_OUTDOOR_LIGHTS] = outdoor
        notes["schedules"] = "Picked the lights that look like they're outside."
    return out
