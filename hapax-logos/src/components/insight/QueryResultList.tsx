import { useRef, useEffect } from "react";
import { QueryResult } from "./QueryResult";

export interface ResultEntry {
  id: string;
  query: string;
  markdown: string;
  isStreaming: boolean;
  error?: string | null;
  metadata?: {
    agent_used: string;
    tokens_in: number;
    tokens_out: number;
    elapsed_ms: number;
  };
}

interface QueryResultListProps {
  results: ResultEntry[];
  onDelete?: (id: string) => void;
}

export function QueryResultList({ results, onDelete }: QueryResultListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [results.length]);

  if (results.length === 0) return null;

  return (
    <div className="space-y-6">
      {results.map((r, i) => (
        <div key={r.id}>
          {i > 0 && <div className="mb-6 border-t border-zinc-800" />}
          <QueryResult
            query={r.query}
            markdown={r.markdown}
            isStreaming={r.isStreaming}
            error={r.error}
            metadata={r.metadata}
            onDelete={onDelete ? () => onDelete(r.id) : undefined}
          />
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
