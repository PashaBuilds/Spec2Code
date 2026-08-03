"""MicroBlaze Debug Module (MDM) UART transportu - Faz 3.

Kapsam:
  * xparameters/XSA parser'inin MDM UART'ini TANIMASI (`subtype: "mdm"`),
  * `testbench_transport: "mdm"` kapisi (pozitif + iki ayri negatif),
  * uretilen ajan (mevcut XUartLite yolu, MDM device id'sine bagli) + banner,
  * manifest `mdm` blogu,
  * host tarafi: tek xsdb `jtagterminal -socket` koprusu, cekirdek filtresi
    PARAMETRE (CoreSight ile ayni kod, farkli hedef).

Diskten dogrulanan gercekler (yorumlarda kaynagiyla birlikte):
  * `uartlite.mdd`: ``supported_peripherals = (mdm axi_uartlite tmr_sem
    psv_pmc_ppu1_mdm)`` -> MDM UART'in surucusu XUartLite'tir, YENI surucu yok.
  * `uartlite.tcl`: MDM'de BAUDRATE/PARITY/DATA_BITS **0** yazilir (baud yok) ve
    IP UART icin konfigure edilmemisse (Debug Only) hicbir define uretilmez.
  * `xsdb.tcl::jtagterminal`: MicroBlaze context'i secilirse xsdb ebeveyne
    (MDM) cikar -> ``CPUType == "MicroBlaze" && ParentID -> ctx = ParentID``.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from backend.parsers.xparameters import parse_xparameters
from backend.parsers.xsa import parse_xsa
from backend.run_on_board import _core_filter
from orchestrator import cmodel, codegen

ROOT = Path(__file__).resolve().parent.parent
PLATFORM = {"family_zone": {"ps": "ps", "pl": "pl"}, "default_zone": "ps"}

#: Vitis'in gercekten urettigi MDM-UART xparameters blogu (uartlite.tcl
#: `xdefine_params_include_file` + `xdefine_params_canonical`): once ornege
#: ozel MDM_1 defineleri, sonra kanonik UARTLITE_0 alias'i AYNI adreste.
MDM_XPARAMETERS = """
#define XPAR_MDM_1_DEVICE_ID 0U
#define XPAR_MDM_1_BASEADDR 0x41400000U
#define XPAR_MDM_1_HIGHADDR 0x4140FFFFU
#define XPAR_MDM_1_BAUDRATE 0U
#define XPAR_UARTLITE_0_DEVICE_ID 0U
#define XPAR_UARTLITE_0_BASEADDR 0x41400000U
#define XPAR_UARTLITE_0_HIGHADDR 0x4140FFFFU
#define XPAR_AXI_UARTLITE_0_DEVICE_ID 1U
#define XPAR_AXI_UARTLITE_0_BASEADDR 0x40600000U
#define XPAR_AXI_UARTLITE_0_HIGHADDR 0x4060FFFFU
#define XPAR_UARTLITE_1_DEVICE_ID 1U
#define XPAR_UARTLITE_1_BASEADDR 0x40600000U
"""

MDM_CONTROLLER = {
    "id": "pl_uart_1", "type": "uart", "instance": "XPAR_MDM_1",
    "base_address": "0x41400000", "device_id": 0, "driver": "XUartLite",
    "subtype": "mdm", "source": "xparameters", "zone": "pl",
}
UARTLITE_CONTROLLER = {
    "id": "pl_uart_0", "type": "uart", "instance": "XPAR_AXI_UARTLITE_0",
    "base_address": "0x40600000", "device_id": 1, "driver": "XUartLite",
    "source": "xparameters", "zone": "pl",
}
AXI_IIC_CONTROLLER = {
    "id": "pl_i2c_0", "type": "i2c", "instance": "XPAR_AXI_IIC_0",
    "base_address": "0x40800000", "device_id": 0, "driver": "XIic",
    "source": "xparameters", "zone": "pl",
}


def microblaze_spec(*controllers: dict, transport: str = "mdm", name: str = "mb_mdm") -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {
        **spec["project"], "name": name, "platform": "microblaze_7series",
        "target_core": "microblaze_0", "runtime": "bare_metal",
        "testbench_transport": transport,
    }
    spec["controllers"] = [dict(c) for c in controllers]
    spec["muxes"] = []
    spec["devices"] = [{
        "id": "u1_tmp101", "part": "TMP101", "descriptor_ref": "descriptors/tmp101.yaml",
        "attach": {"controller_id": "pl_i2c_0", "i2c_address": "0x4A",
                   "via_mux": None, "reset_gpio": None, "irq_line": None},
        "operations_requested": ["device_init", "temperature_read"],
        "tests_requested": [],
    }] if any(c["id"] == "pl_i2c_0" for c in controllers) else []
    return spec


def generate(spec: dict) -> Path:
    out_dir = Path(tempfile.mkdtemp()) / spec["project"]["name"]
    codegen.generate(spec, out_dir)
    return out_dir


class MdmRecognitionTests(unittest.TestCase):
    def test_mdm_uart_is_classified_as_xuartlite_and_flagged_as_mdm(self) -> None:
        parsed = parse_xparameters(MDM_XPARAMETERS, PLATFORM)

        uarts = [c for c in parsed.controllers if c["type"] == "uart"]
        self.assertEqual(len(uarts), 2, uarts)
        by_subtype = {c.get("subtype", ""): c for c in uarts}
        mdm = by_subtype["mdm"]
        # Surucu YENI degil: uartlite.mdd MDM'i uartlite'in desteklenen
        # peripheral'lari arasinda sayar. Ayrimi yapan tek sey instance'tir.
        self.assertEqual(mdm["driver"], "XUartLite")
        self.assertEqual(mdm["zone"], "pl")
        # Kanonik XPAR_UARTLITE_0 alias'i AYNI adrestedir; tek denetleyiciye
        # indirilirken MDM adi kazanir (tek "debug module" diyen ad).
        self.assertEqual(mdm["instance"], "XPAR_MDM_1")
        self.assertEqual(mdm["base_address"], "0x41400000")
        self.assertNotIn("unknown_driver", [u.get("reason", "") for u in parsed.unmatched])

    def test_plain_axi_uartlite_carries_no_subtype_field_at_all(self) -> None:
        parsed = parse_xparameters(MDM_XPARAMETERS, PLATFORM)

        plain = [c for c in parsed.controllers if c["base_address"] == "0x40600000"]
        self.assertEqual(len(plain), 1)
        # Alan EK/OPSIYONEL: MDM olmayan hicbir denetleyicide gorunmez, yani
        # mevcut spec'ler bayt-bayt ayni kalir.
        self.assertNotIn("subtype", plain[0])
        self.assertEqual(plain[0]["driver"], "XUartLite")

    def test_ps_controllers_are_untouched_by_the_mdm_rule(self) -> None:
        text = """
        #define XPAR_XIICPS_0_DEVICE_ID 0
        #define XPAR_XIICPS_0_BASEADDR 0xFF020000
        #define XPAR_XUARTPS_0_DEVICE_ID 0
        #define XPAR_XUARTPS_0_BASEADDR 0xFF000000
        """

        parsed = parse_xparameters(text, PLATFORM)

        self.assertEqual([c["driver"] for c in parsed.controllers], ["XIicPs", "XUartPs"])
        self.assertTrue(all("subtype" not in c for c in parsed.controllers))

    def test_debug_only_mdm_in_the_real_xsa_fixture_yields_no_uart_controller(self) -> None:
        # test/0_dosyalar/microblaze_ax7a100.xsa `debug_module {Debug Only}`
        # ile kuruldu: mdm_1 modulunun C_USE_UART=0 ve MEMRANGE'i YOK, yani
        # uartlite.tcl da hicbir define uretmez. Tanima bu yuzden dogal olarak
        # kapalidir - ek bir bayrak gerekmez.
        xsa = ROOT / "test/0_dosyalar/microblaze_ax7a100.xsa"
        if not xsa.exists():
            self.skipTest("MicroBlaze XSA fixture yok")

        parsed = parse_xsa(xsa)

        self.assertEqual(parsed.platform, "microblaze_7series")
        self.assertEqual([c["instance"] for c in parsed.controllers if c.get("subtype") == "mdm"], [])
        uart_instances = [c["instance"] for c in parsed.controllers if c["type"] == "uart"]
        self.assertEqual(uart_instances, ["XPAR_AXI_UARTLITE_0"])

    def test_xsa_mdm_with_a_uart_memrange_is_recognized(self) -> None:
        # Ayni fixture, tek fark: mdm_1'e (UART acikken olusan) MEMRANGE
        # eklendi. Fazla varsayim yok - gercek dosyanin uzerine yazilmis
        # minimum degisiklik.
        source = ROOT / "test/0_dosyalar/microblaze_ax7a100.xsa"
        if not source.exists():
            self.skipTest("MicroBlaze XSA fixture yok")
        with zipfile.ZipFile(source) as archive:
            hwh = archive.read("design_1.hwh").decode("utf-8")
            members = {name: archive.read(name) for name in archive.namelist()}
        marker = '<PARAMETER NAME="C_USE_UART" VALUE="0"/>'
        self.assertEqual(hwh.count(marker), 1, "fixture MDM parametre bicimi degismis")
        patched = hwh.replace(
            marker,
            '<PARAMETER NAME="C_USE_UART" VALUE="1"/>'
            '<MEMRANGE INSTANCE="mdm_1" BASENAME="C_BASEADDR" BASEVALUE="0x41400000"'
            ' HIGHVALUE="0x4140ffff"/>',
        )
        self.assertNotEqual(patched, hwh)
        target = Path(tempfile.mkdtemp()) / "mdm_uart.xsa"
        with zipfile.ZipFile(target, "w") as archive:
            for name, blob in members.items():
                archive.writestr(name, patched.encode("utf-8") if name == "design_1.hwh" else blob)

        parsed = parse_xsa(target)

        mdm = [c for c in parsed.controllers if c.get("subtype") == "mdm"]
        self.assertEqual(len(mdm), 1, parsed.controllers)
        self.assertEqual(mdm[0]["type"], "uart")
        self.assertEqual(mdm[0]["driver"], "XUartLite")
        self.assertEqual(mdm[0]["instance"], "XPAR_MDM_1")
        self.assertEqual(mdm[0]["base_address"], "0x41400000")


class MdmTransportGateTests(unittest.TestCase):
    def test_mdm_transport_selected_when_platform_and_mdm_uart_are_present(self) -> None:
        spec = microblaze_spec(MDM_CONTROLLER, AXI_IIC_CONTROLLER)

        self.assertEqual(codegen._testbench_transport_agent(spec), "mdm")

    def test_mdm_transport_on_a_non_microblaze_platform_is_an_explicit_error(self) -> None:
        spec = microblaze_spec(MDM_CONTROLLER, AXI_IIC_CONTROLLER)
        spec["project"]["platform"] = "zynq_ultrascale"

        with self.assertRaises(cmodel.CodegenError) as ctx:
            codegen._testbench_transport_agent(spec)

        self.assertIn("microblaze_7series", str(ctx.exception))

    def test_mdm_transport_without_an_mdm_uart_controller_is_an_explicit_error(self) -> None:
        # Fixture kartinin durumu: MDM var ama "Debug Only" -> UART yok.
        spec = microblaze_spec(UARTLITE_CONTROLLER, AXI_IIC_CONTROLLER)

        with self.assertRaises(cmodel.CodegenError) as ctx:
            codegen._testbench_transport_agent(spec)

        message = str(ctx.exception)
        self.assertIn("subtype", message)
        self.assertIn("Debug Only", message)
        # Yanlis nedeni soylememeli: platform DOGRU.
        self.assertNotIn("yalnizca microblaze_7series", message)

    def test_auto_never_picks_mdm(self) -> None:
        # CoreSight ile ayni kural: JTAG kablosu + xsdb koprusu gerektirir,
        # sessizce secilemez. MDM tek UART olsa bile auto None doner.
        spec = microblaze_spec(MDM_CONTROLLER, AXI_IIC_CONTROLLER, transport="auto")

        self.assertIsNone(codegen._testbench_transport_agent(spec))

    def test_uart_transport_never_binds_the_mdm_instance(self) -> None:
        # MDM'in pini YOKTUR: seri ajan olarak uretilirse hicbir COM portu
        # konusamaz. Tek UART MDM ise uart transportu ajan URETMEZ.
        spec = microblaze_spec(MDM_CONTROLLER, AXI_IIC_CONTROLLER, transport="uart")
        self.assertIsNone(codegen._testbench_transport_agent(spec))

        # MDM + gercek uartlite birlikteyse uart transportu uartlite'i secer.
        spec = microblaze_spec(MDM_CONTROLLER, UARTLITE_CONTROLLER, AXI_IIC_CONTROLLER,
                               transport="uart")
        self.assertEqual(codegen._testbench_transport_agent(spec), "uart")
        self.assertEqual(
            codegen._testbench_agent_uart_controller(spec)["instance"], "XPAR_AXI_UARTLITE_0")


class MdmAgentCodegenTests(unittest.TestCase):
    def test_generated_agent_is_the_uartlite_path_bound_to_the_mdm_device_id(self) -> None:
        spec = microblaze_spec(MDM_CONTROLLER, UARTLITE_CONTROLLER, AXI_IIC_CONTROLLER)
        out_dir = generate(spec)

        header = (out_dir / "tests" / "spec2code_testbench_uart.h").read_text(encoding="utf-8")
        source = (out_dir / "tests" / "spec2code_testbench_uart.c").read_text(encoding="utf-8")
        main = (out_dir / "tests" / "spec2code_testbench_uart_main.c").read_text(encoding="utf-8")

        # Aygit MDM'dir; sirf "bir uartlite var" diye console UART'ina baglanmaz.
        self.assertIn("#define SPEC2CODE_TESTBENCH_UART_DEVICE_ID XPAR_MDM_1_DEVICE_ID", header)
        self.assertNotIn("XPAR_AXI_UARTLITE_0_DEVICE_ID", header)
        # Surucu yolu AYNEN uartlite: tek cagrili init, SetBaudRate/LookupConfig YOK.
        self.assertIn('#include "xuartlite.h"', source)
        self.assertIn(
            "XUartLite_Initialize(&S_sTestbenchUart, SPEC2CODE_TESTBENCH_UART_DEVICE_ID)", source)
        self.assertNotIn("SetBaudRate", source)
        self.assertNotIn("LookupConfig", source)
        self.assertIn("MicroBlaze Debug Module", source)
        # Banner: host bu satiri gorup MDM ajanini tanir.
        self.assertIn("S2C-MDM-AGENT-READY", main)
        self.assertNotIn("S2C-UART-AGENT-READY", main)
        self.assertIn("transport: MDM", main)

    def test_manifest_mdm_block_mirrors_coresight_and_names_the_bridge(self) -> None:
        spec = microblaze_spec(MDM_CONTROLLER, AXI_IIC_CONTROLLER)
        out_dir = generate(spec)

        manifest = json.loads(
            (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["transport_agent"], "mdm")
        self.assertEqual(manifest["mdm"], {
            "device": "mdm (MicroBlaze Debug Module UART)",
            "driver": "XUartLite",
            "instance": "XPAR_MDM_1",
            "processor": "microblaze_0",
            "target_filter": '"*MicroBlaze*#0"',
            "host_bridge": "xsdb jtagterminal -socket",
        })
        # CoreSight blogu SIZMAZ.
        self.assertNotIn("coresight", manifest)
        self.assertNotIn("uart", manifest)

    def test_mdm_project_still_publishes_the_axi_iic_scan_controllers(self) -> None:
        # Faz 2 boslugunun MDM tarafi: XIic tasarimlarinda tarama op'lari
        # uretiliyordu ama manifest bildirmiyordu.
        spec = microblaze_spec(MDM_CONTROLLER, AXI_IIC_CONTROLLER)
        out_dir = generate(spec)

        manifest = json.loads(
            (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(
            manifest["i2c_scan"]["controllers"],
            [{"id": "pl_i2c_0", "instance": "XPAR_AXI_IIC_0"}])

    def test_coresight_transport_is_untouched_on_zynqmp(self) -> None:
        # PS yolu regresyon kilidi: mdm dali CoreSight secimini etkilemez.
        spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
        spec["project"] = {**spec["project"], "name": "cs_guard",
                           "testbench_transport": "coresight"}

        self.assertEqual(codegen._testbench_transport_agent(spec), "coresight")


class MdmHostBridgeTests(unittest.TestCase):
    def test_core_filter_is_a_parameter_and_selects_the_microblaze_core(self) -> None:
        # xsdb `targets` agacinda cekirdek "MicroBlaze #0" olarak listelenir
        # (MDM'in kendisi "MicroBlaze Debug Module at USER2"); cekirdegi
        # secmek yeter, jtagterminal ebeveyne kendisi cikar.
        self.assertEqual(_core_filter("microblaze_0"), '"*MicroBlaze*#0"')
        self.assertEqual(_core_filter("MicroBlaze_1"), '"*MicroBlaze*#0"')
        # Arm hedefleri DEGISMEDI.
        self.assertEqual(_core_filter("psu_cortexa53_0"), '"*A53*#0"')
        self.assertEqual(_core_filter("psv_cortexa72_0"), '"*A72*#0"')
        self.assertEqual(_core_filter("ps7_cortexa9_0"), '"*A9*#0"')
        self.assertEqual(_core_filter("psu_cortexr5_0"), '"*R5*#0"')

    def test_manifest_target_filter_matches_the_host_core_filter(self) -> None:
        # Iki katman (codegen manifest'i / backend koprusu) ayni literali
        # tasir; sapinca bu test kirilir.
        self.assertEqual(
            codegen._TESTBENCH_MDM_TARGET_FILTER,
            _core_filter(codegen._TESTBENCH_MDM_PROCESSOR))

    def test_bridge_script_selects_the_given_filter_then_opens_jtagterminal(self) -> None:
        from backend import testbench as tb

        scripts: list[str] = []

        class FakeStdout:
            def __init__(self, port: int) -> None:
                self._lines = iter([f"S2C-DCC-PORT={port}\n"])

            def __iter__(self):
                return self._lines

        class FakePopen:
            def __init__(self, argv, **_kwargs) -> None:
                scripts.append(Path(argv[1]).read_text(encoding="utf-8"))
                self.pid = 0
                self.stdout = FakeStdout(4711)

            def kill(self) -> None:
                pass

        mdm = tb._TestbenchMdmSession("mdm-bridge")
        coresight = tb._TestbenchCoresightSession("cs-bridge")
        with mock.patch.object(tb.subprocess, "Popen", FakePopen):
            _proc, port = mdm._spawn_bridge(Path("xsdb.bat"), _core_filter("microblaze_0"))
            coresight._spawn_bridge(Path("xsdb.bat"), _core_filter("psu_cortexa53_0"))

        self.assertEqual(port, 4711)
        self.assertIn('targets -set -nocase -filter {name =~ "*MicroBlaze*#0"}', scripts[0])
        self.assertIn("set iDccPort [jtagterminal -socket]", scripts[0])
        # Ayni metot, farkli parametre: kopru kodu KOPYALANMADI.
        self.assertIn('targets -set -nocase -filter {name =~ "*A53*#0"}', scripts[1])
        self.assertEqual(
            scripts[0].replace('"*MicroBlaze*#0"', "F"),
            scripts[1].replace('"*A53*#0"', "F"))

    def test_manager_opens_an_mdm_session_with_the_microblaze_default_core(self) -> None:
        from backend.testbench import TestbenchSessionManager

        captured: dict[str, str] = {}

        def fake_bridge(_vitis: str, _url: str, processor: str):
            captured["processor"] = processor
            raise RuntimeError("bridge stop")  # baglanti kurulmadan cik

        manager = TestbenchSessionManager()
        with self.assertRaises(RuntimeError):
            manager.connect_mdm("mdm1", "C:/fake/Vitis", "", "", 1.0,
                                bridge_factory=fake_bridge)

        self.assertEqual(captured["processor"], "microblaze_0")
        status = manager.list_sessions()[0]
        self.assertEqual(status.transport, "mdm")
        manager.disconnect("mdm1")


class MdmApiRouteTests(unittest.TestCase):
    def test_connect_route_routes_mdm_to_the_mdm_session(self) -> None:
        from fastapi.testclient import TestClient

        from backend.api import routes
        from backend.main import app
        from backend.testbench import TestbenchSessionStatus

        calls: list[tuple] = []

        class FakeSessions:
            def connect_mdm(self, session_id, vitis_path, hw_server_url, processor, timeout_s):
                calls.append((session_id, vitis_path, hw_server_url, processor, timeout_s))
                return TestbenchSessionStatus(session_id=session_id, transport="mdm")

        with mock.patch.object(routes, "testbench_sessions", FakeSessions()):
            client = TestClient(app)
            response = client.post("/api/testbench/session/connect", json={
                "session_id": "mdm-route", "transport": "mdm",
                "vitis_path": "C:/Xilinx/Vitis/2023.2",
                # UI varsayilani ZynqMP cekirdegidir; MDM'de microblaze_0'a dusmeli
                # (aksi halde cekirdek filtresi "*A53*#0" olur ve hedef bulunmaz).
                "processor": "psu_cortexa53_0",
            })

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["transport"], "mdm")
        self.assertEqual(calls[0][3], "microblaze_0")

    def test_connect_route_requires_a_vitis_path_for_mdm(self) -> None:
        from fastapi.testclient import TestClient

        from backend.main import app

        client = TestClient(app)
        response = client.post("/api/testbench/session/connect", json={
            "session_id": "mdm-novitis", "transport": "mdm"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("vitis_path", response.text)


class GeneratedTelnetNamingTests(unittest.TestCase):
    def test_generated_telnet_log_source_has_zero_naming_violations(self) -> None:
        # Faz 2 bulgusu: `S_spClients` (struct-pointer DIZISI -> S_spArr...) ve
        # fonksiyon-ici `static const char cArrCrlf` (statik -> S_ oneki)
        # naming linter'da ERROR seviyesindeydi, yani telnet'li HER tasarimda
        # `spec2code_cli build` QC kapisini dusuruyordu.
        from orchestrator.qc import naming_linter

        if not naming_linter._ensure_libclang():
            self.skipTest("libclang yok; AST kontrolleri atlanir")

        spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
        spec["project"] = {**spec["project"], "name": "telnet_naming",
                           "testbench_transport": "coresight"}
        spec["controllers"].append({
            "id": "ps_eth_0", "type": "eth", "instance": "XPAR_XEMACPS_0",
            "base_address": "0xFF0B0000", "device_id": 0, "driver": "XEmacPs",
            "source": "xparameters", "zone": "ps",
        })
        out_dir = generate(spec)
        telnet = out_dir / "tests" / "spec2code_telnet_log.c"
        self.assertTrue(telnet.exists())

        ruleset = json.loads((ROOT / "std/default.ruleset.json").read_text(encoding="utf-8"))
        violations = naming_linter.lint_file(
            telnet, ruleset, [out_dir / "tests", out_dir / "drivers"])

        self.assertEqual([v.to_dict() for v in violations], [])
        # Yeni adlar gercekten uretiliyor (test sessizce bos dosyayi olculemesin).
        text = telnet.read_text(encoding="utf-8")
        self.assertIn("S_spArrClients", text)
        self.assertIn("S_cArrCrlf", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
