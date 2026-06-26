/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        elev: "var(--elev)",
        inset: "var(--inset)",
        border: "var(--border)",
        text: "var(--text)",
        muted: "var(--muted)",
        faint: "var(--faint)",
        accent: "var(--accent)",
        "accent-dim": "var(--accent-dim)",
        ok: "var(--ok)",
        warn: "var(--warn)",
        danger: "var(--danger)",
        "zone-ps": "var(--zone-ps)",
        "zone-pl": "var(--zone-pl)",
        "zone-noc": "var(--zone-noc)",
        "zone-aie": "var(--zone-aie)",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      borderColor: { DEFAULT: "var(--border)" },
      keyframes: {
        "fade-in": { from: { opacity: "0", transform: "translateY(4px)" }, to: { opacity: "1", transform: "none" } },
        "pulse-line": { "0%,100%": { opacity: "0.4" }, "50%": { opacity: "1" } },
      },
      animation: {
        "fade-in": "fade-in 0.2s ease-out",
        "pulse-line": "pulse-line 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
