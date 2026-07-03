/** Board hedefi yardımcıları: platform/çekirdek → Vitis işlemci adı. */

export function defaultVitisProcessor(platform: string, targetCore: string): string {
  if (platform === "zynq_ultrascale") {
    const a53 = /^a53_(\d)$/.exec(targetCore);
    if (a53) return `psu_cortexa53_${a53[1]}`;
    const r5 = /^r5_(\d)$/.exec(targetCore);
    if (r5) return `psu_cortexr5_${r5[1]}`;
  }
  if (platform === "versal") {
    const a72 = /^a72_(\d)$/.exec(targetCore);
    if (a72) return `psv_cortexa72_${a72[1]}`;
    const r5 = /^r5_(\d)$/.exec(targetCore);
    if (r5) return `psv_cortexr5_${r5[1]}`;
  }
  if (platform === "zynq_7000") {
    const a9 = /^a9_(\d)$/.exec(targetCore);
    if (a9) return `ps7_cortexa9_${a9[1]}`;
  }
  if (platform === "microblaze_7series" && !targetCore.startsWith("microblaze")) {
    return "microblaze_0";
  }
  return targetCore;
}
