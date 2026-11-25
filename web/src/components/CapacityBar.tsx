import type { CSSProperties } from "react";

interface CapacityBarProps {
  id: string;
  label: string;
  percentage: number;
  variant: "organic" | "inorganic";
  fullThresholdPct?: number;
}

export function CapacityBar({
  id,
  label,
  percentage,
  variant,
  fullThresholdPct = 87.5,
}: CapacityBarProps) {
  const clamped = Math.max(0, Math.min(100, Number(percentage) || 0));
  const isFull = clamped >= fullThresholdPct;
  const isNearFull = !isFull && clamped > 80;

  let fillColor = variant === "organic" ? "#4A6B4D" : "#4C6473";
  let statusText = "Aman";
  let statusTextClass = "text-[#4A544C]";

  if (isFull) {
    fillColor = "#A94438";
    statusText = "Penuh";
    statusTextClass = "font-semibold text-[#8A3228]";
  } else if (isNearFull) {
    fillColor = "#9A6324";
    statusText = "Hampir penuh";
    statusTextClass = "font-medium text-[#7D4E18]";
  }

  const progressStyle = {
    "--progress-bar-fill": fillColor,
    "--progress-bar-track": "#E6E0D4",
  } as CSSProperties;

  return (
    <div className="rounded-lg border border-[#DED8CC] bg-white p-4">
      <div className="flex items-baseline justify-between gap-2">
        <label
          htmlFor={id}
          className="text-sm font-medium text-[#1E2620]"
        >
          {label}
        </label>
        <div className="flex items-baseline gap-2">
          <span className={`text-xs ${statusTextClass}`}>{statusText}</span>
          <span className="text-base font-semibold tabular-nums text-[#1E2620]">
            {clamped.toFixed(0)}%
          </span>
        </div>
      </div>
      <progress
        id={id}
        max={100}
        value={clamped}
        style={progressStyle}
        className="capacity-progress mt-2.5"
      />
    </div>
  );
}
