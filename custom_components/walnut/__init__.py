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

from .const import DOMAIN
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

    def _update_method(data: BluetoothServiceInfoBleak) -> dict[str, float | int]:
        sensor_values: dict[str, float] = {}
        # TODO: maybe not use strings?
        sensor_values["address"] = data.address
        sensor_values["rssi"] = data.advertisement.rssi

        idx = 0
        while idx < len(data.manufacturer_data.get(0x03D3)):
            sensor_and_data = data.manufacturer_data.get(0x03D3)[idx : idx + 4]
            sensor_id = int.from_bytes(sensor_and_data[0:2], "big")
            sensor_data = sensor_and_data[2:4]

            if sensor_id == 1:  # Temperature
                sensor_values["temperature"] = (
                    int.from_bytes(sensor_data, "big", signed=True) / 10
                )
            elif sensor_id == 2:
                sensor_values["humidity"] = int.from_bytes(sensor_data, "big") / 10

            idx += 4

        return sensor_values

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

    return True
