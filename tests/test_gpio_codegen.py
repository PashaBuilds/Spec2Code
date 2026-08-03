"""MicroBlaze AXI GPIO (XGpio): controller-level ops + gpio transport devices.

Two separate paths are locked here:

  * **Controller-level** ``gpio_read`` / ``gpio_write`` - the target is an AXI
    GPIO core, not a device, exactly like ``i2c_scan``. The wire frame must
    carry a CONTROLLER index and the generated bridge must resolve it from the
    controller table.
  * **Device-level** ``transport.type == "gpio"`` descriptors, which now emit a
    real XGpio driver unit.

The XGpio facts asserted below come from
``C:/Xilinx_2023_2/Vitis/2023.2/data/embeddedsw/XilinxProcessorIPLib/drivers/gpio_v4_10``:
``XGpio_SetDataDirection(XGpio*, unsigned Channel, u32 DirectionMask)`` where a
mask bit set to **1 is an INPUT** and **0 is an OUTPUT** (``src/xgpio.c``
doxygen), each channel owning its own TRI register at
``(Channel-1) * XGPIO_CHAN_OFFSET + XGPIO_TRI_OFFSET`` (``src/xgpio_l.h``).
"""

import json
import struct
import tempfile
import unittest
from pathlib import Path

import yaml

from backend import s2cmsg
from backend.validators.wiring import validate_wiring
from orchestrator import cmodel, codegen


ROOT = Path(__file__).resolve().parent.parent

AXI_I2C_CONTROLLER = {
    "id": "pl_i2c_0", "type": "i2c", "instance": "XPAR_AXI_IIC_0",
    "base_address": "0x40800000", "device_id": 0, "driver": "XIic",
    "source": "xparameters", "zone": "pl",
}
AXI_GPIO_CONTROLLER = {
    "id": "pl_gpio_0", "type": "gpio", "instance": "XPAR_AXI_GPIO_0",
    "base_address": "0x40000000", "device_id": 0, "driver": "XGpio",
    "source": "xparameters", "zone": "pl",
}


def _microblaze_spec(project_name: str) -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": project_name,
                       "platform": "microblaze_7series", "target_core": "microblaze_0",
                       "runtime": "bare_metal", "testbench_transport": "uart"}
    spec["controllers"] = [
        {"id": "pl_uart_0", "type": "uart", "instance": "XPAR_AXI_UARTLITE_0",
         "base_address": "0x40600000", "device_id": 0, "driver": "XUartLite",
         "source": "xparameters", "zone": "pl"},
        dict(AXI_I2C_CONTROLLER),
        dict(AXI_GPIO_CONTROLLER),
    ]
    spec["muxes"] = []
    spec["devices"] = []
    return spec


def _gpio_lines(controller_id: str = "pl_gpio_0", channel: int = 1, mask: int = 0xF) -> dict:
    return {
        "id": "j5_gpio_lines", "part": "GPIO_LINES",
        "descriptor_ref": "descriptors/gpio_lines.yaml",
        "attach": {"controller_id": controller_id, "gpio_channel": channel,
                   "gpio_pin_mask": mask},
        "tests_requested": [],
    }


def _tmp101(controller_id: str = "pl_i2c_0") -> dict:
    return {
        "id": "u3_tmp101", "part": "TMP101", "descriptor_ref": "descriptors/tmp101.yaml",
        "attach": {"controller_id": controller_id, "i2c_address": "0x4A"},
        "tests_requested": [],
    }


def _generate(spec: dict) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / spec["project"]["name"]
        codegen.generate(spec, out_dir)
        return {
            path.relative_to(out_dir).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(out_dir.rglob("*")) if path.is_file()
        }


class GpioDeviceUnitTests(unittest.TestCase):
    """`transport.type: gpio` descriptors emit a real, verified XGpio driver."""

    def test_gpio_device_unit_uses_the_verified_xgpio_api(self) -> None:
        spec = _microblaze_spec("unit_gpio_device")
        spec["devices"] = [_gpio_lines()]

        files = _generate(spec)
        source = files["drivers/gpiolines.c"]
        header = files["drivers/gpiolines.h"]

        self.assertIn('#include "xgpio.h"', header)
        # Classic (non-SDT) BSP flow: XGpio_Initialize takes a DEVICE ID.
        self.assertIn("iStatus = XGpio_Initialize(spGpio, XPAR_AXI_GPIO_0_DEVICE_ID);", source)
        for call in ("XGpio_GetDataDirection(spGpio, GPIOLINES_GPIO_CHANNEL)",
                     "XGpio_SetDataDirection(spGpio, GPIOLINES_GPIO_CHANNEL,",
                     "XGpio_DiscreteRead(spGpio, GPIOLINES_GPIO_CHANNEL)",
                     "XGpio_DiscreteWrite(spGpio, GPIOLINES_GPIO_CHANNEL,"):
            self.assertIn(call, source)
        # PS GPIO must never leak in - a different driver with a different API.
        self.assertNotIn("XGpioPs", source)
        self.assertIn("#define GPIOLINES_GPIO_CHANNEL 1U", source + files["drivers/gpiolines.h"])

    def test_direction_mask_bit_one_is_input_so_a_write_clears_the_masked_bits(self) -> None:
        # THE fact this whole unit rests on: in XGpio_SetDataDirection a set bit
        # is an INPUT. Driving pins therefore means CLEARING their bits, and
        # only theirs - `dir & ~mask`, never `dir | mask` and never a bare mask.
        spec = _microblaze_spec("unit_gpio_direction")
        spec["devices"] = [_gpio_lines()]

        source = _generate(spec)["drivers/gpiolines.c"]

        self.assertIn(
            "XGpio_SetDataDirection(spGpio, GPIOLINES_GPIO_CHANNEL, uiDirection & ~uiMask);",
            source)
        # Read-modify-write of the data register: pins outside the mask keep
        # whatever they were driving.
        self.assertIn("(uiCurrent & ~uiMask) | (uiValue & uiMask));", source)

    def test_write_fails_loudly_when_the_core_is_all_inputs(self) -> None:
        # An "All Inputs" AXI GPIO has a READ-ONLY tri-state register: the
        # direction write is silently swallowed and the data write does nothing.
        # Without the read-back guard the op would report success forever.
        spec = _microblaze_spec("unit_gpio_ro_guard")
        spec["devices"] = [_gpio_lines()]

        source = _generate(spec)["drivers/gpiolines.c"]
        write_body = source[source.index("gpiolinesPinsWrite"):source.index("gpiolinesPinsRead")]

        self.assertIn("if ((uiDirection & uiMask) != 0U)", write_body)
        self.assertIn("return XST_FAILURE;", write_body)

    def test_read_never_touches_the_direction_register(self) -> None:
        # Tri-stating a line the board is actively driving (a held reset, an
        # enable) is destructive; the discrete data register reads back fine on
        # output pins, so a read has no business writing TRI.
        spec = _microblaze_spec("unit_gpio_read_passive")
        spec["devices"] = [_gpio_lines()]

        source = _generate(spec)["drivers/gpiolines.c"]
        read_body = source[source.index("gpiolinesPinsRead"):source.index("int gpiolinesDeviceInit")]

        self.assertIn("XGpio_DiscreteRead(spGpio, GPIOLINES_GPIO_CHANNEL)", read_body)
        self.assertNotIn("SetDataDirection", read_body)

    def test_channel_two_device_guards_against_a_single_channel_core(self) -> None:
        # Channel 2 lives at register offsets 0x8/0xC which simply do not exist
        # on a single-channel core; the driver only Xil_Asserts, and asserts
        # compile out of a release BSP.
        spec = _microblaze_spec("unit_gpio_channel2")
        spec["devices"] = [_gpio_lines(channel=2)]

        source = _generate(spec)["drivers/gpiolines.c"]

        self.assertIn("#define GPIOLINES_GPIO_CHANNEL 2U",
                      source + _generate(spec)["drivers/gpiolines.h"])
        self.assertIn("if (spGpio->IsDual == 0)", source)

    def test_masks_come_from_the_descriptor_steps_and_the_attach_default(self) -> None:
        spec = _microblaze_spec("unit_gpio_masks")
        spec["devices"] = [_gpio_lines(mask=0xF)]

        source = _generate(spec)["drivers/gpiolines.c"]

        # reset_assert/reset_release declare pin_mask 0x1 explicitly.
        self.assertIn("gpiolinesPinsWrite(spGpio, 0x1U, 0x0U);", source)
        self.assertIn("gpiolinesPinsWrite(spGpio, 0x1U, 0x1U);", source)
        # line_read declares no pin_mask -> the device's own mask, emitted as
        # the named define rather than a second copy of the literal.
        self.assertIn("gpiolinesPinsRead(spGpio, GPIOLINES_GPIO_MASK, uipLine);", source)
        self.assertIn("#define GPIOLINES_GPIO_MASK 0xFU", _generate(spec)["drivers/gpiolines.h"])

    def test_unexpressible_descriptor_step_raises_codegen_error(self) -> None:
        # A GPIO core has no register map; a descriptor that asks for one must
        # fail at generation, not emit a driver that quietly skips the step.
        descriptor = {
            "part": "BOGUS_GPIO", "transport": {"type": "gpio"},
            "operations": [{"name": "config_read", "steps": [{"op": "read_register", "reg": "CFG"}]}],
        }
        with self.assertRaises(cmodel.CodegenError) as ctx:
            cmodel._gpio_device_unit({"id": "d0", "part": "BOGUS_GPIO", "attach": {}},
                                     dict(AXI_GPIO_CONTROLLER), descriptor)
        self.assertIn("read_register", str(ctx.exception))

    def test_runtime_valued_pin_write_raises_instead_of_guessing(self) -> None:
        descriptor = {
            "part": "BOGUS_GPIO", "transport": {"type": "gpio"},
            "operations": [{"name": "byte_write", "steps": [{"op": "pin_write", "pin_mask": 1}]}],
        }
        with self.assertRaises(cmodel.CodegenError) as ctx:
            cmodel._gpio_device_unit({"id": "d0", "part": "BOGUS_GPIO", "attach": {}},
                                     dict(AXI_GPIO_CONTROLLER), descriptor)
        self.assertIn("pin_value", str(ctx.exception))

    def test_ps_gpio_driver_still_fails_loudly(self) -> None:
        # XGpioPs has a completely different API (flat pin space, no channel /
        # TRI-mask model) and no emitter arm.
        with self.assertRaises(cmodel.CodegenError) as ctx:
            cmodel._handle_for({"id": "ps_gpio_0", "type": "gpio", "instance": "XPAR_XGPIOPS_0",
                                "zone": "ps"})
        message = str(ctx.exception)
        self.assertIn("XGpioPs", message)
        self.assertIn("XGpio", message)


class GpioExampleDescriptorTests(unittest.TestCase):
    def test_shipped_gpio_lines_descriptor_is_honest_board_wiring(self) -> None:
        descriptor = yaml.safe_load((ROOT / "descriptors/gpio_lines.yaml").read_text(encoding="utf-8"))
        self.assertEqual(descriptor["transport"]["type"], "gpio")
        # No invented register map: a GPIO bank is wiring, not a chip.
        self.assertNotIn("registers", descriptor)
        self.assertIn("cip degil", descriptor["summary"].lower().replace("ç", "c"))
        names = {op["name"] for op in descriptor["operations"]}
        self.assertEqual(names, {"device_init", "line_read", "reset_assert", "reset_release"})


class GpioControllerOpTests(unittest.TestCase):
    """`gpio_read` / `gpio_write` target a CONTROLLER, like `i2c_scan`."""

    def test_controller_ops_are_declared_controller_addressed(self) -> None:
        self.assertIn("gpio_read", codegen._CONTROLLER_ADDRESSED_OPS)
        self.assertIn("gpio_write", codegen._CONTROLLER_ADDRESSED_OPS)

    def test_generated_ops_use_the_verified_xgpio_api_and_payload_mapping(self) -> None:
        spec = _microblaze_spec("unit_gpio_ctrl_ops")
        spec["devices"] = [_tmp101()]

        ops = _generate(spec)["tests/unit_gpio_ctrl_ops_testbench_ops.c"]

        self.assertIn('spec2codeTestbenchStringEqual(spRequest->cArrOperation, "gpio_read")', ops)
        self.assertIn('spec2codeTestbenchStringEqual(spRequest->cArrOperation, "gpio_write")', ops)
        self.assertIn('spGpioTarget = spec2codeTestbenchGpioHandleGet(spRequest->cArrRegister);', ops)
        # Payload mapping: uiAdres = channel, uiUzunluk = mask (0 = all pins),
        # uiDeger = value.
        self.assertIn("uiChannel = spRequest->uiAddress;", ops)
        self.assertIn("uiMask = (spRequest->uiLength == 0U) ? 0xFFFFFFFFU : spRequest->uiLength;", ops)
        self.assertIn("(uiCurrent & ~uiMask) | (spRequest->uiValue & uiMask));", ops)
        # Same direction contract as the device unit.
        self.assertIn("XGpio_SetDataDirection(spGpioTarget, uiChannel, uiDirection & ~uiMask);", ops)
        self.assertIn("if ((uiChannel == 2U) && (spGpioTarget->IsDual == 0))", ops)

    def test_gpio_ops_are_absent_when_no_axi_gpio_controller_is_wired(self) -> None:
        spec = _microblaze_spec("unit_gpio_absent")
        spec["controllers"] = [c for c in spec["controllers"] if c["type"] != "gpio"]
        spec["devices"] = [_tmp101()]

        ops = _generate(spec)["tests/unit_gpio_absent_testbench_ops.c"]

        self.assertNotIn("XGpio", ops)
        self.assertNotIn("gpio_read", ops)

    def test_controller_table_puts_i2c_first_and_publishes_gpio_index(self) -> None:
        # The i2c_scan index contract (index == position in
        # manifest i2c_scan.controllers) survives only if the I2C entries stay a
        # PREFIX of the shared table; the GPIO index is published explicitly so
        # nothing has to re-derive the offset.
        spec = _microblaze_spec("unit_gpio_ctrl_table")
        spec["devices"] = [_tmp101(), _gpio_lines()]

        files = _generate(spec)
        source = files["tests/spec2code_mesaj.c"]
        manifest = json.loads(files["tests/spec2code_testbench_manifest.json"])

        table = source[source.index("S_cpArrDenetleyiciTablosu[]"):]
        table = table[:table.index("};")]
        self.assertLess(table.index('"pl_i2c_0"'), table.index('"pl_gpio_0"'))
        self.assertEqual(manifest["gpio"]["controllers"],
                         [{"id": "pl_gpio_0", "instance": "XPAR_AXI_GPIO_0", "index": 1}])
        # ...and the bridge knows both ops resolve against that table.
        self.assertIn(f"    0x{s2cmsg.message_id_for_op('gpio_read'):08X}U,", source)
        self.assertIn(f"    0x{s2cmsg.message_id_for_op('gpio_write'):08X}U,", source)

    def test_manifest_rejects_a_gpio_controller_the_board_getter_cannot_resolve(self) -> None:
        spec = _microblaze_spec("unit_gpio_phantom")
        spec["devices"] = [_tmp101()]
        # A PS GPIO would be skipped everywhere; force the mismatch instead by
        # making the board-getter list disagree with the advertised list.
        original = codegen._testbench_board_controller_entries
        codegen._testbench_board_controller_entries = staticmethod(  # type: ignore[assignment]
            lambda s: [e for e in original(s) if e["htype"] != "XGpio"])
        try:
            get_descriptor = codegen.make_descriptor_loader(codegen._ROOT)
            with self.assertRaises(cmodel.CodegenError) as ctx:
                codegen._testbench_manifest(spec, get_descriptor)
        finally:
            codegen._testbench_board_controller_entries = original  # type: ignore[assignment]
        self.assertIn("pl_gpio_0", str(ctx.exception))

    def test_gpio_ops_carry_the_controller_index_on_the_wire(self) -> None:
        # Same field regression class as i2c_scan (v0.1.142): the controller id
        # STRING never reaches the wire, so the target must ride in
        # uiCihazIndeks as a CONTROLLER index. Unpack the real tx frame.
        from backend import gpio as gpio_mod
        from backend.testbench import _pack_command

        seen: list[tuple[str, int, int, int, int, int]] = []

        def fake_send(session_id, command):
            request, _msg_id = _pack_command(command)
            frame = s2cmsg.FrameParser().feed(request)[0]
            device_index, _reg, address, length, value, has_value = struct.unpack_from(
                "<IIIIII", frame[2], 0)
            seen.append((command.operation, device_index, address, length, value, has_value))
            return type("R", (), {"parsed": {
                "id": str(command.command_id), "ok": "1", "durum": 0, "status": "0",
                "value": "0xA5", "data": "000000A5", "message": f"{command.operation} ok"}})()

        original = gpio_mod.testbench_sessions.send
        gpio_mod.testbench_sessions.send = fake_send  # type: ignore[assignment]
        try:
            read = gpio_mod.read_channel("s1", "pl_gpio_0", controller_index=1,
                                         channel=2, mask=0xF0, timeout_s=1.0)
            write = gpio_mod.write_channel("s1", "pl_gpio_0", controller_index=1,
                                           channel=1, value=0x3, mask=0x3, timeout_s=1.0)
        finally:
            gpio_mod.testbench_sessions.send = original  # type: ignore[assignment]

        self.assertEqual(seen[0], ("gpio_read", 1, 2, 0xF0, 0, 0))
        self.assertEqual(seen[1], ("gpio_write", 1, 1, 0x3, 0x3, 1))
        self.assertEqual(read["value"], 0xA5)
        self.assertEqual(write["channel"], 1)

    def test_host_rejects_an_impossible_channel_before_touching_the_wire(self) -> None:
        from backend import gpio as gpio_mod

        def explode(session_id, command):  # pragma: no cover - must not run
            raise AssertionError("no frame may be sent for an invalid channel")

        original = gpio_mod.testbench_sessions.send
        gpio_mod.testbench_sessions.send = explode  # type: ignore[assignment]
        try:
            with self.assertRaises(gpio_mod.GpioError):
                gpio_mod.read_channel("s1", "pl_gpio_0", controller_index=0, channel=3)
        finally:
            gpio_mod.testbench_sessions.send = original  # type: ignore[assignment]


class GpioWiringValidationTests(unittest.TestCase):
    def _spec(self, device: dict) -> dict:
        return {
            "schema_version": "1.0",
            "project": {"name": "p", "platform": "microblaze_7series",
                        "target_core": "microblaze_0", "runtime": "bare_metal"},
            "controllers": [dict(AXI_GPIO_CONTROLLER), dict(AXI_I2C_CONTROLLER)],
            "devices": [device],
        }

    def test_correct_gpio_device_validates(self) -> None:
        result = validate_wiring(self._spec(_gpio_lines()))
        self.assertTrue(result["valid"], result["errors"])

    def test_gpio_device_on_a_non_gpio_controller_is_rejected(self) -> None:
        result = validate_wiring(self._spec(_gpio_lines(controller_id="pl_i2c_0")))
        self.assertFalse(result["valid"])
        self.assertTrue(any("GPIO descriptor is attached to i2c" in e["message"]
                            for e in result["errors"]), result["errors"])

    def test_out_of_range_channel_and_empty_mask_are_rejected(self) -> None:
        bad_channel = validate_wiring(self._spec(_gpio_lines(channel=3)))
        self.assertFalse(bad_channel["valid"])
        self.assertTrue(any("gpio_channel" in e["path"] for e in bad_channel["errors"]))

        bad_mask = validate_wiring(self._spec(_gpio_lines(mask=0)))
        self.assertFalse(bad_mask["valid"])
        self.assertTrue(any("gpio_pin_mask" in e["path"] for e in bad_mask["errors"]))

    def test_two_devices_driving_the_same_pin_conflict(self) -> None:
        spec = self._spec(_gpio_lines(mask=0x3))
        second = _gpio_lines(mask=0x6)
        second["id"] = "j6_gpio_lines"
        spec["devices"].append(second)

        result = validate_wiring(spec)

        self.assertFalse(result["valid"])
        self.assertTrue(any("conflict" in e["message"] and "0x2" in e["message"]
                            for e in result["errors"]), result["errors"])

    def test_different_channels_do_not_conflict(self) -> None:
        spec = self._spec(_gpio_lines(channel=1, mask=0x3))
        second = _gpio_lines(channel=2, mask=0x3)
        second["id"] = "j6_gpio_lines"
        spec["devices"].append(second)

        self.assertTrue(validate_wiring(spec)["valid"])


if __name__ == "__main__":
    unittest.main()
