import { useEffect, useState } from "react";
import { api } from "../../api/client";

interface OverrideResponse {
  value: number | null;
}

const SLIDER_STEP = 0.05;

export function CbipPanel() {
  const [value, setValue] = useState<number | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initial load.
  useEffect(() => {
    let cancelled = false;
    api
      .get<OverrideResponse>("/api/cbip/intensity-override")
      .then((res) => {
        if (cancelled) return;
        setValue(res?.value ?? null);
        setLoaded(true);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e));
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const persist = async (next: number | "auto") => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.put<OverrideResponse>(
        "/api/cbip/intensity-override",
        { value: next },
      );
      setValue(res?.value ?? null);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };

  const onAuto = () => persist("auto");
  const onSlide = (e: React.ChangeEvent<HTMLInputElement>) => {
    const next = Math.max(0, Math.min(1, parseFloat(e.target.value)));
    persist(next);
  };

  const isAuto = value === null;
  const sliderValue = value ?? 0.5;
  const intensityLabel = isAuto
    ? "stimmung-coupled"
    : sliderValue < 0.25
    ? "OFF"
    : sliderValue < 0.75
    ? "MID"
    : "FULL";

  if (!loaded) {
    return <div className="text-xs text-zinc-600">loading…</div>;
  }

  return (
    <div className="space-y-2 text-xs">
      <div className="flex items-center justify-between">
        <span className="text-zinc-500">CBIP intensity</span>
        <span className={isAuto ? "text-zinc-400" : "text-zinc-300"}>
          {intensityLabel}
        </span>
      </div>

      <div className="space-y-1">
        <input
          type="range"
          min={0}
          max={1}
          step={SLIDER_STEP}
          value={sliderValue}
          onChange={onSlide}
          disabled={busy}
          className={`w-full ${isAuto ? "opacity-40" : ""}`}
          aria-label="CBIP enhancement intensity override"
        />
        <div className="flex justify-between text-[9px] uppercase tracking-wider text-zinc-600">
          <span>off</span>
          <span>mid</span>
          <span>full</span>
        </div>
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-zinc-800">
        <button
          type="button"
          onClick={onAuto}
          disabled={busy || isAuto}
          className="text-[10px] uppercase tracking-wider text-zinc-500 hover:text-zinc-300 disabled:opacity-40"
        >
          {isAuto ? "✓ auto (stimmung)" : "revert to auto"}
        </button>
        <span className="text-[10px] text-zinc-600">
          {isAuto ? "" : `${Math.round(sliderValue * 100)}%`}
        </span>
      </div>

      {error != null && (
        <div className="text-[10px] text-amber-400 truncate" title={error}>
          {error}
        </div>
      )}
    </div>
  );
}
