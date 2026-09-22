"""Config flow for Sync Switch & Light Group (main/linked master/members model)."""
from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ICON,
    CONF_LINKED_MASTER,
    CONF_MEMBERS,
    CONF_NAME,
    DEFAULT_ICON,
    DOMAIN,
    SUPPORTED_DOMAINS,
)


def _members_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=list(SUPPORTED_DOMAINS), multiple=True)
    )


def _linked_master_selector() -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=list(SUPPORTED_DOMAINS), multiple=False)
    )


def _icon_selector() -> selector.IconSelector:
    return selector.IconSelector()


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    schema: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, "")): str,
        vol.Optional(CONF_ICON, default=defaults.get(CONF_ICON, DEFAULT_ICON)): _icon_selector(),
    }

    if defaults.get(CONF_LINKED_MASTER):
        schema[vol.Optional(CONF_LINKED_MASTER, default=defaults[CONF_LINKED_MASTER])] = (
            _linked_master_selector()
        )
    else:
        schema[vol.Optional(CONF_LINKED_MASTER)] = _linked_master_selector()

    schema[vol.Required(CONF_MEMBERS, default=defaults.get(CONF_MEMBERS, []))] = _members_selector()

    return vol.Schema(schema)


def _options_schema(current_icon: str, current_linked_master: str | None, current_members: list[str]) -> vol.Schema:
    schema: dict[Any, Any] = {vol.Optional(CONF_ICON, default=current_icon): _icon_selector()}

    if current_linked_master:
        schema[vol.Optional(CONF_LINKED_MASTER, default=current_linked_master)] = (
            _linked_master_selector()
        )
    else:
        schema[vol.Optional(CONF_LINKED_MASTER)] = _linked_master_selector()

    schema[vol.Required(CONF_MEMBERS, default=current_members)] = _members_selector()

    return vol.Schema(schema)


def _validate(linked_master: str | None, members: list[str]) -> str | None:
    if not members:
        return "need_one_member"
    if linked_master and linked_master in members:
        return "linked_master_cannot_be_member"
    return None


class SyncGroupExtConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sync Switch & Light Group."""

    VERSION = 4

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            members = user_input[CONF_MEMBERS]
            linked_master = user_input.get(CONF_LINKED_MASTER) or None
            name = user_input[CONF_NAME].strip()

            error = _validate(linked_master, members)
            if error:
                errors["base"] = error
            elif not name:
                errors["base"] = "name_required"
            else:
                # Give this config entry - and, through it, the Main entity
                # derived from it - a stable, unique identity so Home
                # Assistant can register it properly (area/labels/category/
                # enable-disable all rely on the entity having a unique_id).
                await self.async_set_unique_id(str(uuid.uuid4()))
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_ICON: user_input.get(CONF_ICON, DEFAULT_ICON),
                        CONF_LINKED_MASTER: linked_master,
                        CONF_MEMBERS: members,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SyncGroupExtOptionsFlow(config_entry)


class SyncGroupExtOptionsFlow(OptionsFlow):
    """Handle options (icon/linked master/members) for an existing sync group."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        current_icon = self._config_entry.options.get(
            CONF_ICON, self._config_entry.data.get(CONF_ICON, DEFAULT_ICON)
        )
        current_linked_master = self._config_entry.options.get(
            CONF_LINKED_MASTER, self._config_entry.data.get(CONF_LINKED_MASTER)
        )
        current_members = self._config_entry.options.get(
            CONF_MEMBERS, self._config_entry.data.get(CONF_MEMBERS, [])
        )

        if user_input is not None:
            members = user_input[CONF_MEMBERS]
            linked_master = user_input.get(CONF_LINKED_MASTER) or None

            error = _validate(linked_master, members)
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    data={
                        CONF_ICON: user_input.get(CONF_ICON, DEFAULT_ICON),
                        CONF_LINKED_MASTER: linked_master,
                        CONF_MEMBERS: members,
                    }
                )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current_icon, current_linked_master, current_members),
            errors=errors,
        )
