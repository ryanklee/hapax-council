import { memo, useRef, useEffect } from "react";
import type { FortressEvent } from "../../../api/types";

interface Props {
  events: FortressEvent[];
}

const EVENT_COLORS: Record<string, string> = {
  combat: "var(--color-red-400)",
  death: "var(--color-red-400)",
  siege: "var(--color-red-400)",
  mood: "var(--color-orange-400)",
  tantrum: "var(--color-orange-400)",
  migrant: "var(--color-green-400)",
  birth: "var(--color-green-400)",
  trade: "var(--color-yellow-400)",
  craft: "var(--color-blue-400)",
  construction: "var(--color-blue-400)",
  mandate: "var(--color-purple-400)",
};

function eventColor(type: string): string {
  for (const [key, color] of Object.entries(EVENT_COLORS)) {
    if (type.toLowerCase().includes(key)) return color;
  }
  return "var(--color-fg-muted)";
}

function eventLabel(event: FortressEvent): string {
  // Use description if available, otherwise fall back to type
  return (event.description as string) ?? event.type;
}

export const EventTimeline = memo(function EventTimeline({ events }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to newest events on update
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = scrollRef.current.scrollWidth;
    }
  }, [events]);

  if (events.length === 0) {
    return (
      <div
        className="rounded p-3 text-xs font-mono"
        style={{ background: "var(--color-bg-elevated)" }}
      >
        <div style={{ color: "var(--color-fg-muted)" }}>No recent events</div>
      </div>
    );
  }

  return (
    <div
      className="rounded p-3 text-xs font-mono"
      style={{ background: "var(--color-bg-elevated)" }}
    >
      <div className="font-bold mb-2" style={{ color: "var(--color-fg-secondary)" }}>
        Events
      </div>
      <div
        ref={scrollRef}
        className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin"
        style={{ scrollbarColor: "var(--color-bg-inset) transparent" }}
      >
        {events.map((event, i) => {
          const color = eventColor(event.type);
          return (
            <div
              key={i}
              className="flex-shrink-0 rounded px-2 py-1 max-w-[160px]"
              style={{ background: "var(--color-bg-inset)" }}
            >
              <div className="flex items-center gap-1 mb-0.5">
                <div
                  className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ background: color }}
                />
                <span className="truncate font-bold" style={{ color }}>
                  {event.type}
                </span>
              </div>
              <div
                className="truncate"
                style={{ color: "var(--color-fg-muted)" }}
                title={eventLabel(event)}
              >
                {eventLabel(event)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});
