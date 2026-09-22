"""The 'Main' switch entity for a sync group, and the sync logic.

A group has:
  * a "Main" entity - created by this integration, a real switch entity
    with the usual helper trappings (name/icon/area/labels/category/
    enable-disable via its own entity settings);
  * an optional "linked master" - an EXISTING switch/light entity you
    already have (e.g. a physical device whose on/off can be driven by
    its own integration, an automation, or a physical button press). It
    is treated as an additional, equally-valid master: triggering it has
    the same effect as triggering Main, and Main is kept mirroring it;
  * one or more "members" - existing switch/light entities that follow
    whichever master (Main or the linked master) was triggered.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_ICON, CONF_LINKED_MASTER, CONF_MEMBERS, DEFAULT_ICON, STATE_VALUES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Main switch entity for one sync group config entry."""
    async_add_entities([SyncGroupMainSwitch(hass, entry)])


class SyncGroupMainSwitch(SwitchEntity, RestoreEntity):
    """The 'Main' entity of a sync group.

    A real, registered switch entity: it gets its own entity_id and can be
    renamed, given an icon/area/labels, and enabled or disabled through the
    normal entity settings dialog, exactly like any other helper.
    """

    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.title
        self._attr_icon = entry.options.get(CONF_ICON, entry.data.get(CONF_ICON, DEFAULT_ICON))
        self._attr_is_on = False
        self._members: list[str] = list(
            entry.options.get(CONF_MEMBERS, entry.data.get(CONF_MEMBERS, []))
        )
        self._linked_master: str | None = (
            entry.options.get(CONF_LINKED_MASTER, entry.data.get(CONF_LINKED_MASTER)) or None
        )
        # True while we are the ones commanding the linked master entity,
        # so we can tell our own echo apart from a genuine external trigger
        # on it (physical button, another integration, etc.).
        self._suppress_linked_master = False

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        # Restore last known state across HA restarts, before falling back
        # to whatever the members currently say.
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in STATE_VALUES:
            self._attr_is_on = last_state.state == "on"

        self._recompute_from_members(write_state=False)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._members, self._handle_member_change
            )
        )

        if self._linked_master:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self._linked_master], self._handle_linked_master_change
                )
            )

    # ------------------------------------------------------------------
    # Members triggering
    # ------------------------------------------------------------------

    @callback
    def _handle_member_change(self, event: Event[EventStateChangedData]) -> None:
        if not self._is_real_trigger(event):
            return
        # A genuine on <-> off trigger on a member: reflect it onto Main
        # and the linked master (if any). Other members are untouched.
        self._recompute_from_members(write_state=True)

    def _recompute_from_members(self, write_state: bool) -> None:
        """Set Main (and the linked master) from the members: on if any
        member is on, off only once every (known) member is off."""
        states = [self.hass.states.get(member_id) for member_id in self._members]
        known_values = [s.state for s in states if s is not None and s.state in STATE_VALUES]

        if not known_values:
            # Every member is unavailable/unknown right now - nothing to
            # infer the group's value from, leave everything as-is.
            return

        aggregate_value = "on" if "on" in known_values else "off"

        if self._attr_is_on != (aggregate_value == "on"):
            self._attr_is_on = aggregate_value == "on"
            if write_state:
                self.async_write_ha_state()

        if self._linked_master:
            self.hass.async_create_task(
                self._set_linked_master(aggregate_value),
                f"sync_group_ext align linked master for {self.entity_id}",
            )

    # ------------------------------------------------------------------
    # Linked master triggering
    # ------------------------------------------------------------------

    @callback
    def _handle_linked_master_change(self, event: Event[EventStateChangedData]) -> None:
        if self._suppress_linked_master:
            # This is the echo of a command we just issued - not a new,
            # externally-originated trigger.
            return
        if not self._is_real_trigger(event):
            return

        new_value = event.data["new_state"].state
        self.hass.async_create_task(
            self._broadcast_from_linked_master(new_value),
            f"sync_group_ext broadcast from linked master {self._linked_master}",
        )

    async def _broadcast_from_linked_master(self, value: str) -> None:
        """The linked master was triggered externally - mirror Main and
        push the value to every member. The linked master itself is not
        re-commanded (it's already at that value)."""
        is_on = value == "on"
        if self._attr_is_on != is_on:
            self._attr_is_on = is_on
            self.async_write_ha_state()

        await self._broadcast_to_members(value)

    # ------------------------------------------------------------------
    # Main triggering (user/automation toggles the Main entity directly)
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._broadcast_to_members("on")
        await self._set_linked_master("on")
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._broadcast_to_members("off")
        await self._set_linked_master("off")
        self._attr_is_on = False
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_real_trigger(event: Event[EventStateChangedData]) -> bool:
        """True only for a genuine on<->off flip, never for unavailable/
        unknown transitions in either direction."""
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]

        if new_state is None or new_state.state not in STATE_VALUES:
            return False
        if old_state is None or old_state.state not in STATE_VALUES:
            return False
        if old_state.state == new_state.state:
            return False
        return True

    async def _broadcast_to_members(self, value: str) -> None:
        targets: list[str] = []

        for member_id in self._members:
            member_state = self.hass.states.get(member_id)
            if member_state is None or member_state.state not in STATE_VALUES:
                continue
            if member_state.state == value:
                continue
            targets.append(member_id)

        if not targets:
            return

        await self._call_turn(targets, value)

    async def _set_linked_master(self, value: str) -> None:
        if not self._linked_master:
            return

        master_state = self.hass.states.get(self._linked_master)
        if master_state is None or master_state.state not in STATE_VALUES:
            return
        if master_state.state == value:
            return

        self._suppress_linked_master = True
        try:
            await self._call_turn([self._linked_master], value)
        finally:
            self._suppress_linked_master = False

    async def _call_turn(self, entity_ids: list[str], value: str) -> None:
        service = SERVICE_TURN_ON if value == "on" else SERVICE_TURN_OFF
        try:
            await self.hass.services.async_call(
                "homeassistant",
                service,
                {"entity_id": entity_ids},
                blocking=True,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Sync group '%s' failed to set %s to %s", self.name, entity_ids, value
            )
