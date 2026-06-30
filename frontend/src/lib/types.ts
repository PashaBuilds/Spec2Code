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
export interface DeviceConfig {
  init_sequence?: InitSequenceWrite[];
  ticspro_registers?: string[];
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
  processor?: string;
  runtime?: "standalone" | "freertos" | "freertos10_xilinx" | "bare_metal";
  app_name?: string;
  timeout_s?: number;
  custom_ip_driver_policy?: "auto_none" | "keep";
}

export interface CustomPlIpCandidate {
  instance: string;
  vlnv: string;
  ip_name: string;
  reason: string;
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
    workspace_path: string;
    source_path: string;
    app_name: string;
    processor: string;
    os: string;
    requires_lwip?: boolean;
    lwip_api_mode?: string | null;
    custom_ip_driver_policy?: "auto_none" | "keep";
    custom_pl_ip_candidates?: CustomPlIpCandidate[];
    staged_files: string[];
    script_path: string;
    manifest_path: string;
    stdout_log: string;
    stderr_log: string;
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
  devices: TestbenchManifestDevice[];
}

export interface TestbenchCommandRequest {
  host: string;
  port: number;
  device: string;
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
  host: string;
  port: number;
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
