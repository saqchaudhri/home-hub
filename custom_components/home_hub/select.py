"""Wall tablet mode: day (photo screensaver) or night (dim clock)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import TABLET_MODE
from .entity import HomeHubEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    if entry.runtime_data.night_enabled:
        async_add_entities([TabletMode(entry, TABLET_MODE)])


class TabletMode(HomeHubEntity, SelectEntity):
    _attr_icon = "mdi:theme-light-dark"
    _attr_options = ["day", "night"]

    @property
    def current_option(self) -> str:
        return self.features.tablet_mode

    async def async_select_option(self, option: str) -> None:
        self.features.set_tablet_mode(option)
