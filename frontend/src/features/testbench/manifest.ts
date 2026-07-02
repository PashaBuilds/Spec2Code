import type { GeneratedFile, TestbenchManifest } from "@/lib/types";

export function generatedPath(file: GeneratedFile): string {
  if (file.relative_path) return file.relative_path;
  const normalized = file.path.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  if (parts[0] === "outputs" && parts.length > 2) return parts.slice(2).join("/");
  return parts[parts.length - 1] ?? file.name;
}

export function findManifest(files: GeneratedFile[]): TestbenchManifest | null {
  const file = files.find((item) => generatedPath(item) === "tests/spec2code_testbench_manifest.json");
  if (!file?.content) return null;
  try {
    return JSON.parse(file.content) as TestbenchManifest;
  } catch {
    return null;
  }
}

export function manifestStorageKey(project: string): string {
  return `spec2code.testbench.manifest.${project || "default"}`;
}

export function loadCachedManifest(project: string): TestbenchManifest | null {
  try {
    const raw = localStorage.getItem(manifestStorageKey(project));
    return raw ? (JSON.parse(raw) as TestbenchManifest) : null;
  } catch {
    return null;
  }
}

export function saveCachedManifest(project: string, manifest: TestbenchManifest): void {
  try {
    localStorage.setItem(manifestStorageKey(project), JSON.stringify(manifest));
  } catch {
    // Cache is only a convenience fallback; the active generate result remains canonical.
  }
}
