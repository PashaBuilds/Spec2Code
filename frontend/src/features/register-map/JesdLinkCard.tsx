import { useRef, useState } from "react";
import { Link2, RefreshCw, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button } from "@/components/ui";
import { useBoardConnection } from "@/store/connection";

/**
 * JESD204C FPGA link bring-up / durum (cihazdan bagimsiz `jesd` ajan cihazi; drivers/ip/jesdlink):
 * reset ver -> kaldir (cmd+data acik) -> RX link reset -> SYSREF darbesi (GPIO varsa) -> RX link bekle -> TX kontrol.
 * Durum sozcugu: bit0 FPGA RX link, bit1 FPGA TX hazir, bit2-4 AFE tarafi (yalniz AFE op'unda), bit7 hepsi tamam.
 */
const BITS: Array<[number, string]> = [
  [0, "FPGA RX link (SH+MB kilit / CGS+SYNC)"],
  [1, "FPGA TX hazır (reset kalktı, SYSREF)"],
  [2, "AFE DAC-JESD-RX link"],
  [3, "AFE alarm yok"],
  [4, "AFE PLL kilitli"],
  [7, "hepsi tamam"],
];

export default function JesdLinkCard() {
  const board = useBoardConnection();
  const cmdId = useRef(1);
  const [busy, setBusy] = useState(false);
  const [word, setWord] = useState<number | null>(null);
  const [msg, setMsg] = useState("");

  async function run(op: "jesd_link_bringup" | "jesd_link_status_read") {
    if (!board.connected || busy) return;
    setBusy(true);
    try {
      const resp = await api.testbenchCommand({
        host: "session", port: 0, device: "jesd", operation: op, command_id: cmdId.current++,
        session_id: board.sessionId, timeout_s: op === "jesd_link_bringup" ? 15 : 5,
      });
      const v = parseInt(resp.parsed.value || "", 0);
      setWord(Number.isNaN(v) ? null : v);
      setMsg(resp.parsed.message || (resp.parsed.ok === "1" ? "tamam" : "hata"));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const ok = word !== null && (word & 0x80) !== 0;
  return (
    <div className="rounded-md border border-border bg-inset p-3" data-testid="jesd-link-card">
      <div className="flex flex-wrap items-center gap-2">
        <Link2 className="h-4 w-4 text-accent" aria-hidden />
        <span className="text-sm text-text">JESD204C link (FPGA çekirdekleri)</span>
        <Badge tone={word === null ? "neutral" : ok ? "ok" : "warn"}>
          {word === null ? "durum yok" : `0x${word.toString(16).toUpperCase().padStart(4, "0")}`}
        </Badge>
        <span className="ml-auto flex gap-2">
          <Button size="sm" variant="outline" onClick={() => void run("jesd_link_status_read")} disabled={!board.connected || busy}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Durum
          </Button>
          <Button size="sm" onClick={() => void run("jesd_link_bringup")} disabled={!board.connected || busy}>
            <Link2 className="h-4 w-4" /> Link bring-up
          </Button>
        </span>
      </div>
      <p className="mt-1 text-[11px] text-faint">
        reset ver → kaldır (cmd+veri açık) → RX link reset → SYSREF darbesi (GPIO varsa) → RX link bekle → TX kontrol.
        {!board.connected ? " Önce karta bağlan." : ""}
      </p>
      {word !== null ? (
        <div className="mt-2 grid gap-1 text-xs sm:grid-cols-2">
          {BITS.map(([bit, label]) => (
            <div key={bit} className="flex items-center gap-2">
              <span className={(word >> bit) & 1 ? "text-ok" : "text-faint"}>{(word >> bit) & 1 ? "●" : "○"}</span>
              <span className="font-mono text-faint">bit{bit}</span>
              <span className="text-muted">{label}</span>
            </div>
          ))}
        </div>
      ) : null}
      {msg ? <p className="mt-1 font-mono text-[11px] text-muted">{msg}</p> : null}
    </div>
  );
}
