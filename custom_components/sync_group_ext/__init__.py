"""Sync Switch & Light Group (main/members model).

A "Main" switch entity is created for each configured group. It behaves
like a normal helper entity (its own entity_id, name, icon, area, labels,
enable/disable toggle, and, on Home Assistant versions that support it,
a category - all managed the standard way through the entity's settings
dialog, because it is a real registered entity with a stable unique_id).

Relationship between the Main switch and its "members" (a mix of
switch.*/light.* entities you pick):

  * Toggling Main (on or off) turns every member to the same value.
  * Toggling a member never affects the other members.
  * Toggling a member DOES update Main so it reflects reality:
      - if that leaves every member off, Main turns off;
      - if a member turns on (e.g. everything was off), Main turns on too
        - but the other members are left untouched.
  * Only on/off is ever touched - light attributes (brightness, color,
    etc.) are never synced.
  * A transition into/out of "unavailable"/"unknown" is never treated as
    a trigger and is never propagated in either direction.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a sync group from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a sync group config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change (e.g. members edited)."""
    await hass.config_entries.async_reload(entry.entry_id)
