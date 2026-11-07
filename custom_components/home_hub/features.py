"""The things Home Hub does by itself: doorbell popup, azan, night mode, outdoor lights.

They run inside Home Hub rather than as automations in the house's own list,
so they are set up from the wizard and disappear cleanly when Home Hub is removed.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_utc_time,
    async_track_state_change_event,
    async_track_sunrise,
    async_track_sunset,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from .const import (
    AZAN_DEFAULT_PRAYERS,
    AZAN_MAX_MINUTES,
    AZAN_SOUND_URL,
    AZAN_STOP_ACTION,
    CONF_AZAN,
    CONF_AZAN_PHONES,
    CONF_AZAN_PRAYERS,
    CONF_AZAN_SOUND,
    CONF_DOORBELL_CAMERA,
    CONF_DOORBELL_SECONDS,
    CONF_DOORBELL_SENSOR,
    CONF_DOORBELL_TABLET,
    CONF_DRIVEWAY_CAMERA,
    CONF_NIGHT_END,
    CONF_NIGHT_MODE,
    CONF_NIGHT_START,
    CONF_OUTDOOR_LIGHTS,
    CONF_SPEAKER,
    DOORBELL_DEFAULT_SECONDS,
    SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

NIGHT_START = "23:00:00"
NIGHT_END = "06:00:00"
# Wakes WallPanel's screensaver so the popup is seen straight away
WAKE_TABLET_JS = (
    "const wp = document.querySelector('home-assistant')?.shadowRoot"
    "?.querySelector('home-assistant-main')?.shadowRoot?.querySelector('wallpanel-view');"
    " if (wp && wp.stopScreensaver) wp.stopScreensaver();"
)


def _parse_time(value: str | None, fallback: str) -> time:
    return dt_util.parse_time(value or fallback) or dt_util.parse_time(fallback)  # type: ignore[return-value]


def is_night(now: datetime, start: time, end: time) -> bool:
    """Whether `now` falls in the night window, which may run past midnight."""
    t = now.time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end


class Features:
    """Runs the chosen features for one Home Hub setup."""

    def __init__(self, hass: HomeAssistant, cfg: dict[str, Any], prayers: list[tuple[str, str]]) -> None:
        self.hass = hass
        self.cfg = cfg
        self._unsubs: list[CALLBACK_TYPE] = []
        self._prayer_timers: dict[str, CALLBACK_TYPE] = {}
        self._azan_safety: CALLBACK_TYPE | None = None
        self._doorbell_task: asyncio.Task | None = None

        speaker = cfg.get(CONF_SPEAKER)
        phones = cfg.get(CONF_AZAN_PHONES) or []
        chosen = cfg.get(CONF_AZAN_PRAYERS) or AZAN_DEFAULT_PRAYERS
        self.azan_prayers = [(name, entity) for name, entity in prayers if name.lower() in chosen]
        self.azan_enabled = bool(cfg.get(CONF_AZAN) and self.azan_prayers and (speaker or phones))
        self.azan_playing = False

        self.night_enabled = bool(cfg.get(CONF_NIGHT_MODE))
        self.night_start = _parse_time(cfg.get(CONF_NIGHT_START), NIGHT_START)
        self.night_end = _parse_time(cfg.get(CONF_NIGHT_END), NIGHT_END)
        self.tablet_mode = "day"

        self.doorbell_enabled = bool(
            cfg.get(CONF_DOORBELL_SENSOR)
            and cfg.get(CONF_DOORBELL_TABLET)
            and (cfg.get(CONF_DRIVEWAY_CAMERA) or cfg.get(CONF_DOORBELL_CAMERA))
        )
        self.outdoor_lights: list[str] = cfg.get(CONF_OUTDOOR_LIGHTS) or []

    # ---- lifecycle -------------------------------------------------------

    @callback
    def start(self) -> None:
        if self.azan_enabled:
            self._start_azan()
        if self.night_enabled:
            self._start_night_mode()
        if self.doorbell_enabled:
            self._unsubs.append(
                async_track_state_change_event(self.hass, [self.cfg[CONF_DOORBELL_SENSOR]], self._doorbell_changed)
            )
        if self.outdoor_lights:
            self._start_outdoor_lights()
        self._changed()  # the entities were added before the features worked out their state

    @callback
    def stop(self) -> None:
        for unsub in [*self._unsubs, *self._prayer_timers.values()]:
            unsub()
        self._unsubs.clear()
        self._prayer_timers.clear()
        if self._azan_safety:
            self._azan_safety()
            self._azan_safety = None
        if self._doorbell_task:
            self._doorbell_task.cancel()

    @callback
    def _changed(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    # ---- azan ------------------------------------------------------------

    def _start_azan(self) -> None:
        entities = [entity for _name, entity in self.azan_prayers]
        for name, entity in self.azan_prayers:
            self._schedule_prayer(name, entity)
        self._unsubs.append(async_track_state_change_event(self.hass, entities, self._prayer_time_changed))
        if speaker := self.cfg.get(CONF_SPEAKER):
            self._unsubs.append(async_track_state_change_event(self.hass, [speaker], self._speaker_changed))
        self._unsubs.append(self.hass.bus.async_listen("mobile_app_notification_action", self._notification_action))

    def _schedule_prayer(self, name: str, entity: str) -> None:
        if cancel := self._prayer_timers.pop(entity, None):
            cancel()
        state = self.hass.states.get(entity)
        when = dt_util.parse_datetime(state.state) if state else None
        if when is None or when <= dt_util.utcnow():
            return

        @callback
        def _due(_now: datetime) -> None:
            self._prayer_timers.pop(entity, None)
            self.hass.async_create_task(self.play_azan(name))

        self._prayer_timers[entity] = async_track_point_in_utc_time(self.hass, _due, dt_util.as_utc(when))

    @callback
    def _prayer_time_changed(self, event: Event[EventStateChangedData]) -> None:
        entity = event.data["entity_id"]
        name = next(n for n, e in self.azan_prayers if e == entity)
        self._schedule_prayer(name, entity)

    async def play_azan(self, prayer: str) -> None:
        """Play the azan on the main speaker and tell the family's phones."""
        speaker = self.cfg.get(CONF_SPEAKER)
        playing = False
        if speaker:
            target = {"entity_id": speaker}
            try:
                await self.hass.services.async_call("media_player", "turn_on", target, blocking=True)
            except Exception:  # noqa: BLE001 - some speakers don't support turn_on
                _LOGGER.debug("Could not turn on %s", speaker, exc_info=True)
            try:
                await self.hass.services.async_call(
                    "media_player",
                    "play_media",
                    {
                        **target,
                        "media_content_id": self.cfg.get(CONF_AZAN_SOUND) or AZAN_SOUND_URL,
                        "media_content_type": "music",
                    },
                    blocking=True,
                )
                playing = True
                self._set_azan_playing(True)
            except Exception:  # noqa: BLE001 - still tell the phones
                _LOGGER.warning("Could not play the azan on %s", speaker, exc_info=True)
        for phone in self.cfg.get(CONF_AZAN_PHONES) or []:
            data: dict[str, Any] = {"title": "Azan", "message": f"It's time for {prayer}"}
            if playing:
                data["data"] = {
                    "tag": "home_hub_azan",
                    "actions": [{"action": AZAN_STOP_ACTION, "title": "Mute azan", "destructive": True}],
                }
            try:
                await self.hass.services.async_call("notify", phone, data, blocking=True)
            except Exception:  # noqa: BLE001 - one phone failing mustn't stop the others
                _LOGGER.warning("Could not send the azan notification to %s", phone, exc_info=True)

    async def stop_azan(self) -> None:
        """Stop the speaker, but only if it is the azan that's playing."""
        if not self.azan_playing:
            return
        if speaker := self.cfg.get(CONF_SPEAKER):
            try:
                await self.hass.services.async_call("media_player", "media_stop", {"entity_id": speaker}, blocking=True)
            except Exception:  # noqa: BLE001
                _LOGGER.warning("Could not stop %s", speaker, exc_info=True)
        self._set_azan_playing(False)

    @callback
    def _set_azan_playing(self, playing: bool) -> None:
        if self._azan_safety:
            self._azan_safety()
            self._azan_safety = None
        self.azan_playing = playing
        if playing:
            self._azan_safety = async_call_later(
                self.hass, timedelta(minutes=AZAN_MAX_MINUTES), callback(lambda _now: self._set_azan_playing(False))
            )
        self._changed()

    @callback
    def _speaker_changed(self, event: Event[EventStateChangedData]) -> None:
        old, new = event.data["old_state"], event.data["new_state"]
        if self.azan_playing and old and old.state == "playing" and (new is None or new.state != "playing"):
            self._set_azan_playing(False)

    @callback
    def _notification_action(self, event: Event) -> None:
        if event.data.get("action") == AZAN_STOP_ACTION:
            self.hass.async_create_task(self.stop_azan())

    # ---- night mode ------------------------------------------------------

    def _start_night_mode(self) -> None:
        self.tablet_mode = "night" if is_night(dt_util.now(), self.night_start, self.night_end) else "day"
        for when, mode in ((self.night_start, "night"), (self.night_end, "day")):
            self._unsubs.append(
                async_track_time_change(
                    self.hass,
                    callback(lambda _now, mode=mode: self.set_tablet_mode(mode)),
                    hour=when.hour,
                    minute=when.minute,
                    second=when.second,
                )
            )

    @callback
    def set_tablet_mode(self, mode: str) -> None:
        self.tablet_mode = mode
        self._changed()

    # ---- doorbell --------------------------------------------------------

    @callback
    def _doorbell_changed(self, event: Event[EventStateChangedData]) -> None:
        new = event.data["new_state"]
        if new is None or new.state != "on":
            return
        if self._doorbell_task and not self._doorbell_task.done():
            self._doorbell_task.cancel()  # rung again: start the 30 seconds over
        self._doorbell_task = self.hass.async_create_background_task(self.show_doorbell(), "home_hub_doorbell")

    async def show_doorbell(self) -> None:
        """Show the camera full screen on the wall tablet, then close it."""
        tablet = [self.cfg[CONF_DOORBELL_TABLET]]
        camera = self.cfg.get(CONF_DRIVEWAY_CAMERA) or self.cfg.get(CONF_DOORBELL_CAMERA)
        seconds = int(self.cfg.get(CONF_DOORBELL_SECONDS) or DOORBELL_DEFAULT_SECONDS)
        if not self.hass.services.has_service("browser_mod", "popup"):
            _LOGGER.warning("The doorbell popup needs browser_mod, which isn't installed")
            return
        try:
            await self.hass.services.async_call(
                "browser_mod", "javascript", {"browser_id": tablet, "code": WAKE_TABLET_JS}, blocking=True
            )
        except Exception:  # noqa: BLE001 - the popup still works without it
            _LOGGER.debug("Could not wake the tablet's screensaver", exc_info=True)
        await asyncio.sleep(0.8)
        await self.hass.services.async_call(
            "browser_mod",
            "popup",
            {
                "browser_id": tablet,
                "title": "Someone at the door",
                "size": "fullscreen",  # browser_mod 2
                "initial_style": "fullscreen",  # browser_mod 3
                "dismissable": True,
                "autoclose": False,
                "content": {
                    "type": "picture-entity",
                    "entity": camera,
                    "camera_view": "live",
                    "fit_mode": "cover",
                    "show_name": False,
                    "show_state": False,
                },
            },
            blocking=True,
        )
        # browser_mod's own timeout doesn't fire on iPads, so close it here
        await asyncio.sleep(seconds)
        await self.hass.services.async_call("browser_mod", "close_popup", {"browser_id": tablet}, blocking=True)

    # ---- outdoor lights --------------------------------------------------

    def _start_outdoor_lights(self) -> None:
        self._unsubs.append(async_track_sunset(self.hass, callback(lambda: self._outdoor(True))))
        self._unsubs.append(async_track_sunrise(self.hass, callback(lambda: self._outdoor(False))))
        self._unsubs.append(
            async_track_state_change_event(self.hass, self.outdoor_lights, self._outdoor_light_changed)
        )
        # Put them right after a restart or power cut
        self.hass.async_create_task(self._outdoor_now())

    def _dark(self) -> bool:
        sun = self.hass.states.get("sun.sun")
        return sun is not None and sun.state == "below_horizon"

    async def _outdoor_now(self, lights: list[str] | None = None) -> None:
        await self._switch(lights or self.outdoor_lights, self._dark())

    @callback
    def _outdoor(self, on: bool) -> None:
        self.hass.async_create_task(self._switch(self.outdoor_lights, on))

    @callback
    def _outdoor_light_changed(self, event: Event[EventStateChangedData]) -> None:
        old = event.data["old_state"]
        if old is not None and old.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            # The socket came back (for example after a power cut): put it right
            self.hass.async_create_task(self._outdoor_now([event.data["entity_id"]]))

    async def _switch(self, entities: list[str], on: bool) -> None:
        await self.hass.services.async_call(
            "homeassistant", "turn_on" if on else "turn_off", {"entity_id": entities}, blocking=False
        )
