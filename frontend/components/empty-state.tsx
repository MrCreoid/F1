"use client";

/**
 * The empty state instructs; it never apologises. Three bundled clips are one click
 * each, and the ambiguous one is offered on purpose — a system that admits it does not
 * know is the best answer to "what if it's wrong?".
 */

import { useRef } from "react";
import type { Sample } from "@/lib/api";

export function EmptyState({
  samples,
  busy,
  error,
  onSample,
  onUpload,
}: {
  samples: Sample[];
  busy: string | null;
  error: string | null;
  onSample: (id: string) => void;
  onUpload: (file: File) => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);

  return (
    <div className="flex min-h-0 items-center justify-center bg-mat-chassis p-8">
      <div className="w-full max-w-[760px]">
        <h1
          className="font-display text-t32 uppercase"
          style={{ fontVariationSettings: '"wdth" 108', fontWeight: 800, letterSpacing: "-.01em" }}
        >
          Load footage to begin analysis.
        </h1>
        <p className="mt-3 max-w-[62ch] text-t15 text-[#B9C2CA]">
          Frames in, surface classification out, then a stable wetness index, a trend, and
          the tyre call. Pick a clip or drop your own.
        </p>

        {error && (
          <div
            className="mt-6 border-l-2 px-3 py-2.5 font-mono text-t13"
            style={{ borderColor: "var(--color-trend-worsening)", background: "var(--color-mat-well)", color: "#E8EBED" }}
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="mt-8 grid gap-px" style={{ background: "var(--color-rule)" }}>
          {samples.map((s, i) => (
            <button
              key={s.id}
              type="button"
              disabled={busy !== null}
              onClick={() => onSample(s.id)}
              className="group flex items-center gap-5 px-4 py-4 text-left disabled:cursor-wait"
              style={{
                background: "linear-gradient(180deg, #171C22 0%, #12161B 100%)",
                boxShadow: "inset 0 1px 0 var(--edge-hi)",
              }}
            >
              <span className="tnum text-t11 text-text-muted">{String(i + 1).padStart(2, "0")}</span>
              <span className="min-w-0 flex-1">
                <span
                  className="block font-display text-t20 uppercase transition-colors duration-200 group-hover:text-sodium"
                  style={{ fontVariationSettings: '"wdth" 112', fontWeight: 800, letterSpacing: ".03em" }}
                >
                  {s.name}
                </span>
                <span className="mt-1 block text-t13 text-[#B9C2CA]">{s.story}</span>
              </span>
              <span className="tnum shrink-0 text-t11 text-text-muted">{s.duration_s.toFixed(0)}s</span>
              <span
                className="relative h-px w-6 shrink-0 transition-all duration-200 group-hover:w-9"
                style={{ background: "var(--color-sodium)" }}
              >
                <span
                  className="absolute -top-[3px] right-0 border-y-[3px] border-l-[5px] border-y-transparent"
                  style={{ borderLeftColor: "var(--color-sodium)" }}
                />
              </span>
            </button>
          ))}
          {samples.length === 0 && (
            <p className="tag px-4 py-4" style={{ background: "#12161B" }}>
              Sample list unavailable — backend not reachable.
            </p>
          )}
        </div>

        <div className="mt-6 flex items-center gap-4">
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => fileInput.current?.click()}
            className="px-4 py-2.5 font-display text-t11 uppercase disabled:opacity-50"
            style={{
              fontVariationSettings: '"wdth" 114',
              fontWeight: 800,
              letterSpacing: ".15em",
              background: "linear-gradient(180deg, #1F252D 0%, #141A20 100%)",
              boxShadow: "inset 0 1px 0 rgba(255,255,255,.09), 0 1px 2px rgba(0,0,0,.6), 0 0 0 1px rgba(0,0,0,.5)",
            }}
          >
            Upload a clip
          </button>
          <span className="tag">MP4 · up to 200 MB · analysed at 4 fps</span>
          <input
            ref={fileInput}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onUpload(file);
              e.target.value = "";
            }}
          />
        </div>

        {busy && (
          <p className="mt-6 font-mono text-t13 text-sodium" aria-live="polite">
            Analysing {busy} — extracting frames, classifying, filtering.
          </p>
        )}
      </div>
    </div>
  );
}
