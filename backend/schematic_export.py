"""Schematic disa aktarimi: draw.io (.drawio XML) ve Excel (.xlsx, kart basina bir sayfa).

Girdi frontend'in `buildSpec()` ile urettigi project.spec (controllers, muxes, devices,
connectors, boards). Kart kurallari `orchestrator/boards.py` ile aynidir: kart tanimli
degilse tek ortuk ana kart; `board_id`si bilinmeyen cihaz/mux ana karta duser.

draw.io: her kart ayri bir sayfa (diagram). Sayfa icinde soldan saga denetleyici ->
mux -> cihaz katmanlari; kenar etiketi I2C adresi / SPI CS / mux kanali. Karttan
disari giden konnektorler sag kenarda port kutusu olarak durur. Birden fazla kart
varsa "Sistem" sayfasi kartlari kutu, konnektorleri kenar olarak gosterir.
Excel: kart basina bir sayfa; Cihazlar / Mux'lar / Denetleyiciler / Konnektorler
bloklari (tum hucreler metin, `backend/xlsx_min.py`).
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape, quoteattr

from backend import xlsx_min
from orchestrator.boards import main_board_id, normalized_boards

_TRANSPORT_LABEL = {"i2c": "I2C", "spi": "SPI", "gpio": "GPIO", "eth": "ETH", "uart": "UART"}

# --- ortak model ------------------------------------------------------------------------


def _boards(spec: dict) -> list[dict]:
    boards = normalized_boards(spec)
    main = main_board_id(spec)
    return sorted(boards, key=lambda b: (0 if str(b.get("id")) == main else 1, str(b.get("name") or b.get("id"))))


def _effective_board(entity: dict, board_ids: set[str], main: str) -> str:
    bid = str(entity.get("board_id") or "")
    return bid if bid in board_ids else main


def _controller_map(spec: dict) -> dict[str, dict]:
    return {str(c.get("id")): c for c in spec.get("controllers") or []}


def _mux_map(spec: dict) -> dict[str, dict]:
    return {str(m.get("id")): m for m in spec.get("muxes") or []}


def _device_transport(device: dict, controllers: dict[str, dict]) -> str:
    attach = device.get("attach") or {}
    controller = controllers.get(str(attach.get("controller_id") or ""), {})
    ctype = str(device.get("transport") or controller.get("type") or "").lower()
    return _TRANSPORT_LABEL.get(ctype, ctype.upper() or "-")


def _attach_label(device: dict, controllers: dict[str, dict]) -> str:
    attach = device.get("attach") or {}
    if attach.get("i2c_address"):
        return f"I2C {attach['i2c_address']}"
    if attach.get("spi_chip_select") is not None:
        return f"SPI CS{attach['spi_chip_select']}"
    return _device_transport(device, controllers)


def _via_mux_label(via: dict | None) -> str:
    if not via:
        return ""
    return f"{via.get('mux_id')} ch{via.get('channel')}"


def _board_entities(spec: dict, board_id: str) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """(devices, muxes, controllers, connectors) - bu karta ait olanlar (denetleyiciler: kullanilanlar)."""
    boards = _boards(spec)
    board_ids = {str(b["id"]) for b in boards}
    main = main_board_id(spec)
    controllers = _controller_map(spec)
    muxes = _mux_map(spec)
    devices = [d for d in spec.get("devices") or [] if _effective_board(d, board_ids, main) == board_id]
    board_muxes = [m for m in spec.get("muxes") or [] if _effective_board(m, board_ids, main) == board_id]
    used_ctrl_ids: list[str] = []
    for entity in [*devices, *board_muxes]:
        cid = str((entity.get("attach") or {}).get("controller_id") or entity.get("controller_id") or "")
        via = (entity.get("attach") or {}).get("via_mux") or {}
        mux = muxes.get(str(via.get("mux_id") or ""))
        if mux and not cid:
            cid = str(mux.get("controller_id") or "")
        if cid and cid in controllers and cid not in used_ctrl_ids:
            used_ctrl_ids.append(cid)
    connectors = [c for c in spec.get("connectors") or []
                  if board_id in (str(c.get("from_board")), str(c.get("to_board")))]
    return devices, board_muxes, [controllers[c] for c in used_ctrl_ids], connectors


# --- Excel --------------------------------------------------------------------------------

_SHEET_BAD = re.compile(r"[\[\]:*?/\\]")


def _sheet_name(name: str, taken: set[str]) -> str:
    base = _SHEET_BAD.sub("_", str(name or "Kart")).strip() or "Kart"
    base = base[:31]
    candidate, n = base, 1
    while candidate.lower() in taken:
        n += 1
        suffix = f" ({n})"
        candidate = base[: 31 - len(suffix)] + suffix
    taken.add(candidate.lower())
    return candidate


def board_sheets(spec: dict) -> list[tuple[str, list[list]]]:
    """Kart basina (sayfa adi, satirlar); ana kart ilk sirada."""
    controllers = _controller_map(spec)
    boards = {str(b["id"]): b for b in _boards(spec)}
    taken: set[str] = set()
    sheets: list[tuple[str, list[list]]] = []
    for board in _boards(spec):
        bid = str(board["id"])
        devices, muxes, used_controllers, connectors = _board_entities(spec, bid)
        rows: list[list] = [
            ["Kart", str(board.get("name") or bid), "Kimlik", bid, "Rol",
             "ana kart" if str(board.get("role")) == "main" else "cevre karti", "Not", str(board.get("notes") or "")],
            [],
            ["Cihazlar"],
            ["Cihaz ID", "Parca", "Hat", "Denetleyici", "Denetleyici ornegi", "Taban adres", "Adres / CS",
             "Mux", "Mux kanali", "Reset GPIO", "IRQ", "Istenen op'lar", "Testler", "Sanal"],
        ]
        for device in devices:
            attach = device.get("attach") or {}
            controller = controllers.get(str(attach.get("controller_id") or ""), {})
            via = attach.get("via_mux") or {}
            rows.append([
                str(device.get("id") or ""), str(device.get("part") or ""), _device_transport(device, controllers),
                str(attach.get("controller_id") or ""), str(controller.get("instance") or ""),
                str(controller.get("base_address") or ""),
                str(attach.get("i2c_address") or (f"CS{attach['spi_chip_select']}" if attach.get("spi_chip_select") is not None else "")),
                str(via.get("mux_id") or ""), "" if not via else str(via.get("channel")),
                "" if attach.get("reset_gpio") in (None, "") else str(attach.get("reset_gpio")),
                "" if attach.get("irq_line") in (None, "") else str(attach.get("irq_line")),
                ", ".join(device.get("operations_requested") or []), ", ".join(device.get("tests_requested") or []),
                "evet" if device.get("simulate") else "",
            ])
        rows += [[], ["Mux'lar"], ["Mux ID", "Parca", "Denetleyici", "I2C adres", "Kanal sayisi"]]
        for mux in muxes:
            rows.append([str(mux.get("id") or ""), str(mux.get("part") or ""), str(mux.get("controller_id") or ""),
                         str(mux.get("i2c_address") or ""), str(mux.get("channels") or "")])
        rows += [[], ["Denetleyiciler (bu kartin kullandigi)"],
                 ["Denetleyici ID", "Tip", "Ornek", "Taban adres", "Surucu", "Bolge"]]
        for controller in used_controllers:
            rows.append([str(controller.get("id") or ""), str(controller.get("type") or "").upper(),
                         str(controller.get("instance") or ""), str(controller.get("base_address") or ""),
                         str(controller.get("driver") or ""), str(controller.get("zone") or "")])
        rows += [[], ["Konnektorler"], ["Konnektor ID", "Ad", "Nereden", "Nereye", "Denetleyici", "Mux / kanal", "Not"]]
        for connector in connectors:
            bus = connector.get("bus") or {}
            rows.append([
                str(connector.get("id") or ""), str(connector.get("name") or ""),
                str(boards.get(str(connector.get("from_board")), {}).get("name") or connector.get("from_board") or ""),
                str(boards.get(str(connector.get("to_board")), {}).get("name") or connector.get("to_board") or ""),
                str(bus.get("controller_id") or ""), _via_mux_label(bus.get("via_mux")), str(connector.get("notes") or ""),
            ])
        sheets.append((_sheet_name(str(board.get("name") or bid), taken), rows))
    return sheets


def xlsx_bytes(spec: dict) -> bytes:
    return xlsx_min.write_workbook(board_sheets(spec))


# --- draw.io ----------------------------------------------------------------------------

_STYLE_CONTROLLER = "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=11;"
_STYLE_MUX = "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;"
_STYLE_DEVICE = "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=11;"
_STYLE_DEVICE_SIM = "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;dashed=1;fontSize=11;"
_STYLE_CONNECTOR = "shape=hexagon;perimeter=hexagonPerimeter2;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=11;"
_STYLE_BOARD = "swimlane;whiteSpace=wrap;html=1;startSize=30;fillColor=#f5f5f5;strokeColor=#666666;fontStyle=1;"
_STYLE_EDGE = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=none;fontSize=10;"
_STYLE_EDGE_CONNECTOR = "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;dashed=1;fontSize=10;"

_W, _H, _GAP_Y = 200, 56, 24
_COL_X = {"controller": 40, "mux": 340, "device": 640, "connector": 940}


class _Page:
    def __init__(self, name: str) -> None:
        self.name = name
        self.cells: list[str] = ["<mxCell id=\"0\"/>", "<mxCell id=\"1\" parent=\"0\"/>"]
        self._next = 2

    def _id(self) -> str:
        self._next += 1
        return f"c{self._next}"

    def vertex(self, label: str, style: str, x: int, y: int, w: int = _W, h: int = _H, parent: str = "1") -> str:
        cid = self._id()
        self.cells.append(
            f"<mxCell id={quoteattr(cid)} value={quoteattr(label)} style={quoteattr(style)} vertex=\"1\" parent={quoteattr(parent)}>"
            f"<mxGeometry x=\"{x}\" y=\"{y}\" width=\"{w}\" height=\"{h}\" as=\"geometry\"/></mxCell>")
        return cid

    def edge(self, source: str, target: str, label: str = "", style: str = _STYLE_EDGE, parent: str = "1") -> str:
        cid = self._id()
        self.cells.append(
            f"<mxCell id={quoteattr(cid)} value={quoteattr(label)} style={quoteattr(style)} edge=\"1\" "
            f"parent={quoteattr(parent)} source={quoteattr(source)} target={quoteattr(target)}>"
            f"<mxGeometry relative=\"1\" as=\"geometry\"/></mxCell>")
        return cid

    def xml(self) -> str:
        return (
            f"<diagram name={quoteattr(self.name)}><mxGraphModel dx=\"1200\" dy=\"800\" grid=\"1\" gridSize=\"10\" "
            "guides=\"1\" tooltips=\"1\" connect=\"1\" arrows=\"1\" fold=\"1\" page=\"1\" pageScale=\"1\" "
            "pageWidth=\"1169\" pageHeight=\"827\"><root>" + "".join(self.cells) + "</root></mxGraphModel></diagram>"
        )


def _controller_label(controller: dict) -> str:
    return (f"<b>{escape(str(controller.get('id') or ''))}</b><br/>{escape(str(controller.get('type') or '').upper())} "
            f"{escape(str(controller.get('instance') or ''))}<br/>{escape(str(controller.get('base_address') or ''))}")


def _device_label(device: dict, controllers: dict[str, dict]) -> str:
    return (f"<b>{escape(str(device.get('id') or ''))}</b><br/>{escape(str(device.get('part') or ''))}"
            f"<br/>{escape(_attach_label(device, controllers))}" + ("<br/><i>sanal</i>" if device.get("simulate") else ""))


def _board_page(spec: dict, board: dict) -> _Page:
    controllers = _controller_map(spec)
    boards = {str(b["id"]): b for b in _boards(spec)}
    bid = str(board["id"])
    devices, muxes, used_controllers, connectors = _board_entities(spec, bid)
    page = _Page(str(board.get("name") or bid))
    rows = max(len(used_controllers), len(muxes), len(devices), len(connectors), 1)
    height = 60 + rows * (_H + _GAP_Y)
    width = _COL_X["connector"] + _W + 40 if connectors else _COL_X["device"] + _W + 40
    role = "ana kart" if str(board.get("role")) == "main" else "cevre karti"
    board_cell = page.vertex(f"{board.get('name') or bid} ({role})", _STYLE_BOARD, 20, 20, width, height)

    def y_of(index: int) -> int:
        return 50 + index * (_H + _GAP_Y)

    ctrl_cells = {str(c.get("id")): page.vertex(_controller_label(c), _STYLE_CONTROLLER, _COL_X["controller"], y_of(i), parent=board_cell)
                  for i, c in enumerate(used_controllers)}
    mux_cells: dict[str, str] = {}
    for i, mux in enumerate(muxes):
        label = (f"<b>{escape(str(mux.get('id') or ''))}</b><br/>{escape(str(mux.get('part') or ''))}"
                 f"<br/>I2C {escape(str(mux.get('i2c_address') or ''))} · {mux.get('channels') or ''} kanal")
        mux_cells[str(mux.get("id"))] = page.vertex(label, _STYLE_MUX, _COL_X["mux"], y_of(i), parent=board_cell)
        src = ctrl_cells.get(str(mux.get("controller_id") or ""))
        if src:
            page.edge(src, mux_cells[str(mux.get("id"))], "", parent=board_cell)
    for i, device in enumerate(devices):
        attach = device.get("attach") or {}
        cell = page.vertex(_device_label(device, controllers),
                           _STYLE_DEVICE_SIM if device.get("simulate") else _STYLE_DEVICE,
                           _COL_X["device"], y_of(i), parent=board_cell)
        via = attach.get("via_mux") or {}
        mux_cell = mux_cells.get(str(via.get("mux_id") or ""))
        if mux_cell:
            page.edge(mux_cell, cell, f"ch{via.get('channel')}", parent=board_cell)
        else:
            src = ctrl_cells.get(str(attach.get("controller_id") or ""))
            if src:
                page.edge(src, cell, _attach_label(device, controllers), parent=board_cell)
    for i, connector in enumerate(connectors):
        other = str(connector.get("to_board")) if str(connector.get("from_board")) == bid else str(connector.get("from_board"))
        other_name = str(boards.get(other, {}).get("name") or other)
        bus = connector.get("bus") or {}
        label = (f"<b>{escape(str(connector.get('name') or connector.get('id') or ''))}</b><br/>"
                 f"&#8594; {escape(other_name)}" + (f"<br/>{escape(_via_mux_label(bus.get('via_mux')))}" if bus.get("via_mux") else ""))
        cell = page.vertex(label, _STYLE_CONNECTOR, _COL_X["connector"], y_of(i), parent=board_cell)
        via = bus.get("via_mux") or {}
        src = mux_cells.get(str(via.get("mux_id") or "")) or ctrl_cells.get(str(bus.get("controller_id") or ""))
        if src:
            page.edge(src, cell, str(bus.get("controller_id") or ""), _STYLE_EDGE_CONNECTOR, parent=board_cell)
    return page


def _system_page(spec: dict) -> _Page:
    page = _Page("Sistem")
    boards = _boards(spec)
    cells: dict[str, str] = {}
    for i, board in enumerate(boards):
        devices, muxes, _ctrls, _conns = _board_entities(spec, str(board["id"]))
        label = (f"<b>{escape(str(board.get('name') or board['id']))}</b><br/>"
                 f"{'ana kart' if str(board.get('role')) == 'main' else 'cevre karti'} · {len(devices)} cihaz, {len(muxes)} mux")
        x = 40 + (i % 3) * 320
        y = 40 + (i // 3) * 160
        cells[str(board["id"])] = page.vertex(label, _STYLE_BOARD.replace("swimlane;", "rounded=1;"), x, y, 240, 80)
    for connector in spec.get("connectors") or []:
        src, dst = cells.get(str(connector.get("from_board"))), cells.get(str(connector.get("to_board")))
        if src and dst:
            bus = connector.get("bus") or {}
            page.edge(src, dst, f"{connector.get('name') or connector.get('id')} ({bus.get('controller_id') or ''})",
                      _STYLE_EDGE_CONNECTOR)
    return page


def drawio_xml(spec: dict) -> str:
    pages = [_board_page(spec, board) for board in _boards(spec)]
    if len(pages) > 1:
        pages.insert(0, _system_page(spec))
    project = str((spec.get("project") or {}).get("name") or "spec2code")
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        f"<mxfile host=\"Spec2Code\" type=\"device\" modified=\"\" agent=\"Spec2Code schematic export\" name={quoteattr(project)}>"
        + "".join(page.xml() for page in pages) + "</mxfile>\n"
    )
