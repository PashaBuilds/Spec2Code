import unittest

from orchestrator.device_profiles import ltc2991


class Ltc2991ProfileTests(unittest.TestCase):
    def test_init_writes_configure_before_trigger_and_enable_repeat_mode(self) -> None:
        # LTC2991 datasheet (2991f): writing register 0x01 both sets the
        # channel enables AND triggers a conversion, so it must come last;
        # Repeated Acquisition (0x08 bit 4) must be set or the poll-then-read
        # operations return stale data after the first conversion.
        config = {
            "pairs": {
                "v1_v2": {"mode": "single_ended_voltage", "shunt_milliohm": None},
                "v3_v4": {"mode": "differential_voltage", "shunt_milliohm": None},
                "v5_v6": {"mode": "current_shunt", "shunt_milliohm": 10},
                "v7_v8": {"mode": "disabled", "shunt_milliohm": None},
            },
            "internal_temperature": True,
            "vcc_read": False,
        }

        writes = ltc2991.i2c_init_writes(config)
        regs = [item["reg"] for item in writes]

        self.assertEqual(
            regs,
            ["CONTROL_V1V4", "CONTROL_V5V8", "PWM_T_INTERNAL_CONTROL", "STATUS_HIGH"],
        )
        by_reg = {item["reg"]: item["value"] for item in writes}
        self.assertEqual(by_reg["PWM_T_INTERNAL_CONTROL"], 0x10)
        # v1_v2 enabled (bit 4), v3_v4 (bit 5), v5_v6 (bit 6), internal temp (bit 3).
        self.assertEqual(by_reg["STATUS_HIGH"], 0x78)
        # v3_v4 differential -> control bits 0x1 at shift 4.
        self.assertEqual(by_reg["CONTROL_V1V4"], 0x10)
        # v5_v6 current shunt -> differential bit at shift 0.
        self.assertEqual(by_reg["CONTROL_V5V8"], 0x01)


if __name__ == "__main__":
    unittest.main()
