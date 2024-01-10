"""Walnut coordinator."""
import logging

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from homeassistant.components.bluetooth.models import BluetoothChange
from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)


class WalnutActiveBluetoothProcessorCoordinator(ActiveBluetoothProcessorCoordinator):
    """Walnut coordinator. Why is this even needed."""

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        if 979 not in service_info.manufacturer_data:
            _LOGGER.debug("No manufacturer data found, skipping service_info update.")
            return

        super()._async_handle_bluetooth_event(service_info, change)
