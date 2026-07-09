// Shared types mirroring the backend project.spec contract (Brief 6.1).

export type PlatformId = "zynq_7000" | "zynq_ultrascale" | "versal" | "microblaze_7series";
export type Runtime = "bare_metal" | "freertos";
export type DeviceStatus = "builtin" | "needs_source" | "from_datasheet";

export interface Zone {
  id: string;
  label: string;
  description?: string;
}
export interface Core {
  id: string;
  label: string;
}
export interface Controller {
  id: string;
  type: string;
  instance: string;
  base_address: string;
  device_id?: number | string;
  driver?: string;
  source: string;
  zone: string;
}
export interface ViaMux {
  mux_id: string;
  channel: number;
}
export interface DeviceAttach {
  controller_id: string;
  i2c_address?: string | null;
  spi_chip_select?: number | null;
  address_width?: number | null;
  via_mux?: ViaMux | null;
  reset_gpio?: string | number | null;
  irq_line?: string | number | null;
}
export interface Device {
  id: string;
  part: string;
  descriptor_ref?: string | null;
  config?: DeviceConfig;
  attach: DeviceAttach;
  operations_requested?: string[];
  tests_requested?: string[];
}
export interface InitSequenceWrite {
  reg: string;
  value: number;
  note?: string;
}
/** CIT (cihaz ici test) olcum satiri: sematik config.cit.measurements[] (Task 6).
 * `op` bir "birimli okuma" op adiyla eslesir (voltage_read, temperature_read...);
 * eslesmeyen op'lar manifest cit.olcumler'e girmez. Hepsi opsiyonel — bos
 * birakilirsa uretim tarafi varsayilan isim/onem uygular (bkz. codegen.py
 * _testbench_cit_section). `enabled: false` olcum manifest listesinde KALIR
 * (bit sirasi/slot stabil kalsin diye), yalnizca disable edilir. */
export interface DeviceCitMeasurement {
  op: string;
  name?: string;
  min?: number;
  max?: number;
  severity?: "critical" | "warning";
  enabled?: boolean;
}
export interface DeviceConfig {
  init_sequence?: InitSequenceWrite[];
  ticspro_registers?: string[];
  cit?: { measurements: DeviceCitMeasurement[] };
  [key: string]: unknown;
}
export interface Mux {
  id: string;
  part: string;
  controller_id: string;
  i2c_address: string;
  channels: number;
}
export interface ProjectMeta {
  name: string;
  platform: PlatformId;
  target_core: string;
  runtime: Runtime;
  output_mode?: string;
  /** Test bench agent transport: auto = eth varsa lwIP, yoksa PS UART; coresight = JTAG DCC (ZynqMP). */
  testbench_transport?: "auto" | "eth" | "uart" | "coresight";
}
export interface LlmConfig {
  enabled: boolean;
  base_url?: string;
  model?: string;
  api_key?: string;
  timeout_s?: number;
  max_tokens?: number;
  max_response_chars?: number;
  retries?: number;
}

export interface KnowledgeAskRequest {
  part: string;
  question: string;
  context: string;
  llm: LlmConfig;
}

export interface KnowledgeAskResponse {
  part: string;
  model: string;
  answer: string;
  context_chars: number;
  grounded?: boolean;
}

export interface VitisCompileIssue {
  severity: string;
  category: string;
  message: string;
  suggestion: string;
  file?: string;
  line?: number | null;
  symbol?: string;
  raw?: string;
}

export interface VitisWorkspaceRequest {
  vitis_path: string;
  xsa_path: string;
  workspace_path: string;
  temp_path: string;
  processor?: string;
  runtime?: "standalone" | "freertos" | "freertos10_xilinx" | "bare_metal";
  platform_name?: string;
  system_name?: string;
  app_name?: string;
  timeout_s?: number;
  custom_ip_driver_policy?: "auto_none" | "keep";
  /** full = platform+BSP+app sıfırdan; update = mevcut workspace'te yalnızca kaynak + app build. */
  mode?: "full" | "update";
}

export interface CustomPlIpCandidate {
  instance: string;
  vlnv: string;
  ip_name: string;
  reason: string;
}

export interface VitisDoctorCheck {
  id: string;
  label: string;
  status: "ok" | "warn" | "error" | "neutral" | string;
  detail: string;
}

export interface VitisMakeLibsSample {
  driver?: string;
  path_tail?: string;
  custom_match?: boolean;
  sourceless?: boolean;
  patched?: boolean;
}

export interface VitisMakeLibsDiagnostic {
  scope: string;
  is_zip?: boolean;
  hwh_count?: number;
  total: number;
  custom_match: number;
  sourceless: number;
  risky: number;
  samples: VitisMakeLibsSample[];
}

export interface VitisSelfHeal {
  attempted: boolean;
  successful: boolean;
  reason?: string;
  message?: string;
  patched_make_libs?: string[];
  synthesized_make_libs?: string[];
  recovery_script_path?: string;
  stdout_log?: string;
  stderr_log?: string;
}

export interface VitisLogMakeLibsTarget {
  processor: string;
  driver: string;
  path_tail: string;
}

export interface VitisElfArtifactSample {
  name: string;
  path_tail: string;
  application_match: boolean;
  /** ELF dosyasının üretim zamanı (epoch saniye) — eski ELF yükleme
   * tuzağını görünür kılar. */
  modified_at?: number | null;
}

export interface VitisElfArtifacts {
  total: number;
  application: number;
  expected_names: string[];
  samples: VitisElfArtifactSample[];
  application_samples: VitisElfArtifactSample[];
}

export interface VitisDoctor {
  status: "ok" | "warn" | "error" | string;
  privacy?: string;
  error_codes: string[];
  recovered_error_codes?: string[];
  checks: VitisDoctorCheck[];
  hints: string[];
  custom_ip_candidates?: Array<Pick<CustomPlIpCandidate, "instance" | "ip_name" | "reason">>;
  xsa_make_libs?: VitisMakeLibsDiagnostic;
  workspace_make_libs?: VitisMakeLibsDiagnostic | null;
  log_make_libs_targets?: VitisLogMakeLibsTarget[];
  elf_artifacts?: VitisElfArtifacts | null;
}

export interface VitisWorkspaceResult {
  vitis_job_id: string;
  source_job_id: string;
  status: "pending" | "running" | "done" | "error";
  error: string | null;
  result: {
    vitis_job_id: string;
    source_job_id: string;
    project: string;
    xsct_path: string;
    vitis_version: string;
    vitis_version_source: string;
    xsa_path: string;
    source_xsa_path?: string;
    workspace_path: string;
    temp_path?: string;
    staging_path?: string;
    source_path: string;
    platform_name?: string;
    system_name?: string;
    domain_name?: string;
    app_name: string;
    processor: string;
    os: string;
    requires_lwip?: boolean;
    lwip_api_mode?: string | null;
    custom_ip_driver_policy?: "auto_none" | "keep";
    custom_pl_ip_candidates?: CustomPlIpCandidate[];
    xsa_make_libs_preflight?: VitisMakeLibsDiagnostic;
    workspace_make_libs_diagnostic?: VitisMakeLibsDiagnostic;
    vitis_elf_artifacts?: VitisElfArtifacts;
    vitis_doctor?: VitisDoctor;
    self_heal?: VitisSelfHeal;
    custom_ip_make_libs_patched?: string[];
    custom_ip_make_libs_patched_count?: number;
    custom_ip_xsa_make_libs_patched?: string[];
    custom_ip_xsa_make_libs_patched_count?: number;
    custom_ip_bsp_patch_total_count?: number;
    staged_files: string[];
    script_path: string;
    manifest_path: string;
    stdout_log: string;
    stderr_log: string;
    recovery_script_path?: string;
    recovery_stdout_log?: string;
    recovery_stderr_log?: string;
    xsct_initial_exit_code?: number;
    xsct_exit_code?: number;
    xsct_stdout_tail?: string;
    xsct_stderr_tail?: string;
    successful?: boolean;
    compile_issues?: VitisCompileIssue[];
  } | null;
}

export interface TestbenchOperation {
  name: string;
  label: string;
  description?: string;
  risk: "safe" | "risky" | string;
  implemented?: boolean;
  fixed_read_length?: number;
  requires_address?: boolean;
  requires_length?: boolean;
  requires_data?: boolean;
  requires_register?: boolean;
  requires_value?: boolean;
  /** Dönüş tipi (int32/uint16/voltages[8]...) — UI ondalık çözüm için. */
  result_returns?: string;
  /** convert birimi (mV, mA, 0.01 C...); boşsa raw hex gösterim kalır. */
  result_unit?: string;
}

export interface TestbenchRegister {
  name: string;
  offset: number;
  access?: string;
  width?: number;
}

export interface TestbenchManifestDevice {
  id: string;
  part: string;
  transport: string;
  attach?: DeviceAttach;
  registers: TestbenchRegister[];
  operations: TestbenchOperation[];
}

export interface TestbenchManifest {
  schema_version: string;
  project: string;
  agent_version?: string;
  protocol: string;
  line_format: string;
  transport_agent?: "lwip" | "uart" | "coresight" | null;
  uart?: { instance: string; baud: number };
  coresight?: { device: string; driver: string; processor: string; host_bridge: string };
  /** I2C hat taraması: taranabilir denetleyiciler + switch topolojisi. */
  i2c_scan?: {
    op: string;
    mux_op: string;
    range: [number, number];
    probe: string;
    controllers: Array<{ id: string; instance: string }>;
    muxes: Array<{ id: string; part: string; controller_id: string; address: number; channels: number }>;
  };
  devices: TestbenchManifestDevice[];
  /** CIT (cihaz ici test) duz olcum listesi (Task 6); bit i == olcumler[i]
   * (Task 7 codegen + Task 8 decode ayni sirayi kullanir). */
  cit?: TestbenchCitSection;
}

export interface TestbenchCitMeasurement {
  index: number;
  device: string;
  device_index: number;
  part: string;
  op: string;
  name: string;
  cname: string;
  unit: string | null;
  min: number | null;
  max: number | null;
  severity: "critical" | "warning" | string;
  enabled: boolean;
}

export interface TestbenchCitSection {
  olcumler: TestbenchCitMeasurement[];
  bit_sirasi: string[];
}

/** POST /api/testbench/cit/{run,read} yanit satiri: manifest cit.olcumler
 * sirasiyla coz(ul)mus tek CIT olcumu (bkz. backend/cit.py decode_board_cit). */
export interface CitDecodeMeasurement {
  index: number;
  name: string;
  cname: string;
  part: string;
  device: string;
  op: string;
  unit: string | null;
  raw: number;
  value: number;
  ok: boolean;
  durum: number;
  min: number | null;
  max: number | null;
  severity: "critical" | "warning" | string;
  enabled: boolean;
}

export interface CitDecodeResult {
  durum: number;
  sayac: number;
  zaman: number;
  olcumler: CitDecodeMeasurement[];
  desteklenmiyor?: boolean;
}

export interface I2cScanResult {
  controller_id: string;
  taken_at: number;
  duration_ms: number;
  range: [number, number];
  /** Karttaki ajan sürümü (taramadan önce sorgulanır); null = alınamadı. */
  agent_version?: string | null;
  /** Ajan yazma-problu taramayı içeriyor mu (v0.1.105+). Eski ELF'in
   * okuma probu sahada NACK'te de başarı raporladı (hepsi-ACK artefaktı). */
  probe_is_write?: boolean;
  /** 0x08–0x77'nin ~tamamı ACK: fiziksel olarak olağan dışı — eski
   * firmware veya SDA'sı takılı hat şüphesi. */
  suspect_all_ack?: boolean;
  direct_addresses: number[];
  switch_addresses: number[];
  muxes: Array<{
    id: string;
    part: string;
    address: number;
    channels: Array<{ channel: number; addresses: number[] }>;
  }>;
}

export interface TestbenchCommandRequest {
  host: string;
  port: number;
  device: string;
  /** Manifest devices[] sırasındaki indeks; tel üzerine giden asıl kimlik.
   * api.testbenchCommand tarafından `device`'tan MERKEZİ olarak çözülür —
   * çağıranların elle set etmesine gerek yok (bkz. resolveDeviceIndex). */
  device_index?: number;
  operation: string;
  command_id?: number;
  session_id?: string;
  register?: string;
  register_address?: number | null;
  address?: number | null;
  length?: number | null;
  value?: number | null;
  data_hex?: string;
  timeout_s?: number;
}

export interface TestbenchCommandResponse {
  request_line: string;
  response_line: string;
  parsed: Record<string, string>;
}

export interface TestbenchSessionConnectRequest {
  session_id: string;
  transport?: "tcp" | "serial" | "coresight";
  host?: string;
  port?: number;
  serial_port?: string;
  baud?: number;
  /** coresight: xsdb bu Vitis kurulumundan bulunur. */
  vitis_path?: string;
  /** coresight: boş = lokal USB JTAG; SmartLynq için `<ip>[:port]`. */
  hw_server_url?: string;
  /** coresight: DCC'nin bağlandığı çekirdek. */
  processor?: string;
  timeout_s?: number;
}

export interface TestbenchSessionStatus {
  session_id: string;
  host: string;
  port: number;
  connected: boolean;
  connected_at?: number | null;
  last_used_at?: number | null;
  last_error?: string;
  transport?: "tcp" | "serial" | "coresight";
  serial_port?: string;
  baud?: number;
  processor?: string;
  hw_server_url?: string;
  dcc_port?: number;
}

export interface TrafficEntry {
  seq: number;
  at: number;
  dir: "tx" | "rx";
  /** İlk 64B'ın hex dökümü (büyük harf, boşluksuz) — ham S2C-MSG çerçevesi/baytları. */
  hex: string;
  /** İnsan-okunur özet: çerçeve ise "AD (istek) sayac=N govde=NB", değilse ASCII fallback metni. */
  ozet: string;
  /** Yalnız unsolicited TRACE_EVENT/BUS_TRACE_EVENT çerçevelerinde dolu:
   * ajanın çözülmüş "S2C-LOG|D|TRACE|id=..|bus=..|..." satırı (bkz.
   * backend/testbench.py `_traffic_push`). Seri Hat panelinin bit-seviyesi
   * bus-dalga formu bunu konsol satırlarıyla aynı parser'a besler. */
  text?: string;
}

export interface SerialPortInfo {
  device: string;
  description: string;
  hwid: string;
}

export interface SerialConsoleEntry {
  seq: number;
  at: number;
  line: string;
}

export interface RunOnBoardRequest {
  vitis_path: string;
  workspace_path: string;
  platform_name: string;
  app_name: string;
  processor?: string;
  platform?: PlatformId;
  program_fpga?: "auto" | "yes" | "no";
  /** Boş = lokal USB JTAG; SmartLynq/uzak hw_server için `<ip>[:port]`. */
  hw_server_url?: string;
  /** Boş = platformdan otomatik bul; XSA bit içermiyorsa elle `.bit` yolu. */
  bitstream_path?: string;
  timeout_s?: number;
}

export interface RegisterSnapshotEntry {
  name: string;
  offset: number | null;
  ok: boolean;
  value: string;
  error: string;
}

export interface RegisterSnapshot {
  device_id: string;
  taken_at: number;
  duration_ms: number;
  total: number;
  read_ok: number;
  registers: RegisterSnapshotEntry[];
}

export interface BringupStepResult {
  index: number;
  device_id: string;
  part: string;
  operation: string;
  label: string;
  category: string;
  risk: string;
  ok: boolean;
  status: string | null;
  value: string;
  data: string;
  response_message: string;
  error: string;
  duration_ms: number;
}

export interface BringupResult {
  bringup_job_id: string;
  status: string;
  error: string | null;
  result: {
    project: string;
    agent_version: string;
    transport_agent: string | null;
    include_init: boolean;
    started_at: number;
    finished_at: number;
    total: number;
    passed: number;
    failed: number;
    steps: BringupStepResult[];
  } | null;
}

export interface RunOnBoardResult {
  runboard_job_id: string;
  status: string;
  error: string | null;
  result: {
    elf: string;
    platform?: string;
    psu_init: string | null;
    ps7_init?: string | null;
    pdi?: string | null;
    bitstream: string | null;
    markers: string[];
    stdout_log: string;
    stderr_log: string;
  } | null;
}

export interface ProjectSpec {
  schema_version: string;
  project: ProjectMeta;
  coding_standard_ref: string;
  llm: LlmConfig;
  controllers: Controller[];
  devices: Device[];
  muxes: Mux[];
  generation_options: {
    qc_max_rounds: number;
    include_doxygen: boolean;
    line_ending: string;
  };
}

export interface CatalogDevice {
  part: string;
  transport: string;
  status: DeviceStatus;
  descriptor?: string;
  summary: string;
  match_tokens?: string[];
}
export interface DescriptorMeta {
  part: string;
  ref: string;
  transport: string;
  summary: string;
  operations: string[];
  /** "user" = user_descriptors/ dosyası (yerleşiği gölgeler), "builtin" = paket içi. */
  source?: "user" | "builtin";
}

/** user_descriptors/ klasöründeki bir dosyanın listesi; bozuk YAML'lar
 * error alanıyla döner ki kullanıcı düzeltebilsin. */
export interface UserDescriptorEntry {
  file: string;
  part: string | null;
  transport?: string | null;
  summary?: string;
  registers?: number;
  operations?: Array<string | null>;
  error?: string;
}
export interface DescriptorField {
  name: string;
  bits: string;
  description?: string;
  values?: Record<string, string>;
}
export interface DescriptorRegister {
  name: string;
  offset: number;
  width: number;
  access?: string;
  reset?: number;
  fields?: DescriptorField[];
}
export interface DescriptorCommand {
  name: string;
  opcode: number;
  address_bytes?: number;
  description?: string;
}
export interface DescriptorOperation {
  name: string;
  description?: string;
  returns?: string;
  steps?: Array<Record<string, unknown>>;
}
export interface DeviceDescriptor {
  part: string;
  transport: {
    type: string;
    address_width?: number;
    default_address?: number;
    byte_order?: string;
    register_model?: {
      ticspro_words?: boolean;
      frame_bits?: number;
      address_bits?: number;
      address_shift?: number;
      data_bits?: number;
      rw_bit?: number;
      write_value?: number;
      default_order?: "ascending" | "descending" | "exported";
      spi_mode?: number;
      max_sck_hz?: number;
      rewrite_last_address?: number;
      rewrite_last_address_after_ms?: number;
    };
  };
  summary?: string;
  registers?: DescriptorRegister[];
  commands?: DescriptorCommand[];
  operations: DescriptorOperation[];
}
export interface PlatformInfo {
  id: PlatformId;
  display_name: string;
  summary: string;
  cores: Core[];
  zones: Zone[];
}
export interface ParseResult {
  platform: string;
  zones: Zone[];
  cores: Core[];
  controllers: Controller[];
  unmatched: { instance: string; base_address: string; reason: string }[];
}

export interface XsaParseResult extends ParseResult {
  processors: string[];
  xsa_path: string;
}
export interface QcViolation {
  file: string;
  line: number;
  column: number;
  rule: string;
  severity: string;
  message: string;
  source: string;
}
export interface QcReport {
  passed: boolean;
  max_rounds: number;
  rounds_run: number;
  tools: Record<string, unknown>;
  final_violations: QcViolation[];
  warning: string | null;
}
export interface ValidationIssue {
  severity?: "error" | "warning";
  path: string;
  message: string;
}
export interface SpecValidation {
  valid: boolean;
  errors: ValidationIssue[];
  schema_errors?: ValidationIssue[];
  wiring?: {
    valid: boolean;
    errors: ValidationIssue[];
    warnings: ValidationIssue[];
  };
  llm_errors?: ValidationIssue[];
}
export interface GeneratedFile {
  path: string;
  relative_path?: string;
  name: string;
  content: string;
}
export interface JobEvent {
  event: string;
  _seq?: number;
  [k: string]: unknown;
}
export interface DriverMatch {
  stem: string;
  files: string[];
  part: string | null;
  confidence: number;
  signals: string[];
}
