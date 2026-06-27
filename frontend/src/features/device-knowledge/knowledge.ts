export interface KnowledgeSource {
  label: string;
  url: string;
}

export interface KnowledgeRegister {
  name: string;
  address: string;
  width: string;
  access: string;
  reset?: string;
  purpose: string;
  fields?: string[];
}

export interface KnowledgeRecipe {
  title: string;
  goal: string;
  steps: string[];
}

export interface DeviceKnowledgePack {
  part: string;
  reviewedAt: string;
  scope: string;
  sources: KnowledgeSource[];
  overview: string;
  keyFacts: string[];
  configuration: string[];
  registers: KnowledgeRegister[];
  recipes: KnowledgeRecipe[];
  gotchas: string[];
  codegenNotes: string[];
}

const PACKS: Record<string, DeviceKnowledgePack> = {
  LTC2991: {
    part: "LTC2991",
    reviewedAt: "2026-06-27",
    scope: "Voltage, current, internal temperature, and VCC monitor use cases.",
    sources: [
      {
        label: "Analog Devices LTC2991 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/2991ff.pdf",
      },
    ],
    overview:
      "8 channel I2C monitor. V1/V2, V3/V4, V5/V6, and V7/V8 pairs can be configured for single-ended voltage, differential voltage, current via shunt, or remote temperature style measurements. Internal temperature and VCC can also be enabled.",
    keyFacts: [
      "Default 7-bit address family is 0x48..0x4F, selected by address pins.",
      "Register access uses an 8-bit register pointer and big-endian MSB/LSB reads.",
      "Pair mode is controlled by CONTROL_V1V4 and CONTROL_V5V8; conversion enable bits live in STATUS_HIGH.",
      "Raw readings are intentionally exposed first; board-level scaling belongs to the application profile.",
    ],
    configuration: [
      "Select one mode for each pair: off, single-ended voltage, differential voltage, current, or temperature.",
      "For current mode, keep the shunt resistor value with the device config so generated code can expose the expected conversion helper later.",
      "Enable internal temperature and VCC only when the board needs those reads; otherwise keep init minimal.",
    ],
    registers: [
      {
        name: "STATUS_LOW",
        address: "0x00",
        width: "8",
        access: "RO",
        reset: "0x00",
        purpose: "Busy/status bits for external channel conversions.",
        fields: ["V1/V2 busy bit"],
      },
      {
        name: "STATUS_HIGH",
        address: "0x01",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Enables V1/V2, V3/V4, V5/V6, V7/V8, internal temperature, and VCC measurements.",
        fields: ["T internal/VCC enable", "pair enable bits"],
      },
      {
        name: "CONTROL_V1V4",
        address: "0x06",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Mode bits for V1/V2 and V3/V4 pairs.",
        fields: ["V1/V2 differential", "V1/V2 temperature", "V3/V4 differential", "V3/V4 temperature"],
      },
      {
        name: "CONTROL_V5V8",
        address: "0x07",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Mode bits for V5/V6 and V7/V8 pairs.",
        fields: ["V5/V6 differential", "V5/V6 temperature", "V7/V8 differential", "V7/V8 temperature"],
      },
      {
        name: "V1_MSB..V8_LSB",
        address: "0x0A..0x19",
        width: "16 each",
        access: "RO",
        purpose: "Raw measurement result registers for external inputs.",
      },
      {
        name: "T_INTERNAL",
        address: "0x1A..0x1B",
        width: "16",
        access: "RO",
        purpose: "Raw internal temperature result.",
      },
    ],
    recipes: [
      {
        title: "Differential voltage on V1/V2",
        goal: "Measure the voltage difference between V1 and V2.",
        steps: [
          "Set V1/V2 mode to differential voltage in the device configuration panel.",
          "Generated init writes CONTROL_V1V4 and enables V1/V2 conversion through STATUS_HIGH.",
          "Read V1_MSB/V1_LSB after the busy bit clears; keep board scaling outside the raw driver.",
        ],
      },
      {
        title: "Current measurement",
        goal: "Use a channel pair with a shunt resistor.",
        steps: [
          "Select current mode for the pair and enter the shunt value in milliohm.",
          "Use the generated raw read as the stable interface; current conversion can use raw code plus shunt value.",
          "Document the shunt tolerance in application code if precision matters.",
        ],
      },
      {
        title: "Internal temperature sanity read",
        goal: "Verify the device is responding without relying on board analog inputs.",
        steps: [
          "Enable internal temperature read.",
          "Poll the internal temperature busy bit.",
          "Read T_INTERNAL_MSB/T_INTERNAL_LSB and log the raw code.",
        ],
      },
    ],
    gotchas: [
      "Do not read conversion data blindly immediately after init; poll the related busy bit or add a conversion delay.",
      "Differential/current/temperature modes are pair-level decisions; changing one input can affect its paired input.",
      "Address conflicts are common when several LTC2991 devices use the same strap pins; route through a mux or change address pins.",
    ],
    codegenNotes: [
      "Spec2Code currently emits an init sequence from device.config for STATUS_HIGH, CONTROL_V1V4, and CONTROL_V5V8.",
      "Generated APIs expose raw reads first; calibrated engineering-unit helpers should be added with explicit board scaling.",
    ],
  },

  TCA9548A: {
    part: "TCA9548A",
    reviewedAt: "2026-06-27",
    scope: "Single-upstream, 8 downstream I2C channel switching.",
    sources: [
      {
        label: "Texas Instruments TCA9548A datasheet",
        url: "https://www.ti.com/lit/ds/symlink/tca9548a.pdf",
      },
    ],
    overview:
      "8 channel I2C switch. The device has no normal register pointer; channel selection is done by writing one control byte where each bit enables one downstream channel.",
    keyFacts: [
      "Default address family is 0x70..0x77, selected by A0/A1/A2.",
      "Writing 0x00 disables all downstream channels.",
      "Multiple channels can be enabled by setting multiple bits, but Spec2Code defaults to exactly one active channel for predictable routing.",
      "The mux is useful for duplicate downstream I2C addresses and for segmenting bus capacitance.",
    ],
    configuration: [
      "Set mux address, then attach downstream devices to a channel number 0..7.",
      "Keep only one channel active unless the board intentionally needs bus fan-out.",
    ],
    registers: [
      {
        name: "CONTROL",
        address: "direct byte",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Pseudo register in Spec2Code; actual device write is a single control byte.",
        fields: ["CH0_EN bit 0", "CH1_EN bit 1", "CH2_EN bit 2", "CH3_EN bit 3", "CH4..CH7 bits 4..7"],
      },
    ],
    recipes: [
      {
        title: "Select one channel",
        goal: "Talk to a single downstream device.",
        steps: [
          "Write 1 << channel to the control byte.",
          "Perform the downstream device transaction on the same upstream I2C controller.",
          "Optionally write 0x00 after the transaction if isolation is required.",
        ],
      },
      {
        title: "Resolve duplicate I2C addresses",
        goal: "Use multiple identical parts with the same address.",
        steps: [
          "Place each duplicate part on a different mux channel.",
          "Keep each device address unchanged.",
          "Select the channel before every device access.",
        ],
      },
    ],
    gotchas: [
      "The channel control byte is not preceded by a register address.",
      "If multiple channels are enabled, downstream devices with the same address will conflict.",
      "Reset leaves all channels disabled, so init or first access must select a channel.",
    ],
    codegenNotes: [
      "Spec2Code generates a camelCase channel select helper and inserts mux selection before downstream device access.",
    ],
  },

  MT25Q128: {
    part: "MT25Q128",
    reviewedAt: "2026-06-27",
    scope: "Safe single-SPI NOR flash read, program, erase, and JEDEC ID flows.",
    sources: [
      {
        label: "Micron MT25Q serial NOR product page",
        url: "https://www.micron.com/products/storage/nor-flash/serial-nor",
      },
    ],
    overview:
      "128 Mbit SPI NOR flash, commonly used as a 16 MB nonvolatile memory. The current Spec2Code profile uses 3-byte addressing and conservative single-SPI commands.",
    keyFacts: [
      "3-byte address width is enough for the full 128 Mbit address range.",
      "Read/program/erase operations must respect write-enable and busy polling.",
      "The part family supports faster dual/quad style read modes, but the current generated driver intentionally stays on the safe base command set.",
      "Page program size is typically 256 bytes; writes crossing page boundaries must be split by application logic.",
    ],
    configuration: [
      "Use chip-select to bind the part to the SPI/QSPI controller instance.",
      "Keep address width at 24 bits for this descriptor.",
      "Add a board reset GPIO only if the flash reset pin is wired to the processor.",
    ],
    registers: [
      {
        name: "READ_ID",
        address: "0x9F",
        width: "opcode",
        access: "RO",
        purpose: "Read JEDEC manufacturer/device identification.",
      },
      {
        name: "READ_STATUS",
        address: "0x05",
        width: "opcode",
        access: "RO",
        purpose: "Read status register, especially WIP/busy state.",
      },
      {
        name: "WRITE_ENABLE",
        address: "0x06",
        width: "opcode",
        access: "WO",
        purpose: "Latch write enable before program/erase operations.",
      },
      {
        name: "READ_DATA",
        address: "0x03",
        width: "opcode + 24-bit address",
        access: "RO",
        purpose: "Conservative array read command.",
      },
      {
        name: "PAGE_PROGRAM",
        address: "0x02",
        width: "opcode + 24-bit address",
        access: "WO",
        purpose: "Program up to one page after write enable.",
      },
      {
        name: "SUBSECTOR/SECTOR_ERASE",
        address: "0x20 / 0xD8",
        width: "opcode + 24-bit address",
        access: "WO",
        purpose: "Erase 4 KB subsector or 64 KB sector.",
      },
    ],
    recipes: [
      {
        title: "JEDEC ID read",
        goal: "Verify wiring and chip-select.",
        steps: ["Assert chip-select.", "Send 0x9F.", "Read three ID bytes and reject all-0x00/all-0xFF."],
      },
      {
        title: "Page program",
        goal: "Program bytes into a page.",
        steps: [
          "Send WRITE_ENABLE.",
          "Send PAGE_PROGRAM with a 24-bit address.",
          "Write no more than the page boundary allows.",
          "Poll READ_STATUS until WIP clears.",
        ],
      },
    ],
    gotchas: [
      "Erase before programming if changing bits from 0 back to 1.",
      "Program and erase timings are long relative to normal SPI reads; always poll WIP.",
      "Do not use quad read/program unless board pins, controller mode, and volatile/nonvolatile config bits are intentionally configured.",
    ],
    codegenNotes: [
      "Spec2Code currently generates the safe 3-byte command set for read, program, sector erase, and ID read.",
    ],
  },

  MT25QU02G: {
    part: "MT25QU02G",
    reviewedAt: "2026-06-27",
    scope: "2 Gbit SPI NOR with 4-byte address command flow.",
    sources: [
      {
        label: "Micron MT25Q serial NOR product page",
        url: "https://www.micron.com/products/storage/nor-flash/serial-nor",
      },
    ],
    overview:
      "2 Gbit SPI NOR flash. The full address range requires 32-bit addressing; Spec2Code uses 4-byte command opcodes and emits an enter-4-byte-mode init command.",
    keyFacts: [
      "4-byte addressing is required for the full 256 MB space.",
      "Generated profile uses 0xB7 enter-4-byte mode plus 4-byte read/program/erase opcodes.",
      "The part family can support dual/quad/octal style transfer modes depending on exact variant and controller wiring; this profile stays on deterministic 4-byte SPI commands.",
      "Large flash parts may have die/bank boundary considerations in application-level storage layout.",
    ],
    configuration: [
      "Bind chip-select to the SPI/QSPI controller.",
      "Keep address width at 32 bits.",
      "Use explicit mode fields later if the board intentionally enables quad/dual transfer modes.",
    ],
    registers: [
      {
        name: "READ_ID",
        address: "0x9F",
        width: "opcode",
        access: "RO",
        purpose: "Read JEDEC ID and confirm the device is reachable.",
      },
      {
        name: "WRITE_ENABLE",
        address: "0x06",
        width: "opcode",
        access: "WO",
        purpose: "Required before mode enter, program, and erase flows.",
      },
      {
        name: "ENTER_4BYTE",
        address: "0xB7",
        width: "opcode",
        access: "WO",
        purpose: "Enter 4-byte address mode for the high address range.",
      },
      {
        name: "READ_DATA_4B",
        address: "0x13",
        width: "opcode + 32-bit address",
        access: "RO",
        purpose: "Read array data with a 4-byte address.",
      },
      {
        name: "PAGE_PROGRAM_4B",
        address: "0x12",
        width: "opcode + 32-bit address",
        access: "WO",
        purpose: "Program a page using a 4-byte address.",
      },
      {
        name: "ERASE_4B",
        address: "0x21 / 0xDC",
        width: "opcode + 32-bit address",
        access: "WO",
        purpose: "Erase 4 KB subsector or 64 KB sector with a 4-byte address.",
      },
    ],
    recipes: [
      {
        title: "Safe init",
        goal: "Prepare full-range access.",
        steps: [
          "Send WRITE_ENABLE.",
          "Send ENTER_4BYTE.",
          "Read JEDEC ID as a wiring sanity check.",
        ],
      },
      {
        title: "Full-range read",
        goal: "Read beyond the 16 MB boundary correctly.",
        steps: [
          "Use READ_DATA_4B (0x13).",
          "Transmit a 32-bit address.",
          "Keep controller transfer mode aligned with the generated command profile.",
        ],
      },
    ],
    gotchas: [
      "A 3-byte command can silently address the wrong region on a 2 Gbit flash.",
      "Always poll status after program/erase.",
      "Dual/quad modes require board-level pin and controller configuration; do not infer them from the part number alone.",
    ],
    codegenNotes: [
      "Spec2Code currently emits 4-byte-safe commands for init, read, program, and erase.",
      "A future flash configuration panel can switch protocol width only after controller and board pins are explicit.",
    ],
  },

  AD7414: {
    part: "AD7414",
    reviewedAt: "2026-06-27",
    scope: "Temperature read and alert threshold configuration.",
    sources: [
      {
        label: "Analog Devices AD7414/AD7415 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/ad7414_7415.pdf",
      },
    ],
    overview:
      "I2C temperature sensor with a 10-bit two's-complement temperature result and programmable high/low alert thresholds. It powers up in continuous conversion for the common read-only case.",
    keyFacts: [
      "Default address family starts at 0x48 and depends on address-select pins.",
      "Temperature result is read as two bytes; useful temperature bits are in the upper 10 bits.",
      "Configuration register controls power-down, one-shot, alert behavior, polarity, and filtering.",
      "Threshold registers are 8-bit style trip points for alert use cases.",
    ],
    configuration: [
      "For simple board monitoring, no mandatory device register write is needed after I2C init.",
      "Use one-shot or power-down only when the application manages conversion timing explicitly.",
      "Set alert polarity and thresholds only if the ALERT pin is wired and consumed.",
    ],
    registers: [
      {
        name: "TEMPERATURE",
        address: "0x00",
        width: "16",
        access: "RO",
        reset: "0x0000",
        purpose: "Raw temperature transfer image.",
        fields: ["TEMP_CODE bits 15:6"],
      },
      {
        name: "CONFIGURATION",
        address: "0x01",
        width: "8",
        access: "RW",
        reset: "0x40",
        purpose: "Power, alert, polarity, reset, and one-shot controls.",
        fields: ["POWER_DOWN", "FILTER_BYPASS", "ALERT_ENABLE", "ALERT_POLARITY", "ALERT_RESET", "ONE_SHOT"],
      },
      {
        name: "THIGH",
        address: "0x02",
        width: "8",
        access: "RW",
        reset: "0x50",
        purpose: "High temperature alert threshold.",
      },
      {
        name: "TLOW",
        address: "0x03",
        width: "8",
        access: "RW",
        reset: "0x4B",
        purpose: "Low temperature alert threshold.",
      },
    ],
    recipes: [
      {
        title: "Temperature read",
        goal: "Get the current raw temperature.",
        steps: [
          "Write register pointer 0x00.",
          "Read two bytes.",
          "Right-shift the transfer image to use the 10-bit signed code.",
        ],
      },
      {
        title: "Alert threshold setup",
        goal: "Use ALERT as a hardware trip signal.",
        steps: [
          "Write THIGH and TLOW.",
          "Configure alert enable and polarity.",
          "Handle alert clear/reset behavior in the application.",
        ],
      },
    ],
    gotchas: [
      "The raw temperature code is signed; do not treat negative temperatures as unsigned.",
      "One-shot mode requires explicit timing between conversion start and read.",
      "Only enable alert behavior if the pin is actually wired; otherwise keep config minimal.",
    ],
    codegenNotes: [
      "Spec2Code emits simple init, temperature_read, and config_read operations for this part.",
    ],
  },

  DS1682: {
    part: "DS1682",
    reviewedAt: "2026-06-27",
    scope: "Elapsed-time counter, alarm value, and event counter reads.",
    sources: [
      {
        label: "Analog Devices / Maxim DS1682 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/ds1682.pdf",
      },
    ],
    overview:
      "Total elapsed-time recorder with an I2C interface, alarm storage, event counter, and user EEPROM bytes. It is useful when the board needs persistent operating-time accounting.",
    keyFacts: [
      "Default I2C address used by the descriptor is 0x6B.",
      "Elapsed time counter is read as a 32-bit little-endian value in quarter-second ticks.",
      "Event counter is 17 bits: one MSB bit in CONFIGURATION plus EVENT_HIGH/EVENT_LOW.",
      "Some write-disable and memory-disable operations are one-way or persistent; treat them as production-only actions.",
    ],
    configuration: [
      "For read-only monitoring, no mandatory startup command is required.",
      "Configure alarm polarity/output only if the alarm pin is part of the board design.",
      "Keep destructive commands out of normal self-tests.",
    ],
    registers: [
      {
        name: "CONFIGURATION",
        address: "0x00",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Alarm flag, write-disable flags, alarm output selection, reset enable, event MSB.",
      },
      {
        name: "ALARM",
        address: "0x01..0x04",
        width: "32",
        access: "RW",
        reset: "0x00000000",
        purpose: "Alarm trip point in quarter-second ticks.",
      },
      {
        name: "ETC",
        address: "0x05..0x08",
        width: "32",
        access: "RO",
        reset: "0x00000000",
        purpose: "Elapsed-time counter in quarter-second ticks.",
      },
      {
        name: "EVENT",
        address: "0x09..0x0A + CFG[0]",
        width: "17",
        access: "RO",
        reset: "0x00000",
        purpose: "Event count.",
      },
      {
        name: "USER EEPROM",
        address: "0x0B..0x14",
        width: "10 bytes",
        access: "RW",
        purpose: "Small nonvolatile user field.",
      },
      {
        name: "CONTROL COMMANDS",
        address: "0x1D..0x1F",
        width: "8 each",
        access: "WO",
        purpose: "Reset, write disable, and memory disable commands.",
      },
    ],
    recipes: [
      {
        title: "Elapsed-time read",
        goal: "Read persistent operating time.",
        steps: [
          "Read ETC_LOW through ETC_HIGH.",
          "Combine bytes as little-endian.",
          "Convert quarter-second ticks to seconds if the application needs engineering units.",
        ],
      },
      {
        title: "Event counter read",
        goal: "Read the full 17-bit event count.",
        steps: [
          "Read CONFIGURATION bit 0 for the event MSB.",
          "Read EVENT_LOW and EVENT_HIGH.",
          "Combine as bit16:CONFIGURATION[0], bits15..8:EVENT_HIGH, bits7..0:EVENT_LOW.",
        ],
      },
    ],
    gotchas: [
      "Do not place reset/write-disable commands in smoke tests.",
      "EEPROM-backed writes can have timing and endurance implications.",
      "Read multi-byte counters consistently; if the application needs atomicity, add retry logic around rollover windows.",
    ],
    codegenNotes: [
      "Spec2Code emits read-oriented operations for config, elapsed time, alarm, and event count.",
    ],
  },

  LTC2945: {
    part: "LTC2945",
    reviewedAt: "2026-06-27",
    scope: "Raw power, sense/current, VIN, ADIN, status, and fault monitor reads.",
    sources: [
      {
        label: "Analog Devices LTC2945 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/ltc2945.pdf",
      },
    ],
    overview:
      "Wide-range I2C power monitor. It measures shunt sense voltage, VIN, auxiliary ADIN, and provides a 24-bit power calculation register.",
    keyFacts: [
      "Descriptor default address is 0x67, matching the common 7-bit form of the CEh write-address option.",
      "CONTROL reset/profile value 0x05 is used for continuous SENSE/VIN power monitoring.",
      "Power is 24-bit raw; sense, VIN, and ADIN reads are 12-bit raw images inside two-byte transfers.",
      "Engineering-unit conversion depends on Rsense and board scaling.",
    ],
    configuration: [
      "Set Rsense and board scaling in the application layer before converting raw codes.",
      "Use snapshot mode only if simultaneous channel capture is required.",
      "Configure alerts/fault limits only when the alert line is wired and tested.",
    ],
    registers: [
      {
        name: "CONTROL",
        address: "0x00",
        width: "8",
        access: "RW",
        reset: "0x05",
        purpose: "ADC mode, snapshot, VIN monitor, shutdown, and multiplier selection.",
        fields: ["SNAPSHOT_ENABLE", "ADC_BUSY", "VIN_MONITOR", "SHUTDOWN", "MULTIPLIER_SELECT"],
      },
      {
        name: "ALERT/STATUS/FAULT",
        address: "0x01..0x03",
        width: "8 each",
        access: "RW/RO",
        purpose: "Alert enable/status and fault reporting.",
      },
      {
        name: "FAULT_CLEAR",
        address: "0x04",
        width: "8",
        access: "RW",
        purpose: "Fault clear path.",
      },
      {
        name: "POWER",
        address: "0x05..0x07",
        width: "24",
        access: "RO",
        purpose: "Raw calculated power register.",
      },
      {
        name: "SENSE",
        address: "0x14..0x15",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit shunt/sense ADC image.",
      },
      {
        name: "VIN",
        address: "0x1E..0x1F",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit VIN ADC image.",
      },
      {
        name: "ADIN",
        address: "0x28..0x29",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit auxiliary ADC image.",
      },
    ],
    recipes: [
      {
        title: "Power monitor init",
        goal: "Start continuous raw monitoring.",
        steps: [
          "Write CONTROL = 0x05.",
          "Read STATUS to verify the device is reachable.",
          "Read POWER, SENSE, VIN, and ADIN raw registers as needed.",
        ],
      },
      {
        title: "Current from sense",
        goal: "Convert raw sense code into board current later.",
        steps: [
          "Read SENSE_MSB/SENSE_LSB.",
          "Extract the raw 12-bit code according to the datasheet transfer format.",
          "Apply Rsense and board calibration outside the low-level driver.",
        ],
      },
    ],
    gotchas: [
      "Raw code to volt/amp/watt conversion is board-specific; never bake an unknown Rsense into the generic driver.",
      "Check ADC_BUSY or use a known conversion cadence if snapshot timing matters.",
      "Fault bits can stay latched until cleared through the documented clear path.",
    ],
    codegenNotes: [
      "Spec2Code emits raw read APIs for status, power, sense, voltage, and ADIN.",
    ],
  },
};

export function getDeviceKnowledge(part: string): DeviceKnowledgePack | undefined {
  return PACKS[part.toUpperCase()];
}

export function hasDeviceKnowledge(part: string): boolean {
  return Boolean(getDeviceKnowledge(part));
}
