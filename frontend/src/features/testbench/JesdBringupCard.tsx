import { useRef, useState } from "react";
import { Link2, RefreshCw, Loader2, Radio } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button } from "@/components/ui";
import { useBoardConnection } from "@/store/connection";
import type { TestbenchManifest } from "@/lib/types";

/**
 * JESD204C / AFE7900 ilklendirme bolumu (Test Bench; Register Map ve Yakalama'dan bagimsiz - kullanici istegi 2026-09-16).
 * Sirket sirasi (jesdlink + AFE7900 surucusu): fiziksel reset darbesi -> register RESET kaldir -> cekirdek yapilandirmasi
 * -> register RESET ver -> TX kaldir -> AFE reset kaldir + Latte bring-up -> RX kaldir -> link bekleme -> AFE alarm temizle.
 * FPGA bring-up: `jesd` sanal cihazi (AFE'siz loopback / AFE ayrica ilklendirilmis). AFE + FPGA: AFE7900 cihazinin op'u.
 * Durum sozcugu: bit0 FPGA RX link, bit1 FPGA TX hazir, bit2 AFE DAC-JESD-RX link, bit3 AFE alarm yok, bit4 AFE PLL,
 * bit5 kart GT PLL lock (board_control), bit7 hepsi tamam.
 */
const BITS: Array<[number, string]> = [
  [0, "FPGA RX link (8B/10B: CGS+SYNC+RX_STARTED · 64B/66B: SH+MB lock)"],
  [1, "FPGA TX hazır (reset kalktı, SYSREF)"],
  [2, "AFE DAC-JESD-RX link (yalnız AFE op'u)"],
  [3, "AFE alarm yok (yalnız AFE op'u)"],
  [4, "AFE PLL kilitli (yalnız AFE op'u)"],
  [5, "kart GT PLL lock (board_control)"],
  [7, "hepsi tamam"],
];

export default function JesdBringupCard({ manifest }: { manifest: TestbenchManifest }) {
  const board = useBoardConnection();
  const cmdId = useRef(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [word, setWord] = useState<number | null>(null);
  const [source, setSource] = useState("");
  const [msg, setMsg] = useState("");
  const jesd = manifest.jesd;
  const afe = manifest.devices.find((d) => d.operations.some((op) => op.name === "jesd_link_bringup"));

  async function run(device: string, op: string, label: string, timeoutS: number) {
    if (!board.connected || busy) return;
    setBusy(label);
    try {
      const resp = await api.testbenchCommand({
        host: "session", port: 0, device, operation: op, command_id: cmdId.current++,
        session_id: board.sessionId, timeout_s: timeoutS,
      });
      const v = parseInt(resp.parsed.value || "", 0);
      setWord(Number.isNaN(v) ? null : v);
      setSource(label);
      setMsg(resp.parsed.message || (resp.parsed.ok === "1" ? "tamam" : "hata"));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  if (!jesd) return null;
  const ok = word !== null && (word & 0x80) !== 0;
  const off = !board.connected || busy !== null;
  return (
    <div className="rounded-md border border-border bg-inset p-3" data-testid="jesd-bringup-card">
      <div className="flex flex-wrap items-center gap-2">
        <Link2 className="h-4 w-4 text-accent" aria-hidden />
        <span className="text-sm text-text">JESD / AFE ilklendirme</span>
        <Badge tone={word === null ? "neutral" : ok ? "ok" : "warn"}>
          {word === null ? "durum yok" : `0x${word.toString(16).toUpperCase().padStart(4, "0")}`}
        </Badge>
        {source ? <span className="text-[11px] text-faint">{source}</span> : null}
      </div>
      <p className="mt-1 text-[11px] text-faint">
        {jesd.link_layer === "8b10b" ? "8B/10B" : "64B/66B"} · {jesd.lanes} lane · alt sınıf {jesd.subclass}
        {manifest.board_control ? ` · kart GPIO ${manifest.board_control.gpio_id} (${manifest.board_control.bits.length} bit)` : " · kart GPIO yok"}.
        Sıra: fiziksel reset → register kaldır → yapılandır → register ver → TX kaldır{afe ? " → AFE bring-up" : ""} → RX kaldır → link bekle.
        {!board.connected ? " Önce karta bağlan." : ""}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => void run("jesd", "jesd_link_bringup", "FPGA bring-up", 20)} disabled={off}>
          {busy === "FPGA bring-up" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />} FPGA bring-up
        </Button>
        {afe ? (
          <Button size="sm" onClick={() => void run(afe.id, "jesd_link_bringup", `AFE + FPGA bring-up (${afe.id})`, 90)} disabled={off}>
            {busy?.startsWith("AFE + FPGA") ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radio className="h-4 w-4" />} AFE + FPGA bring-up
          </Button>
        ) : null}
        <Button size="sm" variant="outline" onClick={() => void run("jesd", "jesd_link_status_read", "FPGA durum", 5)} disabled={off}>
          {busy === "FPGA durum" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} FPGA durum
        </Button>
        {afe ? (
          <Button size="sm" variant="outline" onClick={() => void run(afe.id, "jesd_link_status_read", `AFE durum (${afe.id})`, 10)} disabled={off}>
            <RefreshCw className="h-4 w-4" /> AFE durum
          </Button>
        ) : null}
      </div>
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
