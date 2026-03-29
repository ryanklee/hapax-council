import type { NoteContext } from "./types";
import { NoteKind } from "./types";

export function resolveNoteContext(
  path: string,
  frontmatter: Record<string, unknown> | null,
  metadataTags: string[],
): NoteContext {
  const fm = frontmatter ?? {};
  const id = typeof fm["id"] === "string" ? fm["id"] : undefined;
  const model = typeof fm["model"] === "string" ? fm["model"] : undefined;

  // Collect tags from frontmatter + metadata cache
  const fmTags = normalizeTags(fm["tags"]);
  const allTags = Array.from(new Set([...fmTags, ...metadataTags]));

  // 1. Measure: path contains sprint/measures/ + id matches d+.d+
  if (path.includes("sprint/measures/") && id && /^\d+\.\d+$/.test(id)) {
    return { kind: NoteKind.Measure, id, model, tags: allTags };
  }

  // 2. Gate: path contains sprint/gates/ + id matches G\d+
  if (path.includes("sprint/gates/") && id && /^G\d+$/.test(id)) {
    return { kind: NoteKind.Gate, id, model, tags: allTags };
  }

  // 3. SprintSummary: path contains sprint/sprints/
  if (path.includes("sprint/sprints/")) {
    return { kind: NoteKind.SprintSummary, id, model, tags: allTags };
  }

  // 4. PosteriorTracker: path ends with _posterior-tracker.md
  if (path.endsWith("_posterior-tracker.md")) {
    return { kind: NoteKind.PosteriorTracker, id, model, tags: allTags };
  }

  // 5. Briefing: path contains 30-system/briefings/
  if (path.includes("30-system/briefings/")) {
    return { kind: NoteKind.Briefing, id, model, tags: allTags };
  }

  // 6. Nudges: path ends with 30-system/nudges.md
  if (path.endsWith("30-system/nudges.md")) {
    return { kind: NoteKind.Nudges, id, model, tags: allTags };
  }

  // 7. Research: path contains hapax-research/ + tags include hapax/research
  if (path.includes("hapax-research/") && allTags.includes("hapax/research")) {
    return { kind: NoteKind.Research, id, model, tags: allTags };
  }

  // 8. Concept: path contains 33 Permanent notes/ + tags include type/concept
  if (path.includes("33 Permanent notes/") && allTags.includes("type/concept")) {
    return { kind: NoteKind.Concept, id, model, tags: allTags };
  }

  // 9. Unknown
  return { kind: NoteKind.Unknown, id, model, tags: allTags };
}

function normalizeTags(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.filter((t) => typeof t === "string");
  }
  if (typeof raw === "string") {
    return raw.split(/[,\s]+/).filter(Boolean);
  }
  return [];
}
