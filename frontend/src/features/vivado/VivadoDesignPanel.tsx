import { useEffect, useRef, useState } from "react";
import { ArrowLeft, CircuitBoard, Hammer, ListTree, Loader2, PackageCheck, Wand2 } from "lucide-react";
import { api, openVivadoSocket } from "@/lib/api";
import { useStore } from "@/store/useStore";
import { cn } from "@/lib/utils";
import { Badge, Button, Card, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";
import type { PlatformId, XsaParseResult } from "@/lib/types";

/** Vivado Tasarımı (Faz A): PS konfigürasyon formu → arka planda batch
 * Vivado → İKİ AŞAMALI teslim: (1) sentezsiz .xsa dakikalar içinde hazır
 * olur ve tek tuşla Setup/şematik akışına bağlanır; (2) istenirse sentez +
 * implementasyon ile .bit (ZynqMP) / .pdi (Versal) üretilir. Zynq-7000
 * bilinçli olarak kapsam dışı. MIO değerleri Vivado tarafından doğrulanır —
 * geçersiz atama 1. aşamada net hata olarak döner. */

const VIVADO_JOB_KEY = "spec2code.vivadoDesignJobId";

type VivadoEvent = { event: string; message?: string; line?: string; stage?: string; progress?: number; xsa_path?: string; image_path?: string; xsa_bit_path?: string; regmap_ip_base?: string; _seq?: number };

interface PeripheralRow {
  kind: string;
  label: string;
  mioPlaceholder: string;
  enabled: boolean;
  mio: string;
  // Yalnız QSPI (ZynqMP): mod IO'yu belirler (Single=MIO 0..5,
  // Dual Parallel=MIO 0..12 — zcu102'den doğrulanmış değerler).
  qspiMode: "Single" | "Dual Parallel";
  qspiDataMode: "" | "x1" | "x2" | "x4";
  qspiFbclk: boolean;
}

const ZYNQMP_ROWS: Pick<PeripheralRow, "kind" | "label" | "mioPlaceholder">[] = [
  { kind: "uart0", label: "UART0", mioPlaceholder: "MIO 18 .. 19" },
  { kind: "uart1", label: "UART1", mioPlaceholder: "MIO 20 .. 21" },
  { kind: "i2c0", label: "I2C0", mioPlaceholder: "MIO 14 .. 15" },
  { kind: "i2c1", label: "I2C1", mioPlaceholder: "MIO 16 .. 17" },
  { kind: "spi0", label: "SPI0", mioPlaceholder: "MIO 38 .. 43" },
  { kind: "spi1", label: "SPI1", mioPlaceholder: "MIO 6 .. 11" },
  { kind: "qspi", label: "QSPI", mioPlaceholder: "MIO 0 .. 12" },
  { kind: "gem3", label: "GEM3 (Ethernet)", mioPlaceholder: "MIO 64 .. 75" },
  { kind: "sd1", label: "SD1", mioPlaceholder: "MIO 39 .. 51" },
];

const VERSAL_ROWS: Pick<PeripheralRow, "kind" | "label" | "mioPlaceholder">[] = [
  { kind: "uart0", label: "UART0", mioPlaceholder: "PMC_MIO 42 .. 43" },
  { kind: "uart1", label: "UART1", mioPlaceholder: "PMC_MIO 40 .. 41" },
  { kind: "i2c0", label: "I2C0", mioPlaceholder: "PMC_MIO 46 .. 47" },
  { kind: "i2c1", label: "I2C1", mioPlaceholder: "PMC_MIO 44 .. 45" },
];

// PSU__DDRC__ alanları: adlar resmi zcu102.xsa hardware handoff'undan.
// Boş bırakılan alan gönderilmez (Vivado varsayılanında kalır).
const DDR_FIELDS: Array<{ key: string; label: string; placeholder: string }> = [
  { key: "PSU__DDRC__MEMORY_TYPE", label: "Bellek tipi", placeholder: "DDR 4" },
  { key: "PSU__DDRC__SPEED_BIN", label: "Hız sınıfı", placeholder: "DDR4_2400R" },
  { key: "PSU__DDRC__COMPONENTS", label: "Yapı", placeholder: "Components" },
  { key: "PSU__DDRC__DEVICE_CAPACITY", label: "Yonga kapasitesi", placeholder: "8192 MBits" },
  { key: "PSU__DDRC__DRAM_WIDTH", label: "Yonga genişliği", placeholder: "16 Bits" },
  { key: "PSU__DDRC__BUS_WIDTH", label: "Veri yolu", placeholder: "64 Bit" },
  { key: "PSU__DDRC__ECC", label: "ECC", placeholder: "Disabled" },
  { key: "PSU__DDRC__CL", label: "CL", placeholder: "17" },
  { key: "PSU__DDRC__CWL", label: "CWL", placeholder: "16" },
  { key: "PSU__DDRC__T_RCD", label: "tRCD", placeholder: "17" },
  { key: "PSU__DDRC__T_RP", label: "tRP", placeholder: "17" },
  { key: "PSU__DDRC__T_RC", label: "tRC (ns)", placeholder: "45.32" },
  { key: "PSU__DDRC__T_RAS_MIN", label: "tRAS min (ns)", placeholder: "32" },
  { key: "PSU__DDRC__T_FAW", label: "tFAW (ns)", placeholder: "21.0" },
  { key: "PSU__DDRC__ROW_ADDR_COUNT", label: "Satır adres biti", placeholder: "16" },
  { key: "PSU__DDRC__COL_ADDR_COUNT", label: "Kolon adres biti", placeholder: "10" },
  { key: "PSU__DDRC__BANK_ADDR_COUNT", label: "Banka adres biti", placeholder: "2" },
  { key: "PSU__DDRC__BG_ADDR_COUNT", label: "Bank group biti", placeholder: "1" },
  { key: "PSU__DDRC__RANK_ADDR_COUNT", label: "Rank adres biti", placeholder: "0" },
];

function buildRows(platform: string): PeripheralRow[] {
  const source = platform === "versal" ? VERSAL_ROWS : ZYNQMP_ROWS;
  return source.map((row) => ({
    ...row,
    enabled: row.kind === "uart0" || row.kind === "i2c0",
    mio: "",
    qspiMode: "Single" as const,
    qspiDataMode: "" as const,
    qspiFbclk: false,
  }));
}

// --- Form kalıcılığı: son girilen ayarlar localStorage'da tutulur; her seferinde
// yeniden girmeye gerek yok. Dosya yolları (vivadoDir/part/temp) kendi
// anahtarlarında, gerisi tek bir JSON snapshot'ta. --- //
const VIVADO_FORM_KEY = "spec2code.vivadoForm";
type SavedForm = {
  platform?: "zynq_ultrascale" | "versal"; designName?: string; refClk?: string;
  ddrMode?: "none" | "model" | "custom"; ddrValues?: Record<string, string>;
  ddrModel?: string; ddrBusWidth?: string; makeBit?: boolean; addTestIp?: boolean;
  rows?: Array<Pick<PeripheralRow, "kind" | "enabled" | "mio" | "qspiMode" | "qspiDataMode" | "qspiFbclk">>;
};
function loadVivadoForm(): SavedForm {
  try { return (JSON.parse(localStorage.getItem(VIVADO_FORM_KEY) || "{}") as SavedForm) || {}; }
  catch { return {}; }
}
function restoreRows(platform: string, saved?: SavedForm["rows"]): PeripheralRow[] {
  const base = buildRows(platform);
  if (!Array.isArray(saved)) return base;
  const byKind = new Map(saved.map((r) => [r.kind, r]));
  return base.map((r) => {
    const s = byKind.get(r.kind);
    return s ? {
      ...r, enabled: !!s.enabled, mio: s.mio ?? "",
      qspiMode: (s.qspiMode as PeripheralRow["qspiMode"]) ?? "Single",
      qspiDataMode: (s.qspiDataMode as PeripheralRow["qspiDataMode"]) ?? "",
      qspiFbclk: !!s.qspiFbclk,
    } : r;
  });
}

export default function VivadoDesignPanel({ onBack }: { onBack?: () => void }) {
  const setProject = useStore((s) => s.setProject);
  const applyParse = useStore((s) => s.applyParse);
  const setStep = useStore((s) => s.setStep);
  const storeProject = useStore((s) => s.project);

  // Son kaydedilen form ayarlari (bir kez okunur; initializer'lar buradan besler).
  const savedFormRef = useRef<SavedForm | null>(null);
  if (savedFormRef.current === null) savedFormRef.current = loadVivadoForm();
  const savedForm = savedFormRef.current;
  const savedPlatform = savedForm.platform === "versal" ? "versal" : "zynq_ultrascale";

  const [vivadoDir, setVivadoDir] = useState(() => localStorage.getItem("spec2code.vivadoDir") ?? "");
  const [platform, setPlatform] = useState<"zynq_ultrascale" | "versal">(savedPlatform);
  const [part, setPart] = useState(() => localStorage.getItem("spec2code.vivadoPart") ?? "");
  const [tempPath, setTempPath] = useState(() => localStorage.getItem("spec2code.vivadoTemp") ?? "");
  const [designName, setDesignName] = useState(() => savedForm.designName ?? "spec2code_hw");
  const [rows, setRows] = useState<PeripheralRow[]>(() => restoreRows(savedPlatform, savedForm.rows));
  const [refClk, setRefClk] = useState(() => savedForm.refClk ?? "33.333");
  const [ddrMode, setDdrMode] = useState<"none" | "model" | "custom">(() => savedForm.ddrMode ?? "none");
  const [ddrValues, setDdrValues] = useState<Record<string, string>>(() => savedForm.ddrValues ?? {});
  // DDR model havuzu: geometri Xilinx kataloğundan, zamanlamaları üretim
  // anında PCW hesaplar (elle CL/tRCD taşınmaz).
  type DdrPart = { id: string; label: string; description: string; speed_bins: string[]; default_speed_bin: string; bus_widths: string[]; chip_gb: number; dram_width: string };
  const [ddrParts, setDdrParts] = useState<DdrPart[]>([]);
  const [ddrModel, setDdrModel] = useState(() => savedForm.ddrModel ?? "");
  const [ddrBusWidth, setDdrBusWidth] = useState(() => savedForm.ddrBusWidth ?? "32 Bit");
  const [makeBit, setMakeBit] = useState(() => savedForm.makeBit ?? false);
  const [addTestIp, setAddTestIp] = useState(() => savedForm.addTestIp ?? false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [events, setEvents] = useState<VivadoEvent[]>([]);
  const [result, setResult] = useState<{ xsa_path?: string; image_path?: string; xsa_bit_path?: string; successful?: boolean; regmap_ip_base?: string } | null>(null);
  const [connectMsg, setConnectMsg] = useState("");
  // Parça kataloğu: kurulu Vivado'nun get_parts çıktısı (platform -> cihaz
  // -> tam parça). El ile parça listesi TAŞINMAZ — tek kaynak kullanıcının
  // kurulumudur; ilk çekim ~1 dk sürer, sonrası önbellekten anındadır.
  const [partsCatalog, setPartsCatalog] = useState<Record<string, Record<string, string[]>> | null>(null);
  const [partsLoading, setPartsLoading] = useState(false);
  const [partsError, setPartsError] = useState("");
  const [manualPart, setManualPart] = useState(false);
  // ZynqMP MIO seçenek tablosu (Vivado kabul-testi taramasından): peripheral
  // -> geçerli MIO konumları. Her satırın MIO'su bu listeden seçilir.
  const [mioOptions, setMioOptions] = useState<Record<string, { options: string[] }>>({});
  const closeRef = useRef<null | (() => void)>(null);
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => () => closeRef.current?.(), []);
  useEffect(() => {
    api.vivadoMioOptions()
      .then((res) => setMioOptions(res.zynq_ultrascale ?? {}))
      .catch(() => setMioOptions({}));
    api.vivadoDdrParts()
      .then((res) => setDdrParts(res.zynq_ultrascale ?? []))
      .catch(() => setDdrParts([]));
  }, []);
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events]);

  // Form ayarlarini her degisiklikte kaydet (dosya yollari kendi anahtarlarinda,
  // gerisi tek snapshot). Bir sonraki acilista aynen geri yuklenir.
  useEffect(() => {
    try {
      localStorage.setItem("spec2code.vivadoDir", vivadoDir);
      localStorage.setItem("spec2code.vivadoPart", part);
      localStorage.setItem("spec2code.vivadoTemp", tempPath);
      const snapshot: SavedForm = {
        platform, designName, refClk, ddrMode, ddrValues, ddrModel, ddrBusWidth, makeBit, addTestIp,
        rows: rows.map((r) => ({ kind: r.kind, enabled: r.enabled, mio: r.mio,
          qspiMode: r.qspiMode, qspiDataMode: r.qspiDataMode, qspiFbclk: r.qspiFbclk })),
      };
      localStorage.setItem(VIVADO_FORM_KEY, JSON.stringify(snapshot));
    } catch { /* localStorage kapali - ayarlar yalnizca bu oturumda kalir */ }
  }, [vivadoDir, part, tempPath, platform, designName, refClk, ddrMode, ddrValues,
      ddrModel, ddrBusWidth, makeBit, addTestIp, rows]);

  function switchPlatform(next: "zynq_ultrascale" | "versal") {
    setPlatform(next);
    setRows(buildRows(next));
    if (next === "versal") setDdrMode("none");
    // Seçili parça yeni platforma ait değilse menü tutarlılığı için sıfırla.
    const nextDevices = partsCatalog?.[next] ?? null;
    if (nextDevices && !(part.split("-", 1)[0] in nextDevices)) setPart("");
  }

  async function fetchParts(options: { refresh?: boolean; cachedOnly?: boolean } = {}) {
    const dir = vivadoDir.trim();
    if (!dir) {
      if (!options.cachedOnly) setPartsError("Önce Vivado dizinini gir.");
      return;
    }
    if (!options.cachedOnly) {
      setPartsLoading(true);
      setPartsError("");
    }
    try {
      const res = await api.vivadoParts({ vivado_path: dir, refresh: options.refresh, cached_only: options.cachedOnly });
      if (res.platforms) {
        setPartsCatalog(res.platforms);
        setManualPart(false);
      }
    } catch (err) {
      if (!options.cachedOnly) setPartsError(err instanceof Error ? err.message : String(err));
    } finally {
      setPartsLoading(false);
    }
  }

  // Önbellekte liste varsa sessizce yükle (Vivado açılmaz).
  useEffect(() => {
    void fetchParts({ cachedOnly: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshResult(jobId: string) {
    try {
      const res = await api.vivadoDesignResult(jobId);
      setResult(res.result);
      if (res.result?.xsa_path) localStorage.setItem("spec2code.lastVivadoXsa", res.result.xsa_path);
      if (res.error) setError(res.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function attach(jobId: string) {
    closeRef.current?.();
    setEvents([]);
    closeRef.current = openVivadoSocket(
      jobId,
      (event) => {
        setEvents((current) => [...current, event as VivadoEvent].slice(-500));
        const ev = event as VivadoEvent;
        if (ev.event === "vivado.error" && ev.message) setError(ev.message);
        if (ev.event === "vivado.xsa_ready" && ev.xsa_path) {
          // Ana Setup sayfası "Vivado'da üretilen XSA'yı kullan" kısayolunu
          // bu anahtardan besler (kullanıcı esnekliği: elle de seçebilir).
          localStorage.setItem("spec2code.lastVivadoXsa", ev.xsa_path);
        }
        if (ev.event === "vivado.end") void refreshResult(jobId);
      },
      () => {
        setRunning(false);
        void refreshResult(jobId);
      },
    );
  }

  // Sekmeden ayrılıp dönünce koşan işe yeniden bağlan (Vitis panel kalıbı).
  useEffect(() => {
    const stored = localStorage.getItem(VIVADO_JOB_KEY);
    if (!stored) return;
    let cancelled = false;
    void (async () => {
      try {
        const res = await api.vivadoDesignResult(stored);
        if (cancelled) return;
        if (res.status === "running" || res.status === "pending") {
          setRunning(true);
          attach(stored);
        } else {
          setResult(res.result);
          if (res.error) setError(res.error);
        }
      } catch {
        localStorage.removeItem(VIVADO_JOB_KEY);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function start() {
    if (running) return;
    setError("");
    setResult(null);
    setConnectMsg("");
    const peripherals = rows.filter((r) => r.enabled).map((r) => ({
      kind: r.kind,
      mio: r.kind === "qspi" ? "" : r.mio.trim(),
      qspi_mode: r.kind === "qspi" ? r.qspiMode : "",
      qspi_data_mode: r.kind === "qspi" ? r.qspiDataMode : "",
      qspi_fbclk: r.kind === "qspi" ? r.qspiFbclk : false,
    }));
    const ddrParams = Object.fromEntries(
      Object.entries(ddrValues).filter(([, value]) => value.trim() !== "").map(([k, v]) => [k, v.trim()]),
    );
    if (platform === "zynq_ultrascale" && ddrMode === "custom" && Object.keys(ddrParams).length === 0) {
      setError(
        "DDR modu 'Gelişmiş' seçili ama hiçbir DDR alanı doldurulmamış. Model havuzundan seç ya da " +
        "datasheet değerlerini gir; ilk bring-up için 'DDR yok — ajan OCM'den koşar' da kullanılabilir.",
      );
      return;
    }
    if (platform === "zynq_ultrascale" && ddrMode === "model" && !ddrModel) {
      setError("DDR modu 'Model havuzu' seçili ama model seçilmedi — listeden kartındaki DDR yongasını seç.");
      return;
    }
    localStorage.setItem("spec2code.vivadoDir", vivadoDir.trim());
    localStorage.setItem("spec2code.vivadoPart", part.trim());
    localStorage.setItem("spec2code.vivadoTemp", tempPath.trim());
    setRunning(true);
    try {
      const res = await api.vivadoDesignStart({
        vivado_path: vivadoDir.trim(),
        platform,
        part: part.trim(),
        temp_path: tempPath.trim(),
        design_name: designName.trim() || "spec2code_hw",
        peripherals,
        ref_clk_mhz: refClk.trim(),
        ddr_mode: platform === "versal" ? "none" : ddrMode,
        ddr_params: ddrMode === "custom" ? ddrParams : {},
        ddr_model: ddrMode === "model" ? ddrModel : "",
        ddr_bus_width: ddrMode === "model" ? ddrBusWidth : "",
        // Hıza dokunulmaz (PCW 1600 varsayılanı) — bkz. backend notu.
        ddr_speed_bin: "",
        add_regmap_test_ip: platform === "zynq_ultrascale" ? addTestIp : false,
        make_bitstream: makeBit,
        timeout_s: makeBit ? 3 * 3600 : 1800,
      });
      localStorage.setItem(VIVADO_JOB_KEY, res.vivado_job_id);
      attach(res.vivado_job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setRunning(false);
    }
  }

  async function connectToSetup(xsaPath: string) {
    setConnectMsg("");
    try {
      const res: XsaParseResult = await api.parseXsaPath(xsaPath);
      setProject({
        platform: res.platform as PlatformId,
        target_core: res.cores[0]?.id ?? storeProject.target_core,
      });
      applyParse(res);
      localStorage.setItem("spec2code.xsaPath", res.xsa_path);
      setConnectMsg(`${res.controllers.length} denetleyici şematiğe aktarıldı.`);
      setStep("schematic");
    } catch (err) {
      setConnectMsg(`Bağlanamadı: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  // MIO gerçeği (Vivado 2023.2 ile doğrulandı): tüm PS çevre birimlerinin
  // varsayılan MIO'su düşük pinlerde kümelenir ve Vivado çakışsa bile
  // otomatik TAŞIMAZ. Yani birden fazla birim boş MIO ile açıksa üretim
  // büyük olasılıkla çakışma hatasıyla düşer — gerçek kartta MIO zaten
  // şemadan gelir. Kullanıcıyı üretimden ÖNCE uyar.
  const enabledRows = rows.filter((r) => r.enabled);
  const blankMioCount = enabledRows.filter((r) => !r.mio.trim()).length;
  const multiBlankMioWarning = enabledRows.length >= 2 && blankMioCount >= 2;

  const xsaReady = result?.xsa_path || events.find((e) => e.event === "vivado.xsa_ready")?.xsa_path;
  const imageReady = result?.image_path || events.find((e) => e.event === "vivado.bit_ready")?.image_path;
  const regmapBase = result?.regmap_ip_base || events.find((e) => e.event === "vivado.regmap_ip")?.regmap_ip_base;
  // Test IP adresi atandiginda Register Map ekrani "Test IP haritasini yukle"
  // ile bu adresi kullanir (adres + register + bitfield otomatik gelir).
  useEffect(() => { if (regmapBase) localStorage.setItem("spec2code.regmap.testIpBase", regmapBase); }, [regmapBase]);
  const lastStage = [...events].reverse().find((e) => e.event === "vivado.stage");
  const tempTooLong = tempPath.trim().length > 60;
  const canStart = Boolean(vivadoDir.trim() && part.trim() && tempPath.trim() && rows.some((r) => r.enabled)) && !running;

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <Card className="p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {onBack ? (
              <Button variant="outline" size="sm" onClick={onBack} title="Ana Setup sayfasına dön — koşan iş kesilmez">
                <ArrowLeft className="h-4 w-4" /> Setup&apos;a dön
              </Button>
            ) : null}
            <CircuitBoard className="h-4 w-4 text-accent" aria-hidden />
            <h3 className="text-sm font-semibold text-text">Vivado ile XSA üret — PS konfigürasyonundan XSA/bit</h3>
          </div>
          <div className="flex items-center gap-1.5">
            {lastStage ? <Badge tone="accent">{lastStage.message ?? lastStage.stage}</Badge> : null}
            {xsaReady ? <Badge tone="ok">XSA hazır</Badge> : null}
            {imageReady ? <Badge tone="ok">{platform === "versal" ? "PDI" : "BIT"} hazır</Badge> : null}
          </div>
        </div>
        <p className="mb-4 text-xs leading-relaxed text-muted">
          Gerçek kartın PS arayüzlerini şemadan seç, MIO&apos;ları gir; arka planda Vivado batch koşar.
          <b> Aşama 1</b>: sentezsiz .xsa (~1-2 dk) — hazır olunca tek tuşla Setup/şematiğe bağlanır.
          <b> Aşama 2</b> (isteğe bağlı): sentez + implementasyon ile {platform === "versal" ? ".pdi" : ".bit"}.
          MIO/parametre doğrulaması Vivado&apos;ya aittir: geçersiz değer 1. aşamada net hatayla döner.
        </p>

        <div className="grid gap-3 lg:grid-cols-2">
          <div>
            <Label>Vivado dizini</Label>
            <Input value={vivadoDir} onChange={(e) => setVivadoDir(e.target.value)} placeholder="C:\\Xilinx_2023_2\\Vivado\\2023.2" />
          </div>
          <div>
            <Label>Temp/Staging dizini (KISA yol)</Label>
            <Input value={tempPath} onChange={(e) => setTempPath(e.target.value)} placeholder="D:\\VivadoTemp" />
            {tempTooLong ? (
              <p className="mt-1 text-[11px] text-warn">Vivado Windows&apos;ta 260 karakter yol sınırı uygular — kısa bir dizin ver (örn. D:\VivadoTemp).</p>
            ) : null}
          </div>
          <div>
            <Label>Platform</Label>
            <Select value={platform} onValueChange={(v) => switchPlatform(v as "zynq_ultrascale" | "versal")}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="zynq_ultrascale">Zynq UltraScale+</SelectItem>
                <SelectItem value="versal">Versal</SelectItem>
              </SelectContent>
            </Select>
            <p className="mt-1 text-[11px] text-faint">Zynq-7000 bu akışta bilinçli olarak kapsam dışı (Faz A).</p>
          </div>
          <div>
            <Label>Hedef parça (part)</Label>
            {partsCatalog && !manualPart ? (
              (() => {
                const deviceMap = partsCatalog[platform] ?? {};
                const deviceNames = Object.keys(deviceMap).sort();
                const selectedDevice = part.split("-", 1)[0];
                const packages = deviceMap[selectedDevice] ?? [];
                return (
                  <>
                    <div className="grid grid-cols-2 gap-2">
                      <Select
                        value={deviceNames.includes(selectedDevice) ? selectedDevice : ""}
                        onValueChange={(d) => setPart(deviceMap[d]?.[0] ?? d)}
                      >
                        <SelectTrigger className="font-mono text-xs"><SelectValue placeholder="cihaz seç" /></SelectTrigger>
                        <SelectContent>
                          {deviceNames.map((name) => (
                            <SelectItem key={name} value={name} className="font-mono text-xs">{name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Select value={packages.includes(part) ? part : ""} onValueChange={setPart}>
                        <SelectTrigger className="font-mono text-xs"><SelectValue placeholder="paket / hız" /></SelectTrigger>
                        <SelectContent>
                          {packages.map((full) => (
                            <SelectItem key={full} value={full} className="font-mono text-xs">
                              {full.slice(selectedDevice.length + 1) || full}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <p className="mt-1 flex items-center gap-2 text-[11px] text-faint">
                      <span className="break-all font-mono">{part || "—"}</span>
                      <button type="button" className="shrink-0 text-accent underline-offset-2 hover:underline" onClick={() => setManualPart(true)}>
                        elle gir
                      </button>
                    </p>
                  </>
                );
              })()
            ) : (
              <>
                <Input value={part} onChange={(e) => setPart(e.target.value)} placeholder={platform === "versal" ? "xcvc1902-vsva2197-2MP-e-S" : "xczu9eg-ffvb1156-2-e"} className="font-mono text-xs" />
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => void fetchParts({})} disabled={partsLoading || !vivadoDir.trim()}>
                    {partsLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ListTree className="h-3.5 w-3.5" />}
                    Parça listesini Vivado&apos;dan getir (~1 dk, bir kez)
                  </Button>
                  {partsCatalog ? (
                    <button type="button" className="text-[11px] text-accent underline-offset-2 hover:underline" onClick={() => setManualPart(false)}>
                      menüden seç
                    </button>
                  ) : null}
                </div>
                {partsError ? <p className="mt-1 text-[11px] text-danger">{partsError}</p> : null}
              </>
            )}
          </div>
          <div>
            <Label>Tasarım adı</Label>
            <Input value={designName} onChange={(e) => setDesignName(e.target.value)} placeholder="spec2code_hw" />
          </div>
          <div>
            <Label>PS referans saati (MHz)</Label>
            <Input value={refClk} onChange={(e) => setRefClk(e.target.value)} placeholder="33.333" className="font-mono text-xs" />
          </div>
        </div>
      </Card>

      <Card className="p-4">
        <h4 className="mb-2 text-sm font-semibold text-text">PS çevre birimleri + MIO</h4>
        <p className="mb-3 text-[11px] text-faint">
          {platform === "zynq_ultrascale"
            ? "MIO konumları açılır menüden seçilir — liste, kurulu Vivado'nun kabul ettiği geçerli konumlardır (kabul-testi taramasıyla üretildi). Gerçek kartta değeri şemadan seç; tek birimde \"otomatik\" bırakılabilir, birden fazla birimde seç (aksi halde varsayılanlar çakışır)."
            : "Gerçek kartta MIO değerleri şemadan okunur (örn. I2C0 → PMC_MIO 46 .. 47). Versal Faz A: UART ve I2C (diğerleri sonraki fazda)."}
        </p>
        {multiBlankMioWarning ? (
          <p className="mb-3 rounded-md border border-warn/30 bg-warn/10 px-2.5 py-1.5 text-[11px] leading-relaxed text-warn">
            {enabledRows.length} çevre birimi seçili ama {blankMioCount} tanesinin MIO&apos;su boş.
            ZynqMP&apos;de tüm birimlerin varsayılan MIO&apos;su düşük pinlerde kümelenir ve Vivado
            çakışanı otomatik taşımaz — bu haliyle üretim büyük olasılıkla &quot;Conflict&quot; hatası
            verir. Her birimin MIO&apos;sunu kartın şemasından gir (tek birim bırakırsan otomatik
            atanabilir).
          </p>
        ) : null}
        <div className="grid gap-2 md:grid-cols-2">
          {rows.map((row, index) => {
            const opts = platform === "zynq_ultrascale" ? mioOptions[row.kind]?.options ?? [] : [];
            const setMio = (value: string) =>
              setRows((current) => current.map((r, i) => (i === index ? { ...r, mio: value } : r)));
            const patchRow = (patch: Partial<PeripheralRow>) =>
              setRows((current) => current.map((r, i) => (i === index ? { ...r, ...patch } : r)));
            if (row.kind === "qspi" && platform === "zynq_ultrascale") {
              // QSPI özel satır: MIO'yu mod belirler; mod/data/FBCLK seçilir.
              return (
                <div key={row.kind} className={cn("flex flex-wrap items-center gap-2 rounded-md border px-2 py-1.5 md:col-span-2", row.enabled ? "border-accent/40 bg-accent/5" : "border-border bg-inset")}>
                  <label className="flex w-40 shrink-0 cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={row.enabled}
                      onChange={(e) => patchRow({ enabled: e.target.checked })}
                      className="h-4 w-4 accent-[var(--accent)]"
                    />
                    <span className="font-mono text-xs text-text">{row.label}</span>
                  </label>
                  <select
                    value={row.qspiMode}
                    onChange={(e) => patchRow({ qspiMode: e.target.value as PeripheralRow["qspiMode"] })}
                    disabled={!row.enabled}
                    className="h-8 rounded-md border border-border bg-inset px-2 font-mono text-xs text-text disabled:opacity-50"
                    title="Single: tek yonga (MIO 0..5). Dual Parallel: 2 yonga, toplam x8 veri (MIO 0..12)."
                  >
                    <option value="Single">Single — MIO 0 .. 5</option>
                    <option value="Dual Parallel">Dual Parallel (2×yonga) — MIO 0 .. 12</option>
                  </select>
                  <select
                    value={row.qspiDataMode}
                    onChange={(e) => patchRow({ qspiDataMode: e.target.value as PeripheralRow["qspiDataMode"] })}
                    disabled={!row.enabled}
                    className="h-8 rounded-md border border-border bg-inset px-2 font-mono text-xs text-text disabled:opacity-50"
                    title="Yonga başına veri hattı (Dual Parallel'de toplam iki katı: 2×4=x8)."
                  >
                    <option value="">veri: varsayılan</option>
                    <option value="x1">x1</option>
                    <option value="x2">x2</option>
                    <option value="x4">x4</option>
                  </select>
                  <label className={cn("flex cursor-pointer items-center gap-1.5 font-mono text-[11px]", row.enabled ? "text-muted" : "text-faint")}
                    title="Geri besleme saati (MIO 6). Kartında bağlı değilse kapalı bırak.">
                    <input
                      type="checkbox"
                      checked={row.qspiFbclk}
                      onChange={(e) => patchRow({ qspiFbclk: e.target.checked })}
                      disabled={!row.enabled}
                      className="h-3.5 w-3.5 accent-[var(--accent)]"
                    />
                    FBCLK (MIO 6)
                  </label>
                </div>
              );
            }
            return (
              <div key={row.kind} className={cn("flex items-center gap-2 rounded-md border px-2 py-1.5", row.enabled ? "border-accent/40 bg-accent/5" : "border-border bg-inset")}>
                <label className="flex w-40 shrink-0 cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={row.enabled}
                    onChange={(e) => setRows((current) => current.map((r, i) => (i === index ? { ...r, enabled: e.target.checked } : r)))}
                    className="h-4 w-4 accent-[var(--accent)]"
                  />
                  <span className="font-mono text-xs text-text">{row.label}</span>
                </label>
                {opts.length > 0 ? (
                  // Vivado-doğrulanmış MIO konumları açılır menüde: ilk seçenek
                  // "otomatik" (boş = Vivado varsayılanı), kalanlar gerçek
                  // geçerli konumlar. Kullanıcı elle de yazabilsin diye tabloda
                  // olmayan bir değer seçilirse (ör. eski kayıt) korunur.
                  <select
                    value={row.mio}
                    onChange={(e) => setMio(e.target.value)}
                    disabled={!row.enabled}
                    className="h-8 w-full min-w-0 rounded-md border border-border bg-inset px-2 font-mono text-xs text-text disabled:opacity-50"
                  >
                    <option value="">otomatik (Vivado varsayılanı)</option>
                    {row.mio && !opts.includes(row.mio) ? <option value={row.mio}>{row.mio} (elle)</option> : null}
                    {opts.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : (
                  <Input
                    value={row.mio}
                    onChange={(e) => setMio(e.target.value)}
                    placeholder={row.mioPlaceholder}
                    disabled={!row.enabled}
                    className="font-mono text-xs"
                  />
                )}
              </div>
            );
          })}
        </div>
      </Card>

      {platform === "zynq_ultrascale" ? (
        <Card className="p-4">
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-sm font-semibold text-text">DDR</h4>
            <Select value={ddrMode} onValueChange={(v) => setDdrMode(v as "none" | "model" | "custom")}>
              <SelectTrigger className="w-80" data-testid="vivado-ddr-mode"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">DDR yok — ajan OCM&apos;den koşar (ilk bring-up önerisi)</SelectItem>
                <SelectItem value="model">Model havuzundan seç (önerilen)</SelectItem>
                <SelectItem value="custom">Gelişmiş — datasheet parametreleri</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {ddrMode === "none" ? (
            <p className="text-[11px] leading-relaxed text-faint">
              DDR denetleyicisi kapalı üretilir; test ajanı OCM&apos;e linklenerek koşabilir. DDR&apos;lı gerçek kart
              için önce bu modla kartı ayağa kaldırıp sonra model havuzuna geçmek yanlış DDR parametresini
              &quot;kart sessiz&quot; yerine görünür bir hataya çevirir.
            </p>
          ) : ddrMode === "model" ? (
            (() => {
              const selected = ddrParts.find((p) => p.id === ddrModel);
              const chipBits = selected ? parseInt(selected.dram_width) || 16 : 16;
              const busBits = parseInt(ddrBusWidth) || 32;
              const chipCount = Math.max(1, Math.round(busBits / chipBits));
              const totalGb = selected ? selected.chip_gb * chipCount : 0;
              return (
                <>
                  <p className="mb-2 text-[11px] leading-relaxed text-faint">
                    Geometri Xilinx&apos;in resmi DDR4 kataloğundan; CL/tRCD gibi zamanlamaları üretim
                    anında Vivado (PCW) hız sınıfına göre kendisi hesaplar — elle değer taşınmaz.
                    Kartındaki yonga listede yoksa söyle, ekleyeyim.
                  </p>
                  <div className="grid gap-2 md:grid-cols-3">
                    <div className="md:col-span-3">
                      <Label>DDR modeli</Label>
                      <select
                        value={ddrModel}
                        onChange={(e) => setDdrModel(e.target.value)}
                        className="h-9 w-full rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
                        data-testid="vivado-ddr-model"
                      >
                        <option value="">model seç...</option>
                        {ddrParts.map((p) => (
                          <option key={p.id} value={p.id}>{p.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label>Veri yolu (yonga sayısı)</Label>
                      <select
                        value={ddrBusWidth}
                        onChange={(e) => setDdrBusWidth(e.target.value)}
                        disabled={!selected}
                        className="h-9 w-full rounded-md border border-border bg-inset px-2 font-mono text-xs text-text disabled:opacity-50"
                      >
                        {(selected?.bus_widths ?? ["32 Bit"]).map((bw) => {
                          const n = Math.max(1, Math.round((parseInt(bw) || 32) / chipBits));
                          return <option key={bw} value={bw}>{bw} — {n} yonga</option>;
                        })}
                      </select>
                    </div>
                    <div>
                      <Label>Hız</Label>
                      <p className="flex h-9 items-center rounded-md border border-border bg-inset px-2 font-mono text-xs text-muted" title="Hıza dokunulmaz: Vivado'nun tutarlı varsayılanı; tüm listelenen parçalar geriye uyumlu. Hız yükseltme, kart doğrulandıktan sonra ayrı fazda.">
                        DDR4-1600 (güvenli varsayılan)
                      </p>
                    </div>
                    {selected ? (
                      <div className="flex items-end">
                        <p className="w-full rounded-md border border-ok/25 bg-ok/10 px-2 py-1.5 font-mono text-[11px] text-ok">
                          {chipCount} × {selected.label.split(" ")[1]} → {totalGb} GB, {ddrBusWidth}
                        </p>
                      </div>
                    ) : null}
                  </div>
                  {selected ? <p className="mt-2 text-[11px] leading-relaxed text-faint">{selected.description}</p> : null}
                </>
              );
            })()
          ) : (
            <>
              <p className="mb-2 text-[11px] text-faint">
                Değerler DDR yongasının datasheet&apos;inden; boş bırakılan alan Vivado varsayılanında kalır.
                Parametre adları resmi zcu102 tasarımından doğrulanmıştır.
              </p>
              <div className="grid gap-2 md:grid-cols-3">
                {DDR_FIELDS.map((fieldDef) => (
                  <div key={fieldDef.key}>
                    <Label title={fieldDef.key}>{fieldDef.label}</Label>
                    <Input
                      value={ddrValues[fieldDef.key] ?? ""}
                      onChange={(e) => setDdrValues((current) => ({ ...current, [fieldDef.key]: e.target.value }))}
                      placeholder={fieldDef.placeholder}
                      className="font-mono text-xs"
                    />
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      ) : (
        <Card className="p-4">
          <h4 className="mb-1 text-sm font-semibold text-text">DDR (Versal)</h4>
          <p className="text-[11px] leading-relaxed text-faint">
            Versal&apos;da DDR, NoC/DDRMC üzerinden kurulur ve Faz A kapsamında değildir — tasarım DDR&apos;sız
            üretilir, test ajanı OCM&apos;den koşar. NoC + DDRMC desteği sonraki fazda.
          </p>
        </Card>
      )}

      <Card className="p-4">
        {platform === "zynq_ultrascale" ? (
          <label className="mb-3 flex cursor-pointer items-start gap-2 border-b border-border pb-3 text-sm text-text">
            <input type="checkbox" checked={addTestIp} onChange={(e) => setAddTestIp(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[var(--accent)]" />
            <span>
              <b>Register Map Test IP ekle</b> (opsiyonel) — AXI4-Lite custom IP; RO sabit (ID/VERSION/STATUS),
              RW (SCRATCH/CONTROL), WO→sayaç (TRIGGER/COUNTER) ve yaz→değişen RO (SCRATCH_MIRROR) register'larıyla
              okuma/yazma yolunu bütün case'lerle doğrular. PS M_AXI_HPM0'a bağlanıp adres atanır; adres+register+bitfield
              bilgisi üretim sonrası <b>Register Map</b> ekranına otomatik gelir.
              <span className="mt-0.5 block text-[11px] text-faint">Şimdilik yalnız ZynqMP. Kart yokken bile XSA/xparameters ve Register Map içe aktarma doğrulanabilir.</span>
            </span>
          </label>
        ) : null}
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-text">
            <input type="checkbox" checked={makeBit} onChange={(e) => setMakeBit(e.target.checked)} className="h-4 w-4 accent-[var(--accent)]" />
            Aşama 2: {platform === "versal" ? ".pdi" : ".bit"} de üret (sentez + implementasyon — tasarıma göre dakikalar/saatler)
          </label>
          <Button onClick={() => void start()} disabled={!canStart} className="ml-auto" data-testid="vivado-start">
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Hammer className="h-4 w-4" />}
            Tasarımı üret
          </Button>
        </div>
        {error ? (
          <p className="mt-2 rounded border border-danger/30 bg-danger/10 px-2 py-1.5 font-mono text-[11px] text-danger">{error}</p>
        ) : null}
      </Card>

      {xsaReady ? (
        <Card className="border-ok/30 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <PackageCheck className="h-5 w-5 shrink-0 text-ok" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-ok">Aşama 1 tamam — sentezsiz XSA hazır</p>
              <p className="break-all font-mono text-[11px] text-muted">{xsaReady}</p>
              {imageReady ? <p className="break-all font-mono text-[11px] text-muted">imaj: {imageReady}</p> : null}
              {result?.xsa_bit_path ? <p className="break-all font-mono text-[11px] text-muted">bit&apos;li XSA: {result.xsa_bit_path}</p> : null}
              {regmapBase ? <p className="font-mono text-[11px] text-accent">Register Map Test IP adresi: {regmapBase} — <b>Register Map → &quot;Test IP haritasını yükle&quot;</b> ile bu adresle otomatik gelir.</p> : null}
            </div>
            <Button onClick={() => void connectToSetup(String(xsaReady))}>
              <Wand2 className="h-4 w-4" /> Setup&apos;a bağla — şemayı kur
            </Button>
          </div>
          {connectMsg ? <p className="mt-2 text-xs text-muted">{connectMsg}</p> : null}
        </Card>
      ) : null}

      <Card className="flex h-72 flex-col p-0">
        <div className="border-b border-border px-4 py-2 text-xs font-semibold text-text">Vivado günlüğü</div>
        <div ref={logRef} className="min-h-0 flex-1 overflow-auto bg-bg px-4 py-2 font-mono text-[11px] leading-relaxed">
          {events.length === 0 ? (
            <p className="mt-6 text-center text-xs text-faint">Henüz iş başlatılmadı.</p>
          ) : (
            events.map((event, index) => (
              <div key={index} className={cn(
                event.event === "vivado.error" ? "text-danger"
                  : event.event === "vivado.stage" ? "text-accent"
                  : event.event?.endsWith("_ready") ? "text-ok"
                  : "text-muted",
              )}>
                {event.message ?? event.line ?? event.event}
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
