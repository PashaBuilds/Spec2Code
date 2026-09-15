import { useEffect, useRef, useState, type ReactNode } from "react";
import { CircleHelp, Download, FileJson, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { PLATFORM_LABELS, RUNTIMES, useStore } from "@/store/useStore";
import type { LlmConfig, PlatformId, PlatformInfo, ProjectSpec } from "@/lib/types";
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
import { VisualBackdrop } from "@/components/visuals";

/** Dürüst platform destek matrisi: neyin doğrulandığı, neyin kapılı olduğu. */
const PLATFORM_SUPPORT: Record<PlatformId, { tone: "ok" | "warn"; text: string }> = {
  zynq_ultrascale: {
    tone: "ok",
    text: "Tam destek — I2C/SPI/QSPI sürücüleri, lwIP + UART test bench, JTAG Build&Run; ZCU102 ile uçtan uca doğrulandı.",
  },
  versal: {
    tone: "ok",
    text: "Doğrulandı (VCK190) — I2C/QSPI sürücüleri, UART (XUartPsv) ajanı, workspace + PDI ile Build&Run. Ethernet/lwIP ajanı Versal'da üretilmez (UART kullanılır); OSPI/CANFD cihazları henüz desteklenmez (açık hata).",
  },
  zynq_7000: {
    tone: "warn",
    text: "I2C/SPI cihazları + UART ajanı + ps7_init ile Build&Run desteklenir. PS QSPI (XQspiPs) henüz desteklenmez — QSPI flash bağlanırsa üretim açık hatayla durur. lwIP ajanı 7000'de üretilmez.",
  },
  microblaze_7series: {
    tone: "ok",
    text: "Nexys A7-100T ile kartta doğrulandı — AXI IIC (XIic, ADT7420), AXI Quad SPI (S25FL128S flash), AXI GPIO (LED/anahtar/buton), AXI UARTLite / MDM UART / AXI EthernetLite (lwIP) ajanları, Register Map Test IP, QSPI flash'tan açılış; Vitis 2023.2 (xsct) ve 2025.2 (Unified/SDT) akışları. Bitstream kartın XDC'sini zorunlu kılar; firmware LMB'den koşar (256KB yerel bellek seçin, 128KB'de link taşar). DDR/MIG yok.",
  },
};

/** '?' yardim baloncugu: icerik varsayilan gizli, simgeye gelince/tiklayinca acilir (kullanici istegi 2026-09-13:
 *  aciklama metinleri ekranda yer kaplamasin). */
function HelpPopover({ label, tone = "neutral", width = "w-80", children }: {
  label: string; tone?: "ok" | "warn" | "neutral"; width?: string; children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const icon = tone === "ok" ? "text-ok" : tone === "warn" ? "text-warn" : "text-muted";
  const box = tone === "ok" ? "border-ok/25 text-muted" : tone === "warn" ? "border-warn/30 text-warn" : "border-border text-muted";
  return (
    <span className="relative inline-flex" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" aria-label={label} title={label} onClick={() => setOpen((v) => !v)} className={icon + " hover:opacity-80"}>
        <CircleHelp className="h-4 w-4" />
      </button>
      {open ? (
        <span role="tooltip" className={`absolute left-0 top-6 z-30 ${width} rounded-md border bg-inset px-2.5 py-1.5 text-xs leading-relaxed shadow-lg ${box}`}>
          {children}
        </span>
      ) : null}
    </span>
  );
}

function PlatformSupportNote({ platform }: { platform: PlatformId }) {
  const note = PLATFORM_SUPPORT[platform];
  if (!note) return null;
  return <HelpPopover label="Platform destek notu" tone={note.tone}>{note.text}</HelpPopover>;
}

const PREFIXES = [
  ["unsigned char", "uc"],
  ["char", "c"],
  ["unsigned short", "us"],
  ["short", "s"],
  ["unsigned int", "ui"],
  ["int", "i"],
  ["unsigned long", "ul"],
  ["unsigned long long", "ull"],
];

export default function ProjectSetup() {
  const project = useStore((s) => s.project);
  const customIps = useStore((s) => s.customIps);
  const setProject = useStore((s) => s.setProject);
  // "auto" transport secenegi arayuzden kaldirildi (2026-09-13); eski kayitli projelerde uart'a cekilir.
  useEffect(() => {
    if (!project.testbench_transport || project.testbench_transport === "auto") setProject({ testbench_transport: "uart" as never });
  }, [project.testbench_transport, setProject]);
  const codingStandardRef = useStore((s) => s.codingStandardRef);
  const llm = useStore((s) => s.llm);
  const setLlm = useStore((s) => s.setLlm);
  const buildSpec = useStore((s) => s.buildSpec);
  const loadSpec = useStore((s) => s.loadSpec);
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [tools, setTools] = useState<Record<string, string | null>>({});
  const [projectIoMessage, setProjectIoMessage] = useState<string | null>(null);
  const [projectIoError, setProjectIoError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.platforms().then(setPlatforms).catch(() => setPlatforms([]));
    api.health().then((h) => setTools(h.tools)).catch(() => setTools({}));
  }, []);

  const current = platforms.find((p) => p.id === project.platform);
  const cores = current?.cores ?? [];
  const setLlmNumber = (
    key: "timeout_s" | "max_tokens" | "max_response_chars" | "retries",
    value: string,
  ) => {
    setLlm({ [key]: value === "" ? undefined : Number(value) } as Partial<LlmConfig>);
  };

  function downloadSpec() {
    setProjectIoMessage(null);
    setProjectIoError(null);
    const spec = buildSpec();
    const blob = new Blob([JSON.stringify(spec, null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${spec.project.name}.project.spec.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setProjectIoMessage("project.spec.json exported");
  }

  async function loadProjectSpec(file: File | undefined) {
    if (!file) return;
    setProjectIoMessage(null);
    setProjectIoError(null);
    try {
      const spec = JSON.parse(await file.text()) as ProjectSpec;
      const validation = await api.validate(spec);
      if (!validation.valid) {
        throw new Error(validation.errors.map((e) => `${e.path}: ${e.message}`).join("; "));
      }
      const platform = await api.platform(spec.project.platform);
      loadSpec(spec, { zones: platform.zones, cores: platform.cores });
      setProjectIoMessage(`${file.name} loaded`);
    } catch (err) {
      setProjectIoError(err instanceof Error ? err.message : String(err));
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Card className="relative overflow-hidden p-5">
      <VisualBackdrop asset="setup" className="h-32" opacity={0.42} position="right top" mask="header" />
      <div className="relative z-10">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-text">Project</h2>
        <div className="flex items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={(e) => void loadProjectSpec(e.target.files?.[0])}
          />
          <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
            <Upload className="h-4 w-4" /> Load
          </Button>
          <Button variant="outline" size="sm" onClick={downloadSpec}>
            <Download className="h-4 w-4" /> Save
          </Button>
        </div>
      </div>
      <div className="space-y-4">
        {customIps.length > 0 && (
          <div className="rounded-md border border-border/60 bg-inset/40 px-3 py-2 text-xs">
            <div className="mb-1 font-semibold text-text">Custom IP ({customIps.length}) — shell komutu: <span className="font-mono">&lt;id&gt; dump | read &lt;n&gt; | write &lt;n&gt; &lt;value&gt;</span></div>
            <ul className="space-y-0.5 font-mono text-[11px] text-muted">
              {customIps.map((ip) => (
                <li key={ip.id}>
                  {ip.id} · {ip.base_address}
                  {ip.high_address ? `..${ip.high_address}` : ""} · {ip.register_count} × 4 B
                  {ip.ip_name ? ` · ${ip.ip_name}` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
        {(projectIoMessage || projectIoError) && (
          <div
            className={
              projectIoError
                ? "rounded-md border border-danger/40 bg-danger/15 px-3 py-2 text-xs text-danger"
                : "rounded-md border border-ok/30 bg-ok/10 px-3 py-2 text-xs text-ok"
            }
          >
            {projectIoError ?? projectIoMessage}
          </div>
        )}

        <div className="space-y-1.5">
          <Label>Project name</Label>
          <Input
            value={project.name}
            onChange={(e) => setProject({ name: e.target.value.replace(/[^A-Za-z0-9_]/g, "_") })}
            placeholder="radar_io_board"
          />
        </div>

        <div className="space-y-1.5">
          <Label className="inline-flex items-center gap-1.5">Platform <PlatformSupportNote platform={project.platform} /></Label>
          <Select
            value={project.platform}
            onValueChange={(v) => {
              const p = platforms.find((x) => x.id === (v as PlatformId));
              setProject({ platform: v as PlatformId, target_core: p?.cores[0]?.id ?? project.target_core });
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(PLATFORM_LABELS) as PlatformId[]).map((id) => (
                <SelectItem key={id} value={id}>
                  {PLATFORM_LABELS[id]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {current && <p className="text-xs text-faint">{current.summary}</p>}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Target core</Label>
            <Select value={project.target_core} onValueChange={(v) => setProject({ target_core: v })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {cores.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Runtime</Label>
            <Select value={project.runtime} onValueChange={(v) => setProject({ runtime: v as never })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RUNTIMES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r === "freertos" ? "FreeRTOS" : "bare-metal"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2 space-y-1.5">
            <Label>Test bench transport</Label>
            <Select
              value={!project.testbench_transport || project.testbench_transport === "auto" ? "uart" : project.testbench_transport}
              onValueChange={(v) => setProject({ testbench_transport: v as never })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="eth">Ethernet (lwIP TCP agent)</SelectItem>
                <SelectItem value="uart">UART (seri agent)</SelectItem>
                <SelectItem value="coresight">CoreSight DCC — JTAG, psu_coresight_0 (ZynqMP)</SelectItem>
                <SelectItem value="mdm">MDM UART — JTAG, MicroBlaze Debug Module (microblaze_7series)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="col-span-2 space-y-1.5">
            <Label>BSP akışı (Vitis sürümü)</Label>
            <Select value={project.bsp_flow ?? "classic"} onValueChange={(v) => setProject({ bsp_flow: v as never })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="classic">Classic — Vitis ≤ 2023.2 (xsct, XPAR_*_DEVICE_ID)</SelectItem>
                <SelectItem value="sdt">SDT — Vitis Unified ≥ 2024.1 (System Device Tree, XPAR_*_BASEADDR, vitis -s)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Üretilen C tek akışa göre çıkar: SDT'de LookupConfig/Initialize taban adresle çağrılır ve BSP DEVICE_ID
              makrosu üretmez. xparameters.h yüklerken başlıkta DEVICE_ID yoksa bu alan kendiliğinden SDT olur.
            </p>
          </div>
          {project.testbench_transport === "eth" && (
          <div className="col-span-2 space-y-1.5">
            <Label>Test bench ağı (Ethernet / lwIP ajanı)</Label>
            {/* Alanlar alt alta (kullanici istegi 2026-09-16): yan yana sigmiyor, degerler kesiliyordu. */}
            <div className="space-y-1.5">
              {(
                [
                  ["ip", "IP", "18.2.75.121"],
                  ["netmask", "Alt ağ maskesi", "255.255.255.0"],
                  ["gateway", "Gateway", "18.2.75.1"],
                  ["mac", "MAC", "00:0A:35:00:01:02"],
                ] as const
              ).map(([key, label, placeholder]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="w-28 shrink-0 text-[11px] text-faint">{label}</span>
                  <Input
                    value={project.testbench_network?.[key] ?? ""}
                    placeholder={placeholder}
                    spellCheck={false}
                    onChange={(e) =>
                      setProject({ testbench_network: { ...(project.testbench_network ?? {}), [key]: e.target.value } })
                    }
                  />
                </div>
              ))}
              <div className="flex items-center gap-3">
                <span className="w-28 shrink-0 text-[11px] text-faint">TCP port</span>
                <Input
                  className="max-w-[10rem]"
                  value={project.testbench_network?.port ?? ""}
                  placeholder="5000"
                  inputMode="numeric"
                  onChange={(e) =>
                    setProject({
                      testbench_network: {
                        ...(project.testbench_network ?? {}),
                        port: e.target.value === "" ? undefined : Number.parseInt(e.target.value, 10) || 0,
                      },
                    })
                  }
                />
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Statik adres, DHCP yok. Ajan başlığındaki makrolara ve manifest'e yazılır; Bağlantı kartı host/port'u
              buradan alır. Boş bırakılan alan varsayılanını kullanır. PC adaptörü aynı alt ağda olmalı.
            </p>
          </div>
          )}
        </div>

        <div className="rounded-md border border-border bg-inset p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-sm text-text">
              <FileJson className="h-4 w-4 text-accent" />
              Sabit kodlama standardı
              <HelpPopover label="Kodlama standardı özeti" width="w-96">
                <span className="block space-y-2">
                  <span className="block">
                    Generate ve QC her zaman default ruleset ile çalışır; Word/JSON standard import akışı kullanılmaz.
                  </span>
                  <span className="grid grid-cols-2 gap-x-3 gap-y-1">
                    {PREFIXES.map(([type, prefix]) => (
                      <span key={type} className="flex items-center justify-between gap-2">
                        <span className="truncate font-mono text-faint">{type}</span>
                        <span className="font-mono text-text">{prefix}</span>
                      </span>
                    ))}
                  </span>
                  <span className="grid gap-0.5 font-mono text-[11px] text-faint">
                    <span>camelCase identifiers, Allman braces, 4 spaces, CRLF</span>
                    <span>function: tca9548aChannelSelect(...)</span>
                    <span>pointer style: XIicPs* spIic; unsigned char* ucpValue</span>
                    <span>types: unsigned char/short/int/long; no uint*_t</span>
                    <span>typedef: SOrnekStruct; enum: EOrnekEnum</span>
                    <span>struct variable: sMyStruct; pointer: spMyStruct</span>
                    <span>array: prefix+Arr; global G_; static S_</span>
                  </span>
                </span>
              </HelpPopover>
            </div>
            <Badge tone="neutral">{codingStandardRef}</Badge>
          </div>
        </div>

        <div className="rounded-md border border-border bg-inset p-3">
          <label className="flex cursor-pointer items-center justify-between">
            <span className="flex items-center gap-2 text-sm text-text">
              LLM assist
              <Badge tone={llm.enabled ? "accent" : "neutral"}>{llm.enabled ? "on" : "off"}</Badge>
            </span>
            <input
              type="checkbox"
              checked={llm.enabled}
              onChange={(e) => setLlm({ enabled: e.target.checked })}
              className="h-4 w-4 accent-[var(--accent)]"
            />
          </label>
          <p className="mt-1 text-xs text-faint">
            Deterministic by default. When on, an OpenAI-compatible endpoint can assist QC fixes
            (QC still gates every accepted change).
          </p>
          {llm.enabled && (
            <div className="mt-3 space-y-2">
              <Input
                value={llm.base_url ?? ""}
                onChange={(e) => setLlm({ base_url: e.target.value })}
                placeholder="base_url (e.g. http://localhost:1234/v1)"
              />
              <Input
                value={llm.model ?? ""}
                onChange={(e) => setLlm({ model: e.target.value })}
                placeholder="exact model name exposed by the server"
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  value={llm.api_key ?? ""}
                  onChange={(e) => setLlm({ api_key: e.target.value })}
                  placeholder="api_key (optional)"
                  type="password"
                />
                <Input
                  type="number"
                  min={1}
                  value={llm.timeout_s ?? ""}
                  onChange={(e) => setLlmNumber("timeout_s", e.target.value)}
                  placeholder="timeout seconds"
                />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Input
                  type="number"
                  min={128}
                  value={llm.max_tokens ?? ""}
                  onChange={(e) => setLlmNumber("max_tokens", e.target.value)}
                  placeholder="max_tokens"
                />
                <Input
                  type="number"
                  min={1024}
                  value={llm.max_response_chars ?? ""}
                  onChange={(e) => setLlmNumber("max_response_chars", e.target.value)}
                  placeholder="max chars"
                />
                <Input
                  type="number"
                  min={0}
                  max={3}
                  value={llm.retries ?? ""}
                  onChange={(e) => setLlmNumber("retries", e.target.value)}
                  placeholder="retries"
                />
              </div>
              <p className="text-[11px] text-faint">
                Enter the exact model id from the OpenAI-compatible server, e.g. a Kimi or Qwen model name.
              </p>
            </div>
          )}
        </div>

        <div className="rounded-md border border-border bg-inset p-3">
          <div className="mb-2 flex items-center gap-2 text-sm text-text">
            <FileJson className="h-4 w-4 text-accent" />
            Toolchain
          </div>
          <div className="grid grid-cols-2 gap-2">
            {["clang-format", "clang-tidy", "cppcheck", "libclang"].map((name) => (
              <div key={name} className="flex min-w-0 items-center justify-between gap-2">
                <span className="truncate font-mono text-[11px] text-muted">{name}</span>
                <Badge tone={tools[name] ? "ok" : "warn"}>{tools[name] ? "ok" : "missing"}</Badge>
              </div>
            ))}
          </div>
        </div>
      </div>
      </div>
    </Card>
  );
}
