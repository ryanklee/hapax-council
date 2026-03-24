import { useCallback, useMemo, useState } from "react";
import { QueryInput } from "../components/insight/QueryInput";
import {
  QueryResultList,
  type ResultEntry,
} from "../components/insight/QueryResultList";
import { RefinementInput } from "../components/insight/RefinementInput";
import {
  useInsightQueries,
  useRunInsightQuery,
  useRefineInsightQuery,
  useDeleteInsightQuery,
} from "../api/hooks";
import { Sparkles } from "lucide-react";

export function InsightPage() {
  const [hasRunning, setHasRunning] = useState(false);
  const { data } = useInsightQueries(hasRunning);
  const runQuery = useRunInsightQuery();
  const refineQuery = useRefineInsightQuery();
  const deleteQuery = useDeleteInsightQuery();

  const queries = data?.queries ?? [];
  const isLoading = runQuery.isPending || refineQuery.isPending;

  // Track whether any query is running (drives fast polling)
  const anyRunning = queries.some((q) => q.status === "running");
  if (anyRunning !== hasRunning) setHasRunning(anyRunning);

  // Map backend records to ResultEntry shape for existing components
  const results: ResultEntry[] = useMemo(
    () =>
      // queries are newest-first from API, reverse for chronological display
      [...queries].reverse().map((q) => ({
        id: q.id,
        query: q.query,
        markdown: q.error ? `> **Error:** ${q.error}` : q.markdown,
        isStreaming: q.status === "running",
        error: q.error,
        metadata:
          q.status === "done" && q.elapsed_ms != null
            ? {
                agent_used: q.agent_type,
                tokens_in: q.tokens_in ?? 0,
                tokens_out: q.tokens_out ?? 0,
                elapsed_ms: q.elapsed_ms,
              }
            : undefined,
      })),
    [queries],
  );

  const handleQuery = useCallback(
    (query: string) => {
      runQuery.mutate(query);
    },
    [runQuery],
  );

  const handleRefine = useCallback(
    (query: string) => {
      const lastDone = queries.find((q) => q.status === "done");
      if (!lastDone) return;
      refineQuery.mutate({
        query,
        parentId: lastDone.id,
        priorResult: lastDone.markdown,
        agentType: lastDone.agent_type,
      });
    },
    [queries, refineQuery],
  );

  const handleDelete = useCallback(
    (id: string) => {
      deleteQuery.mutate(id);
    },
    [deleteQuery],
  );

  const lastResult = results[results.length - 1];
  const showRefinement =
    lastResult && !lastResult.isStreaming && lastResult.metadata;

  return (
    <div className="flex flex-1 flex-col">
      <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-4 p-6">
        <QueryInput onSubmit={handleQuery} isLoading={isLoading} />

        {results.length === 0 && !isLoading && (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-zinc-600">
            <Sparkles className="h-8 w-8" />
            <p className="text-sm">
              Ask about development history, system patterns, or architecture
            </p>
          </div>
        )}

        <div className="flex-1 overflow-y-auto">
          <QueryResultList results={results} onDelete={handleDelete} />
          {showRefinement && (
            <RefinementInput onSubmit={handleRefine} isLoading={isLoading} />
          )}
        </div>
      </div>
    </div>
  );
}
