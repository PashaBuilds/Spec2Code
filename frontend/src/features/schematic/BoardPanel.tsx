// Secili KART'in duzenleme paneli: ad/not, kart silme (icindeki cihazlar ana
// karta duser) ve kartlar arasi ISIMLI konnektorler. Konnektor elektriksel yolu
// degistirmez, hattin hangi fiziksel kabloyla hangi karta gittigini BELGELER.
import { useEffect, useState } from "react";
import { Cable, CircuitBoard, Plus, Trash2, X } from "lucide-react";
import { useStore } from "@/store/useStore";
import type { Board, Connector } from "@/lib/types";
import { effectiveBoardId } from "@/lib/boards";
import {
  Badge,
  Button,
  Card,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui";

const NONE = "__none__";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3 border-t border-border px-4 py-4 first:border-t-0">
      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-faint">{title}</h3>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

export default function BoardPanel({ board }: { board: Board }) {
  const boards = useStore((s) => s.boards);
  const devices = useStore((s) => s.devices);
  const muxes = useStore((s) => s.muxes);
  const connectors = useStore((s) => s.connectors);
  const updateBoard = useStore((s) => s.updateBoard);
  const addBoard = useStore((s) => s.addBoard);
  const deleteBoard = useStore((s) => s.deleteBoard);
  const deleteConnector = useStore((s) => s.deleteConnector);
  const select = useStore((s) => s.select);

  const [name, setName] = useState(board.name);
  const [notes, setNotes] = useState(board.notes ?? "");
  const [editingConnector, setEditingConnector] = useState<Connector | "new" | null>(null);

  // Kanvastan yeniden adlandirma da panele yansisin; form ise yalniz KART
  // degisince kapansin (ad yazarken kapanmamali).
  useEffect(() => setName(board.name), [board.id, board.name]);
  useEffect(() => setNotes(board.notes ?? ""), [board.id, board.notes]);
  useEffect(() => setEditingConnector(null), [board.id]);

  const members = [
    ...muxes.filter((m) => effectiveBoardId(m, boards) === board.id).map((m) => m.id),
    ...devices.filter((d) => effectiveBoardId(d, boards) === board.id).map((d) => d.id),
  ];
  const related = connectors.filter((c) => c.from_board === board.id || c.to_board === board.id);
  const fallback = boards.find((b) => b.id !== board.id && b.role === "main") ?? boards.find((b) => b.id !== board.id);

  function handleDelete() {
    const message = fallback
      ? `"${board.name}" silinecek. İçindeki ${members.length} birim "${fallback.name}" kartına taşınacak. Devam edilsin mi?`
      : `"${board.name}" silinecek. Bu son kart: proje kartsız duruma döner (cihazlar korunur). Devam edilsin mi?`;
    if (window.confirm(message)) deleteBoard(board.id);
  }

  return (
    <div className="space-y-3">
      <Card className="overflow-hidden">
        <div className="flex items-start justify-between gap-3 border-b border-border bg-inset/40 px-4 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <CircuitBoard className="h-4 w-4 shrink-0 text-accent" />
            <div className="min-w-0">
              <div className="truncate text-sm text-text">{board.name}</div>
              <div className="truncate font-mono text-[11px] text-faint">{board.id}</div>
            </div>
          </div>
          <Badge tone={board.role === "main" ? "accent" : "neutral"}>
            {board.role === "main" ? "ana kart" : "kart"}
          </Badge>
        </div>

        <Section title="Kart">
          <Field label="Ad">
            <Input
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                updateBoard(board.id, { name: e.target.value });
              }}
              onBlur={() => {
                if (name.trim()) return;
                setName("Kart");
                updateBoard(board.id, { name: "Kart" });
              }}
            />
          </Field>
          <Field label="Not">
            <Input
              value={notes}
              placeholder="ör. FPGA + PS, 10-pin FFC ile RF karta"
              onChange={(e) => {
                setNotes(e.target.value);
                updateBoard(board.id, { notes: e.target.value });
              }}
            />
          </Field>
          <div className="flex items-center justify-between text-xs">
            <span className="text-faint">içindeki birim</span>
            <span className="font-mono text-muted">{members.length}</span>
          </div>
          {board.role === "main" && (
            <p className="text-[11px] text-faint">
              Denetleyiciler (FPGA/PS) tanımı gereği ana karttadır; kart değiştiremezler.
            </p>
          )}
        </Section>

        <Section title="Konnektörler">
          {related.length === 0 && !editingConnector && (
            <p className="text-[11px] text-faint">
              Bu kartın başka bir karta giden fiziksel bağlantısı henüz tanımlı değil.
            </p>
          )}
          <div className="space-y-2">
            {related.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between gap-2 rounded border border-border bg-inset px-2 py-1.5"
              >
                <button
                  className="flex min-w-0 flex-1 items-center gap-2 text-left"
                  onClick={() => setEditingConnector(c)}
                >
                  <Cable className="h-3.5 w-3.5 shrink-0 text-muted" />
                  <span className="min-w-0 truncate font-mono text-[11px] text-text">{c.name}</span>
                  <span className="shrink-0 font-mono text-[10px] text-faint">
                    {c.from_board} → {c.to_board}
                  </span>
                </button>
                <button
                  className="shrink-0 text-faint hover:text-danger"
                  title="Konnektörü sil"
                  onClick={() => deleteConnector(c.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
          {editingConnector ? (
            <ConnectorForm
              board={board}
              connector={editingConnector === "new" ? null : editingConnector}
              onClose={() => setEditingConnector(null)}
            />
          ) : (
            <Button
              variant="outline"
              size="sm"
              disabled={boards.length < 2}
              title={boards.length < 2 ? "Konnektör için en az iki kart gerekir" : undefined}
              onClick={() => setEditingConnector("new")}
            >
              <Plus className="h-4 w-4" /> Konnektör ekle
            </Button>
          )}
        </Section>

        <Section title="Tehlikeli bölge">
          <Button variant="danger" size="sm" onClick={handleDelete}>
            <Trash2 className="h-4 w-4" /> Kartı sil
          </Button>
          <p className="text-[11px] text-faint">
            {fallback
              ? `İçindeki birimler "${fallback.name}" kartına taşınır, hiçbir cihaz silinmez.`
              : "Son kart silinince proje kartsız duruma döner; cihazlar korunur."}
          </p>
        </Section>
      </Card>

      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => addBoard("")}>
          <Plus className="h-4 w-4" /> Kart ekle
        </Button>
        <Button variant="ghost" size="sm" onClick={() => select(null)}>
          <X className="h-4 w-4" /> Seçimi bırak
        </Button>
      </div>
    </div>
  );
}

function ConnectorForm({
  board,
  connector,
  onClose,
}: {
  board: Board;
  connector: Connector | null;
  onClose: () => void;
}) {
  const boards = useStore((s) => s.boards);
  const controllers = useStore((s) => s.controllers);
  const muxes = useStore((s) => s.muxes);
  const addConnector = useStore((s) => s.addConnector);
  const updateConnector = useStore((s) => s.updateConnector);

  const other = boards.find((b) => b.id !== board.id);
  const [name, setName] = useState(connector?.name ?? "J1 → J1");
  const [fromBoard, setFromBoard] = useState(connector?.from_board ?? board.id);
  const [toBoard, setToBoard] = useState(connector?.to_board ?? other?.id ?? board.id);
  const [controllerId, setControllerId] = useState(
    connector?.bus.controller_id ?? controllers[0]?.id ?? "",
  );
  const [muxId, setMuxId] = useState(connector?.bus.via_mux?.mux_id ?? NONE);
  const [channel, setChannel] = useState(String(connector?.bus.via_mux?.channel ?? 0));
  const [notes, setNotes] = useState(connector?.notes ?? "");

  const mux = muxes.find((m) => m.id === muxId);
  const valid = name.trim() !== "" && fromBoard !== toBoard && controllerId !== "";

  function submit() {
    if (!valid) return;
    const payload = {
      name: name.trim(),
      from_board: fromBoard,
      to_board: toBoard,
      bus: {
        controller_id: controllerId,
        via_mux: mux ? { mux_id: mux.id, channel: Number(channel) } : null,
      },
      notes: notes.trim(),
    };
    if (connector) updateConnector(connector.id, payload);
    else addConnector(payload);
    onClose();
  }

  return (
    <div className="space-y-3 rounded border border-accent/40 bg-inset/60 p-3">
      <Field label="Ad">
        <Input value={name} placeholder="J7 → J1" onChange={(e) => setName(e.target.value)} />
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Kaynak kart">
          <Select value={fromBoard} onValueChange={setFromBoard}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {boards.map((b) => (
                <SelectItem key={b.id} value={b.id}>
                  {b.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Hedef kart">
          <Select value={toBoard} onValueChange={setToBoard}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {boards.map((b) => (
                <SelectItem key={b.id} value={b.id}>
                  {b.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      </div>
      <Field label="Hat (denetleyici)">
        <Select value={controllerId} onValueChange={setControllerId}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {controllers.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.id} ({c.type.toUpperCase()})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Switch (ops.)">
          <Select value={muxId} onValueChange={setMuxId}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>yok</SelectItem>
              {muxes.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        {mux && (
          <Field label="Kanal">
            <Select value={channel} onValueChange={setChannel}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: mux.channels }, (_, i) => (
                  <SelectItem key={i} value={String(i)}>
                    ch {i}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        )}
      </div>
      <Field label="Not">
        <Input value={notes} placeholder="ör. 10-pin FFC" onChange={(e) => setNotes(e.target.value)} />
      </Field>
      {fromBoard === toBoard && (
        <p className="text-[11px] text-danger">Konnektörün iki ucu aynı kart olamaz.</p>
      )}
      <div className="flex gap-2">
        <Button size="sm" disabled={!valid} onClick={submit}>
          {connector ? "Kaydet" : "Ekle"}
        </Button>
        <Button variant="ghost" size="sm" onClick={onClose}>
          Vazgeç
        </Button>
      </div>
    </div>
  );
}
