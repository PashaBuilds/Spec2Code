"""Kart kontrol GPIO'su (board_control -> drivers/ip/boardctl) ve JESD/AFE bring-up entegrasyonu."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import boardctl, codegen  # noqa: E402
from tests.test_afe7900 import _spec  # noqa: E402

GPIO = {"id": "pl_gpio_ctrl", "type": "gpio", "instance": "XPAR_AXI_GPIO_0", "base_address": "0xA0020000",
        "driver": "XGpio", "source": "xparameters", "zone": "pl"}
BOARD = {
    "gpio_id": "pl_gpio_ctrl",
    "jesd_reset_ms": 100,
    "bits": [
        {"name": "lmx2820_mute", "channel": 1, "bit": 0, "role": "generic"},
        {"name": "afe1_reset_active_low", "channel": 1, "bit": 3, "role": "afe_reset", "active_low": True, "target": "afe0"},
        {"name": "jesd_afe1_rx_core_reset_active_high", "channel": 1, "bit": 9, "role": "jesd_rx_core_reset", "target": "jesd204c_rx"},
        {"name": "jesd_afe1_tx_core_reset_active_high", "channel": 1, "bit": 11, "role": "jesd_tx_core_reset", "target": "jesd204c_tx"},
        {"name": "afe1_hsclk1_lcpll_lock_0", "channel": 2, "bit": 4, "role": "pll_lock", "target": "afe0"},
        {"name": "afe1_hsclk0_lcpll_lock_0", "channel": 2, "bit": 5, "role": "pll_lock", "target": "afe0"},
    ],
}


def _board_spec(*, afe: bool) -> dict:
    spec = _spec(jesd="64b66b")
    spec["controllers"].append(dict(GPIO))
    spec["board_control"] = json.loads(json.dumps(BOARD))
    if not afe:
        spec["devices"] = []
    return spec


class BoardControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="boardctl_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _generate(self, spec: dict) -> dict[str, str]:
        written = codegen.generate(spec, self.tmp)
        return {Path(p).relative_to(self.tmp).as_posix(): Path(p).read_text(encoding="utf-8", errors="replace")
                for p in written}

    def test_normalize(self) -> None:
        board = boardctl.board_control(_board_spec(afe=False))
        self.assertEqual(board["base"], 0xA0020000)
        self.assertEqual(board["jesd_reset_ms"], 100)
        self.assertEqual([b["role"] for b in board["bits"]][:2], ["generic", "afe_reset"])
        self.assertTrue(boardctl.has_jesd_reset(board))
        self.assertTrue(boardctl.has_role(board, "pll_lock"))
        self.assertFalse(boardctl.has_role(board, "sysref"))
        # GPIO id controllers'ta yoksa ya da bit yoksa modul uretilmez
        spec = _board_spec(afe=False)
        spec["board_control"]["gpio_id"] = "yok"
        self.assertIsNone(boardctl.board_control(spec))
        spec = _board_spec(afe=False)
        spec["board_control"]["bits"] = []
        self.assertIsNone(boardctl.board_control(spec))

    def test_jesd_only_physical_reset_then_register_reset_and_locks(self) -> None:
        files = self._generate(_board_spec(afe=False))
        self.assertIn("drivers/ip/boardctl.c", files)
        h = files["drivers/ip/boardctl.h"]
        c = files["drivers/ip/boardctl.c"]
        self.assertIn("#define BOARDCTL_GPIO_BASE 0xA0020000U", h)
        self.assertIn("#define BOARDCTL_JESD_RESET_MS 100U", h)
        self.assertIn("#define BOARDCTL_PLL_LOCK_COUNT 2U", h)
        self.assertIn('{"afe1_reset_active_low", 1U, 0x00000008U, BOARDCTL_ROLE_AFE_RESET, TRUE, "afe0"},', c)
        self.assertIn('{"afe1_hsclk1_lcpll_lock_0", 2U, 0x00000010U, BOARDCTL_ROLE_PLL_LOCK, FALSE, "afe0"},', c)
        # acilis: giris kanali TRI=1, AFE reset aktif, cikis TRI=0 seviyelerden sonra
        self.assertIn("Xil_Out32((UINTPTR)BOARDCTL_GPIO_BASE + BOARDCTL_REG_IN_TRI, 0xFFFFFFFFU);", c)
        self.assertLess(c.index("boardCtlOutWrite();\n    Xil_Out32((UINTPTR)BOARDCTL_GPIO_BASE + BOARDCTL_REG_OUT_TRI, 0U);"),
                        c.index("int boardCtlRoleWrite("))
        self.assertIn("usleep(BOARDCTL_JESD_RESET_MS * 1000U);", c)
        self.assertNotIn("boardCtlSysrefPulse", h)  # sysref rolu yok -> fonksiyon uretilmez
        link = files["drivers/ip/jesdlink.c"]
        self.assertIn('#include "boardctl.h"', link)
        bring = link[link.index("int jesdLinkBringup("):]
        # fiziksel reset darbesi register RESET'ten ONCE
        self.assertLess(bring.index("boardCtlJesdCoreResetPulse();"), bring.index("jesdLinkCoreReset(JESDLINK_TX_BASE, 1U)"))
        status = link[link.index("int jesdLinkStatusWord("):link.index("int jesdLinkBringup(")]
        self.assertIn("if (boardCtlPllLocksRead() == TRUE)", status)
        self.assertIn("usStatus |= JESDLINK_STATUS_PLL_LOCK;", status)
        self.assertIn("#define JESDLINK_STATUS_FPGA_ALL 0x0023U", files["drivers/ip/jesdlink.h"])
        self.assertIn("#define JESDLINK_BOARDCTL TRUE", files["drivers/ip/jesdlink.h"])
        # eski adla-SYSREF GPIO tespiti (adinda sysref yok) -> saat agaci dali
        self.assertIn("JESD: SYSREF GPIO yok", link)
        manifest = json.loads(files["tests/spec2code_testbench_manifest.json"])
        self.assertEqual(manifest["board_control"]["gpio_id"], "pl_gpio_ctrl")
        self.assertEqual(len(manifest["board_control"]["bits"]), 6)
        self.assertIn("5", manifest["jesd"]["status_bits"])

    def test_afe_release_before_bringup_and_physical_reset_before_afe(self) -> None:
        files = self._generate(_board_spec(afe=True))
        drv = files["drivers/afe7900.c"]
        self.assertIn('#include "boardctl.h"', drv)
        init = drv[drv.index("int afe7900DeviceInit("):]
        init = init[:init.index("\n}\n")]
        self.assertIn("usleep(BOARDCTL_AFE_RESET_HOLD_MS * 1000U);", init)
        # AFE reset kaldirma, bring-up'tan HEMEN once
        self.assertLess(init.index('boardCtlRoleWrite(BOARDCTL_ROLE_AFE_RESET, "afe0", FALSE);'),
                        init.index("afeDeviceBringupFromMem"))
        op = drv[drv.index("int afe7900JesdLinkBringup("):]
        op = op[:op.index("\n}\n")]
        # fiziksel JESD reset AFE bring-up'tan (device_init) once, register reset'ten de once
        self.assertLess(op.index("boardCtlJesdCoreResetPulse();"), op.index("jesdLinkCoreReset(JESDLINK_TX_BASE, 1U)"))
        self.assertLess(op.index("boardCtlJesdCoreResetPulse();"), op.index("afe7900DeviceInit("))
        self.assertIn("if (boardCtlPllLocksRead() == TRUE)", op)
        self.assertIn("if ((usStatus & 0x003FU) == 0x003FU)", op)

    def test_pll_reset_only_pulsed_on_versal(self) -> None:
        # Versal: PHY ancak HSCLK/LCPLL reset pinleriyle resetleniyor -> JESD fiziksel darbeye katilir; ZynqMP'de pasif.
        for platform, expect in (("zynq_ultrascale", False), ("versal", True)):
            spec = _board_spec(afe=False)
            spec["project"]["platform"] = platform
            spec["project"]["target_core"] = "a72_0" if platform == "versal" else "a53_0"
            spec["board_control"]["bits"].append({"name": "hsclk_afe1_lcpll_reset", "channel": 1, "bit": 10, "role": "pll_reset"})
            files = self._generate(spec)
            c = files["drivers/ip/boardctl.c"]
            pulse = c[c.index("int boardCtlJesdCoreResetPulse(void)"):]
            self.assertEqual("boardCtlRoleWrite(BOARDCTL_ROLE_PLL_RESET, NULL, TRUE);" in pulse, expect, platform)
            self.assertEqual("boardCtlRoleWrite(BOARDCTL_ROLE_PLL_RESET, NULL, FALSE);" in pulse, expect, platform)
            if expect:
                self.assertLess(pulse.index("BOARDCTL_ROLE_PLL_RESET, NULL, TRUE"), pulse.index("BOARDCTL_ROLE_JESD_RX_CORE_RESET, NULL, TRUE"))
            shutil.rmtree(self.tmp, ignore_errors=True)
            self.tmp.mkdir()

    def test_sysref_role_replaces_named_gpio(self) -> None:
        spec = _board_spec(afe=False)
        spec["board_control"]["bits"].append({"name": "sysref_pulse", "channel": 1, "bit": 1, "role": "sysref"})
        files = self._generate(spec)
        self.assertIn("void boardCtlSysrefPulse(void);", files["drivers/ip/boardctl.h"])
        link = files["drivers/ip/jesdlink.c"]
        self.assertIn("boardCtlSysrefPulse();", link)
        self.assertNotIn("JESD: SYSREF GPIO yok", link)

    def test_without_board_control_nothing_changes(self) -> None:
        spec = _spec(jesd="64b66b")
        spec["devices"] = []
        files = self._generate(spec)
        self.assertNotIn("drivers/ip/boardctl.c", files)
        self.assertNotIn("boardctl", files["drivers/ip/jesdlink.c"])
        self.assertIn("#define JESDLINK_STATUS_FPGA_ALL 0x0003U", files["drivers/ip/jesdlink.h"])
        self.assertIn("#define JESDLINK_BOARDCTL FALSE", files["drivers/ip/jesdlink.h"])


if __name__ == "__main__":
    unittest.main()
