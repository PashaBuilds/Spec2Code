// Shared types mirroring the backend project.spec contract (Brief §6.1).

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
  config?: Record<string, unknown>;
  attach: DeviceAttach;
  operations_requested?: string[];
  tests_requested?: string[];
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
export interface RulesetCheck {
  name: string;
  passed: boolean;
  detail: string;
}
export interface RulesetDiff {
  path: string;
  default: unknown;
  candidate: unknown;
}
export interface RulesetResult {
  ruleset: Record<string, unknown>;
  valid: boolean;
  issues: ValidationIssue[];
  diff: RulesetDiff[];
  checks: RulesetCheck[];
  source_text?: string;
  llm_used?: boolean;
  llm_error?: string;
  needs_human_review?: boolean;
  ok?: boolean;
  ref?: string;
  path?: string;
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
