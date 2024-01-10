"""Config flow for Walnut integration."""
from __future__ import annotations

import logging
from typing import Any

from habluetooth import BluetoothServiceInfoBleak
import voluptuous as vol

from homeassistant.components.bluetooth.api import async_discovered_service_info
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.helpers.device_registry import format_mac

from .const import DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class WalnutConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flows for Walnut."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_advs: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user initialized flow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Create the config entry.
            # TODO: maybe make a step to name the device.
            _LOGGER.debug("User input: %s", user_input)
            device_adv = self._discovered_advs[user_input[CONF_ADDRESS]]
            await self.async_set_unique_id(
                format_mac(device_adv.address), raise_on_progress=False
            )
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=device_adv.address,
                description="This should be a description about the device location.",
                data={
                    CONF_ADDRESS: device_adv.address,
                },
            )

        self._async_discover_devices()
        # TODO: if len of _discovered_advs == 1 just select the device.

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: address
                            for address, _ in self._discovered_advs.items()
                        }
                    )
                }
            ),
            errors=errors,
        )

    @callback
    def _async_discover_devices(self) -> None:
        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass):
            address = discovery_info.address
            if (
                format_mac(address) in current_addresses
                or address in self._discovered_advs
            ):
                continue

            if SERVICE_UUID not in discovery_info.service_uuids:
                continue

            if discovery_info.manufacturer_data.get(979) is None:
                continue

            self._discovered_advs[address] = discovery_info

        if not self._discovered_advs:
            _LOGGER.debug("No devices found")
            raise AbortFlow("no_devices_found")
