"""Look things up in the house's Home Assistant for the wizard and the builder."""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import AZAN_PLAYING, CONF_PEOPLE, DOMAIN, PRAYERS, REQUIRED_CARDS, STOP_AZAN, TABLET_MODE
from .dashboards import HouseInfo

_LOGGER = logging.getLogger(__name__)
_PRAYER_RE = re.compile(r"^sensor\..*_(" + "|".join(PRAYERS) + r")_prayer$")


def find_prayer_sensors(hass: HomeAssistant) -> list[tuple[str, str]]:
    """Return [(name, entity_id)] for the five prayers, from the Islamic Prayer Times integration."""
    found: dict[str, str] = {}
    registry = er.async_get(hass)
    candidates = [e.entity_id for e in registry.entities.values() if e.platform == "islamic_prayer_times"]
    # Fall back to entity ids alone (for example YAML-defined or renamed sensors)
    candidates += [s.entity_id for s in hass.states.async_all("sensor")]
    for entity_id in candidates:
        if (m := _PRAYER_RE.match(entity_id)) and m.group(1) not in found:
            found[m.group(1)] = entity_id
    if len(found) != len(PRAYERS):
        return []
    return [(p.capitalize(), found[p]) for p in PRAYERS]


def gather_house_info(hass: HomeAssistant, entry: ConfigEntry, cfg: dict[str, Any]) -> HouseInfo:
    """Collect what the dashboard builder needs beyond the wizard answers."""
    names = {}
    for person in cfg.get(CONF_PEOPLE) or []:
        state = hass.states.get(person)
        full = state.attributes.get("friendly_name", "") if state else person.split(".", 1)[1]
        names[person] = full.split()[0] if full else ""
    registry = er.async_get(hass)

    def own(domain: str, key: str) -> str | None:
        """The entity id of one of Home Hub's own entities, if the feature is on."""
        return registry.async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{key}")

    return HouseInfo(
        prayers=find_prayer_sensors(hass),
        person_names=names,
        azan_playing=own("binary_sensor", AZAN_PLAYING),
        stop_azan=own("button", STOP_AZAN),
        tablet_mode=own("select", TABLET_MODE),
    )


def find_tablets(hass: HomeAssistant) -> dict[str, str]:
    """Browsers registered with browser_mod, as {browser id: name}."""
    tablets = {}
    for device in dr.async_get(hass).devices.values():
        for domain, browser_id in device.identifiers:
            if domain == "browser_mod":
                tablets[browser_id] = device.name_by_user or device.name or browser_id
    return tablets


def find_phones(hass: HomeAssistant) -> dict[str, str]:
    """Phones with the Home Assistant app, as {notify service: name}."""
    services = hass.services.async_services_for_domain("notify")
    return {
        name: name.removeprefix("mobile_app_").replace("_", " ").title()
        for name in sorted(services)
        if name.startswith("mobile_app_")
    }


async def missing_cards(hass: HomeAssistant) -> list[str]:
    """Return the names of custom cards the dashboards need but that aren't installed."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        resources = hass.data[LOVELACE_DATA].resources
        await resources.async_get_info()  # makes sure the stored list is loaded
        urls = " ".join(item.get("url", "") for item in resources.async_items()).lower()
    except (KeyError, AttributeError):
        _LOGGER.debug("Could not read dashboard resources", exc_info=True)
        return []
    return [label for key, label in REQUIRED_CARDS.items() if key not in urls]
