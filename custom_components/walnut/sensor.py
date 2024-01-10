"""Sensor platform for Walnut."""

import logging

from sensor_state_data import SensorUpdate

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.sensor import sensor_device_info_to_hass_device_info

from .const import DOMAIN
from .coordinator import WalnutActiveBluetoothProcessorCoordinator
from .walnut import WalnutSensor

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: dict[WalnutSensor, SensorEntityDescription] = {
    WalnutSensor.TEMPERATURE: SensorEntityDescription(
        key=WalnutSensor.TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WalnutSensor.HUMIDITY: SensorEntityDescription(
        key=WalnutSensor.HUMIDITY,
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    WalnutSensor.SIGNAL_STRENGTH: SensorEntityDescription(
        key=WalnutSensor.SIGNAL_STRENGTH,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        has_entity_name=True,
        name="Signal Strength",
    ),
    WalnutSensor.BATTERY: SensorEntityDescription(
        key=WalnutSensor.BATTERY,
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        has_entity_name=True,
        name="Battery Level",
    ),
}


def sensor_update_to_bluetooth_data_update(sensor_update: SensorUpdate):
    """Convert a sensor update to a bluetooth data update."""
    _LOGGER.debug("Parsed data: %s", sensor_update.devices)
    return PassiveBluetoothDataUpdate(
        devices={
            device_id: sensor_device_info_to_hass_device_info(device_info)
            for device_id, device_info in sensor_update.devices.items()
        },
        entity_descriptions={
            PassiveBluetoothEntityKey(
                device_key.key, device_key.device_id
            ): SENSOR_DESCRIPTIONS[device_key.key]
            for device_key in sensor_update.entity_descriptions
        },
        entity_data={
            PassiveBluetoothEntityKey(
                device_key.key, device_key.device_id
            ): sensor_values.native_value
            for device_key, sensor_values in sensor_update.entity_values.items()
        },
        entity_names={
            PassiveBluetoothEntityKey(
                device_key.key, device_key.device_id
            ): sensor_values.name
            for device_key, sensor_values in sensor_update.entity_values.items()
        },
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Walnut sensors."""
    coordinator: WalnutActiveBluetoothProcessorCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]
    processor = PassiveBluetoothDataProcessor(sensor_update_to_bluetooth_data_update)
    entry.async_on_unload(
        processor.async_add_entities_listener(WalnutSensorsEntity, async_add_entities)
    )
    entry.async_on_unload(coordinator.async_register_processor(processor))


class WalnutSensorsEntity(PassiveBluetoothProcessorEntity, SensorEntity):
    """Representation of the Walnut sensors."""

    # TODO: probably split this to separate entities. Also how to name the device?

    @property
    def native_value(self) -> int | float | None:
        """Return the native value."""
        return self.processor.entity_data.get(self.entity_key)
