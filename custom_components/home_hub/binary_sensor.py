"""Azan playing: on while the azan plays, so the dashboards can show a Stop button."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import AZAN_PLAYING
from .entity import HomeHubEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.runtime_data.azan_enabled:
        async_add_entities([AzanPlaying(entry, AZAN_PLAYING)])


class AzanPlaying(HomeHubEntity, BinarySensorEntity):
    _attr_icon = "mdi:mosque"

    @property
    def is_on(self) -> bool:
        return self.features.azan_playing
