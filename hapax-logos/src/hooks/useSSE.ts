import { useState, useRef, useCallback } from "react";
import { startCancellableStream, type StreamHandle } from "../api/stream";

interface UseSSEReturn {
  lines: string[];
  isRunning: boolean;
  error: string | null;
  start: (path: string, body?: unknown) => void;
  cancel: () => void;
  clear: () => void;
}

export function useSSE(): UseSSEReturn {
  const [lines, setLines] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const handleRef = useRef<StreamHandle | null>(null);

  const start = useCallback((path: string, body?: unknown) => {
    // Cancel any existing stream
    handleRef.current?.cancel();
    setLines([]);
    setError(null);
    setIsRunning(true);

    startCancellableStream(path, {
      method: "POST",
      body,
      onEvent: (event) => {
        try {
          const data = JSON.parse(event.data);
          if (event.event === "output") {
            setLines((prev) => [...prev, data.line]);
          } else if (event.event === "done") {
            const msg = data.cancelled
              ? `--- cancelled (${data.duration}s) ---`
              : `--- done (exit ${data.exit_code}, ${data.duration}s) ---`;
            setLines((prev) => [...prev, msg]);
            setIsRunning(false);
          } else if (event.event === "error") {
            setError(data.message);
            setIsRunning(false);
          }
        } catch {
          // Non-JSON data, append raw
          setLines((prev) => [...prev, event.data]);
        }
      },
      onDone: () => setIsRunning(false),
      onError: (err) => {
        setError(err.message);
        setIsRunning(false);
      },
    }).then((handle) => {
      handleRef.current = handle;
    });
  }, []);

  const cancel = useCallback(() => {
    handleRef.current?.cancel();
  }, []);

  const clear = useCallback(() => {
    setLines([]);
    setError(null);
  }, []);

  return { lines, isRunning, error, start, cancel, clear };
}
