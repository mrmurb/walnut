"""The Walnut Integration."""
from __future__ import annotations

import logging

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.api import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import CoreState, HomeAssistant

from .const import CONF_POLL_INTERVAL, DOMAIN
from .coordinator import WalnutActiveBluetoothProcessorCoordinator
from .walnut import WalnutDeviceData

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Walnut from a config entry."""
    _LOGGER.debug("Entry: %s", entry.as_dict())
    address = entry.data[CONF_ADDRESS]
    assert address is not None

    data = WalnutDeviceData()
    if CONF_POLL_INTERVAL in entry.options:
        data.set_poll_interval(entry.options.get(CONF_POLL_INTERVAL))

    def _needs_poll(
        service_info: BluetoothServiceInfoBleak, last_poll: float | None
    ) -> bool:
        _LOGGER.debug("Last poll: %s", last_poll)
        return (
            hass.state == CoreState.running
            and data.poll_needed(service_info, last_poll)
            and bool(
                async_ble_device_from_address(
                    hass, service_info.device.address, connectable=True
                )
            )
        )

    async def _async_poll(service_info: BluetoothServiceInfoBleak):
        if service_info.connectable:
            connectable_device = service_info.device
        elif device := async_ble_device_from_address(
            hass, service_info.device.address, True
        ):
            connectable_device = device
        else:
            raise RuntimeError(
                f"No connectable device found for {service_info.device.address}"
            )
        return await data.async_poll(connectable_device)

    async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        if CONF_POLL_INTERVAL in entry.options:
            data.set_poll_interval(entry.options[CONF_POLL_INTERVAL])

    coordinator = hass.data.setdefault(DOMAIN, {})[
        entry.entry_id
    ] = WalnutActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.ACTIVE,
        update_method=data.update,
        needs_poll_method=_needs_poll,
        poll_method=_async_poll,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        # only start after all platforms have had a chance to subscribe
        coordinator.async_start()
    )
    entry.async_on_unload(entry.add_update_listener(_update_listener))

    return True
