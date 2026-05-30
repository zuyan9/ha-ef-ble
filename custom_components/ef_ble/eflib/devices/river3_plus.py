from ..entity import controls
from ..pb import pr705_pb2
from ..props import computed_field, pb_field
from ..props.enums import IntFieldValue
from ..props.resv_info_parser import (
    resv_is_charging,
    resv_output_power,
    resv_soc,
    resv_temperature,
)
from . import river3

pb = river3.pb


class _removed:
    """Drop an inherited field on this model"""

    def __set_name__(self, owner, name):
        self._name = name
        owner._fields = [f for f in owner._fields if f.public_name != name]
        owner._computed_fields = [
            f for f in owner._computed_fields if f.public_name != name
        ]

    def __get__(self, obj, owner):
        if obj is None:
            return self
        raise AttributeError(self._name)


class LedMode(IntFieldValue):
    OFF = 0
    DIM = 1
    BRIGHT = 2
    SOS = 3


class Device(river3.Device):
    """River 3 Plus"""

    SN_PREFIX = (b"R631", b"R634", b"R635")

    battery_level_main = pb_field(river3.pb.bms_batt_soc)

    # River 3 Plus (R63x) firmware does not emit these values
    battery_input_power = _removed()
    battery_output_power = _removed()
    fan_running = _removed()

    battery_1_enabled = pb_field(pb.plug_in_info_dcp_in_flag)
    battery_1_battery_level = pb_field(pb.plug_in_info_dcp_resv, resv_soc)
    battery_1_cell_temperature = pb_field(pb.plug_in_info_dcp_resv, resv_temperature)
    battery_1_sn = pb_field(pb.plug_in_info_dcp_sn)
    _battery_1_usbc_charging = pb_field(pb.plug_in_info_dcp_resv, resv_is_charging)
    _battery_1_usbc_power = pb_field(pb.plug_in_info_dcp_resv, resv_output_power)

    led_mode = pb_field(river3.pb.led_mode, LedMode.from_value)

    @computed_field
    def battery_1_usbc_input_power(self) -> float | None:
        return self._battery_1_usbc_power_for_direction(charging=True)

    @computed_field
    def battery_1_usbc_output_power(self) -> float | None:
        return self._battery_1_usbc_power_for_direction(charging=False)

    def _battery_1_usbc_power_for_direction(self, charging: bool) -> float | None:
        if self._battery_1_usbc_charging is None or self._battery_1_usbc_power is None:
            return None
        return (
            abs(self._battery_1_usbc_power)
            if self._battery_1_usbc_charging is charging
            else 0
        )

    @controls.select(led_mode, options=LedMode)
    async def set_led_mode(self, state: LedMode):
        await self._send_config_packet(pr705_pb2.ConfigWrite(cfg_led_mode=state.value))

    @property
    def device(self):
        model = ""
        match self._sn[:4]:
            case "R634":
                model = "(270)"
            case "R635":
                model = "Wireless"

        return f"River 3 Plus {model}".strip()
