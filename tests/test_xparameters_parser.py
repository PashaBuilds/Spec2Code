import unittest

from backend.parsers.xparameters import parse_xparameters


PLATFORM = {"family_zone": {"ps": "ps", "pl": "pl"}, "default_zone": "ps"}


class XparametersParserTests(unittest.TestCase):
    def test_ps_i2c_aliases_collapse_to_driver_instance(self) -> None:
        text = """
        #define XPAR_PSU_I2C_0_DEVICE_ID 0
        #define XPAR_PSU_I2C_0_BASEADDR 0xFF020000
        #define XPAR_PSU_I2C_0_HIGHADDR 0xFF02FFFF
        #define XPAR_XIICPS_0_DEVICE_ID XPAR_PSU_I2C_0_DEVICE_ID
        #define XPAR_XIICPS_0_BASEADDR 0xFF020000
        #define XPAR_XIICPS_0_HIGHADDR 0xFF02FFFF
        """

        parsed = parse_xparameters(text, PLATFORM)

        self.assertEqual(len(parsed.controllers), 1)
        controller = parsed.controllers[0]
        self.assertEqual(controller["id"], "ps_i2c_0")
        self.assertEqual(controller["type"], "i2c")
        self.assertEqual(controller["instance"], "XPAR_XIICPS_0")
        self.assertEqual(controller["device_id"], 0)
        self.assertEqual(controller["base_address"], "0xFF020000")

    def test_same_type_different_addresses_remain_distinct(self) -> None:
        text = """
        #define XPAR_PSU_I2C_0_DEVICE_ID 0
        #define XPAR_PSU_I2C_0_BASEADDR 0xFF020000
        #define XPAR_XIICPS_0_DEVICE_ID XPAR_PSU_I2C_0_DEVICE_ID
        #define XPAR_XIICPS_0_BASEADDR 0xFF020000
        #define XPAR_PSU_I2C_1_DEVICE_ID 1
        #define XPAR_PSU_I2C_1_BASEADDR 0xFF030000
        #define XPAR_XIICPS_1_DEVICE_ID XPAR_PSU_I2C_1_DEVICE_ID
        #define XPAR_XIICPS_1_BASEADDR 0xFF030000
        """

        parsed = parse_xparameters(text, PLATFORM)

        self.assertEqual([c["instance"] for c in parsed.controllers], ["XPAR_XIICPS_0", "XPAR_XIICPS_1"])
        self.assertEqual([c["id"] for c in parsed.controllers], ["ps_i2c_0", "ps_i2c_1"])


if __name__ == "__main__":
    unittest.main()
