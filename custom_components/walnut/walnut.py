import logging  # noqa: D100

from bleak import BleakError, BLEDevice
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
    retry_bluetooth_connection_error,
)
from bluetooth_data_tools import short_address
from bluetooth_sensor_state_data import BluetoothData
from home_assistant_bluetooth import BluetoothServiceInfo
from sensor_state_data import SensorDeviceClass, SensorUpdate, Units
from sensor_state_data.enum import StrEnum

from .const import BATTERY_CHARACTERISTIC

_LOGGER = logging.getLogger(__name__)


class WalnutSensor(StrEnum):
    """Walnut sensor."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    SIGNAL_STRENGTH = "signal_strength"
    BATTERY = "battery"


class WalnutDeviceData(BluetoothData):  # noqa: D101
    def __init__(self):  # noqa: D107
        super().__init__()

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""
        _LOGGER.debug("Parsing Walnut BLE adv data.")

        address = service_info.address
        manufacturer_data = service_info.manufacturer_data
        if 0x03D3 not in manufacturer_data:
            return None

        data = manufacturer_data[0x03D3]
        self.set_device_manufacturer("Sigma")
        self.set_device_name(f"Walnut {short_address(address)}")
        _LOGGER.debug("Parsing Walnut manufacturer data: %s", data)

        self.update_sensor(
            str(WalnutSensor.SIGNAL_STRENGTH),
            Units.SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
            service_info.rssi,
            SensorDeviceClass.SIGNAL_STRENGTH,
            "Signal Strength",
        )

        idx = 0
        while idx < len(data):
            sensor_and_data = data[idx : idx + 4]
            sensor_id = int.from_bytes(sensor_and_data[0:2], "big")
            sensor_data = sensor_and_data[2:4]
            if sensor_id == 1:
                temperature = int.from_bytes(sensor_data, "big", signed=True) / 10
                self.update_sensor(
                    str(WalnutSensor.TEMPERATURE),
                    Units.TEMP_CELSIUS,
                    temperature,
                    SensorDeviceClass.TEMPERATURE,
                    "Temperature",
                )
            elif sensor_id == 2:
                humidity = int.from_bytes(sensor_data, "big") / 10
                self.update_sensor(
                    str(WalnutSensor.HUMIDITY),
                    Units.PERCENTAGE,
                    humidity,
                    SensorDeviceClass.HUMIDITY,
                    "Humidity",
                )
            idx += 4

    def poll_needed(  # noqa: D102
        self, service_info: BluetoothServiceInfo, last_poll: float | None
    ) -> bool:
        if last_poll is None:
            return True
        return last_poll > 10  # TODO: what is a good time? maybe config value.

    async def async_poll(self, ble_device: BLEDevice) -> SensorUpdate:  # noqa: D102
        _LOGGER.debug("Polling Walnut device: %s", ble_device.address)
        client = await establish_connection(
            BleakClientWithServiceCache, ble_device, ble_device.address
        )
        try:
            await self._get_payload(client)
        except BleakError as e:
            _LOGGER.warning("Failed to connect to %s: %s", ble_device, e)
        finally:
            await client.disconnect()
        return self._finish_update()

    @retry_bluetooth_connection_error()
    async def _get_payload(self, client: BleakClientWithServiceCache) -> None:
        """Get the payload from the brush using its gatt_characteristics."""
        battery_char = client.services.get_characteristic(BATTERY_CHARACTERISTIC)
        battery_payload = await client.read_gatt_char(battery_char)
        self.update_sensor(
            str(WalnutSensor.BATTERY),
            Units.PERCENTAGE,
            battery_payload[0],
            SensorDeviceClass.BATTERY,
            "Battery",
        )
        _LOGGER.debug("Successfully read active gatt characters")
