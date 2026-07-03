import { useEffect, useMemo, useRef, useState } from "react";
import { Command as CommandIcon, CornerDownLeft } from "lucide-react";
import { cn } from "@/lib/utils";

export interface PaletteCommand {
  id: string;
  label: string;
  hint?: string;
  keywords?: string;
  run: () => void;
}

/** Ctrl+K / Cmd+K komut paleti: görünümler arası hızlı geçiş ve aksiyonlar. */
export default function CommandPalette({ commands }: { commands: PaletteCommand[] }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((current) => !current);
        setQuery("");
        setCursor(0);
      } else if (event.key === "Escape") {
        setOpen(false);
      }
    }
    function onOpen() {
      setOpen(true);
      setQuery("");
      setCursor(0);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("s2c:palette", onOpen);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("s2c:palette", onOpen);
    };
  }, []);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return commands;
    return commands
      .map((command) => {
        const haystack = `${command.label} ${command.keywords ?? ""}`.toLowerCase();
        const index = haystack.indexOf(needle);
        return { command, index };
      })
      .filter((item) => item.index >= 0)
      .sort((a, b) => a.index - b.index)
      .map((item) => item.command);
  }, [commands, query]);

  useEffect(() => {
    setCursor((current) => Math.min(current, Math.max(0, matches.length - 1)));
  }, [matches]);

  if (!open) return null;

  function execute(command: PaletteCommand) {
    setOpen(false);
    command.run();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-bg/60 pt-[18vh] backdrop-blur-sm"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-lg border border-accent/40 bg-elev shadow-copper-glow"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-border px-3 py-2.5">
          <CommandIcon className="h-4 w-4 shrink-0 text-accent" aria-hidden />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setCursor(0);
            }}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setCursor((current) => Math.min(current + 1, matches.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setCursor((current) => Math.max(current - 1, 0));
              } else if (event.key === "Enter" && matches[cursor]) {
                event.preventDefault();
                execute(matches[cursor]);
              }
            }}
            placeholder="Komut ara... (ekranlar, aksiyonlar)"
            className="w-full bg-transparent font-mono text-sm text-text outline-none placeholder:text-faint"
          />
          <kbd className="rounded border border-border bg-inset px-1.5 py-0.5 font-mono text-[10px] text-faint">esc</kbd>
        </div>
        <div className="max-h-72 overflow-auto py-1">
          {matches.length === 0 ? (
            <p className="px-4 py-6 text-center text-xs text-faint">Eşleşen komut yok.</p>
          ) : (
            matches.map((command, index) => (
              <button
                key={command.id}
                type="button"
                onClick={() => execute(command)}
                onMouseEnter={() => setCursor(index)}
                className={cn(
                  "flex w-full items-center gap-2 px-4 py-2 text-left text-sm",
                  index === cursor ? "bg-accent-dim text-accent" : "text-text",
                )}
              >
                <span className="min-w-0 flex-1 truncate">{command.label}</span>
                {command.hint ? (
                  <span className="shrink-0 font-mono text-[10px] text-faint">{command.hint}</span>
                ) : null}
                {index === cursor ? (
                  <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-accent" aria-hidden />
                ) : null}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
