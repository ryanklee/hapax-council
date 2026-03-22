import { useNudges } from "../../../api/hooks";

/** Faint nudge pills for the ground surface — atmospheric, not actionable. */
export function GroundNudgePills() {
  const { data: nudges } = useNudges();
  const pills = (nudges ?? []).slice(0, 2);
  if (!pills.length) return null;

  return (
    <div className="flex gap-1.5">
      {pills.map((n: { source_id?: string; title?: string }, i: number) => (
        <div
          key={n.source_id ?? i}
          className="text-[8px] px-1.5 py-0.5 rounded-full bg-zinc-800/30 text-white/8 truncate max-w-[160px]"
        >
          {n.title ?? "nudge"}
        </div>
      ))}
    </div>
  );
}
