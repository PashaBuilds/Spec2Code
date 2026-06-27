# Spec2Code Visual Assets

Bu repo, arayuzde dekorasyon yerine okunabilirligi bozmayan teknik gorsel aksanlar
kullanir. Gorseller `frontend/public/visuals/` altindadir ve React tarafinda
metin/govde icerigi her zaman deterministik olarak basilir.

## Current Assets

- `setup-board.webp`: setup ve xparameters panellerinde kullanilan koyu FPGA/PCB gorseli.
- `generate-qc.webp`: generate console ve code viewer empty state gorseli.
- `schematic-traces.webp`: schematic canvas icin dusuk kontrastli PCB trace dokusu.

## Usage Rules

- Gorseller metin icermemelidir; UI metinleri React tarafinda yazilir.
- Schematic canvas icinde gorsel opacity dusuk tutulur, node/edge okunurlugu onceliklidir.
- Cihaz ikonlari icin bitmap yerine mevcut lucide ikon sistemi tercih edilir.
- Yeni asset eklendiyse WebP olarak optimize edilmelidir.

## Generation Prompts

### setup-board.webp

Modern, premium embedded-systems visual for a dark engineering UI. Close-up macro
view of a high-end FPGA development board with subtle copper traces, I2C/SPI/QSPI
signal lines, small components, and faint schematic overlay impression. Polished
3D-photoreal hybrid, wide landscape, strong negative space for UI content,
charcoal/graphite/muted cyan with small amber highlights. No readable text,
logos, watermarks, people, cables, large glowing blobs, UI mockup, or typography.

### generate-qc.webp

Modern visual metaphor for deterministic embedded C code generation from a
hardware schematic. Dark workstation surface with compact PCB edge, subtle
terminal/code-like light reflections, organized signal paths flowing into clean
file blocks without readable characters. Premium 3D render, landscape, clean
negative space, muted steel and deep teal/cyan signal accents with tiny green QC
indicator lights. No readable text, logos, watermark, people, giant glow, or fake
app screenshot.

### schematic-traces.webp

Restrained dark PCB trace texture for a professional schematic editor. Nearly
flat dark surface with faint copper and cyan circuit traces, via dots, and
schematic grid hints. Square, evenly distributed, low contrast, no central focal
object. No readable text, logos, watermark, bright glow, large chips, components
that compete with UI nodes, gradient orb, or fake UI.
