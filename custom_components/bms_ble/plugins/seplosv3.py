"""Base class defintion for battery management systems (BMS)."""

from abc import ABCMeta, abstractmethod
from typing import Any

from bleak.backends.device import BLEDevice

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.components.bluetooth.match import (
    BluetoothMatcherOptional,
    ble_device_matches,
)
from homeassistant.util.unit_conversion import _HRS_TO_SECS

from ..const import (
    ATTR_BATTERY_CHARGING,
    ATTR_CURRENT,
    ATTR_CYCLE_CAP,
    ATTR_CYCLE_CHRG,
    ATTR_POWER,
    ATTR_RUNTIME,
    ATTR_VOLTAGE,
)


class BaseBMS(metaclass=ABCMeta):
    """Base class for battery management system."""

    def __init__(self, ble_device: BLEDevice, reconnect: bool = False) -> None:
        """Intialize the BMS.

        ble_device: the Bleak device to connect to
        reconnect: if true, the connection will be closed after each update
        """

    @staticmethod
    @abstractmethod
    def matcher_dict_list() -> list[dict[str, Any]]:
        """Return a list of Bluetooth matchers."""

    @staticmethod
    @abstractmethod
    def device_info() -> dict[str, str]:
        """Return a dictionary of device information.

        keys: manufacturer, model
        """

    @classmethod
    def device_id(cls) -> str:
        """Return device information as string."""
        return " ".join(cls.device_info().values())

    @classmethod
    def supported(cls, discovery_info: BluetoothServiceInfoBleak) -> bool:
        """Return true if service_info matches BMS type."""
        for matcher_dict in cls.matcher_dict_list():
            if ble_device_matches(
                BluetoothMatcherOptional(**matcher_dict), discovery_info
            ):
                return True
        return False

    @classmethod
    def calc_values(cls, data: dict[str, int | float | bool], values: set[str]):
        """Calculate missing BMS values from existing ones.

        data: data dictionary from BMS
        values: list of values to add to the dictionary
        """

        def can_calc(value: str, using: frozenset[str]) -> bool:
            """Check that value to add does not exists, is requested and the necessary parameters are available."""
            return (value in values) and (value not in data) and using.issubset(data)

        # calculate cycle capacity from voltage and cycle charge
        if can_calc(ATTR_CYCLE_CAP, frozenset({ATTR_VOLTAGE, ATTR_CYCLE_CHRG})):
            data[ATTR_CYCLE_CAP] = data[ATTR_VOLTAGE] * data[ATTR_CYCLE_CHRG]

        # calculate current power from voltage and current
        if can_calc(ATTR_POWER, frozenset({ATTR_VOLTAGE, ATTR_CURRENT})):
            data[ATTR_POWER] = data[ATTR_VOLTAGE] * data[ATTR_CURRENT]

        # calculate charge indicator from current
        if can_calc(ATTR_BATTERY_CHARGING, frozenset({ATTR_CURRENT})):
            data[ATTR_BATTERY_CHARGING] = data[ATTR_CURRENT] > 0

        # calculate runtime from current and cycle charge
        if can_calc(ATTR_RUNTIME, frozenset({ATTR_CURRENT, ATTR_CYCLE_CHRG})):
            if data[ATTR_CURRENT] < 0:
                data[ATTR_RUNTIME] = int(
                    data[ATTR_CYCLE_CHRG] / abs(data[ATTR_CURRENT]) * _HRS_TO_SECS
                )

    async def disconnect(self) -> None:
        """Disconnect connection to BMS if active."""

    @abstractmethod
    async def async_update(self) -> dict[str, int | float | bool]:
        """Retrieve updated values from the BMS.

        Returns a dictionary of BMS values, where the keys need to match the keys in the SENSOR_TYPES list.
        """
