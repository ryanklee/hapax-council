import { describe, it, expect, vi, beforeEach, type Mock } from "vitest";

// vi.hoisted runs before imports
const { mockInvoke, mockListen } = vi.hoisted(() => ({
  mockInvoke: vi.fn(),
  mockListen: vi.fn(),
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: mockInvoke,
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: mockListen,
}));

import { startStream, startCancellableStream, type StreamEvent } from "../stream";

/**
 * Helper: set up listen mock so it captures the callback.
 * Returns an object with a getCallback() method (call after startStream resolves)
 * and the unlisten mock.
 */
function setupListen(): { getCallback: () => (ev: { payload: unknown }) => void; unlisten: Mock } {
  const unlisten = vi.fn();
  let captured: ((ev: { payload: unknown }) => void) | null = null;

  mockListen.mockImplementation((_event: string, cb: (ev: { payload: unknown }) => void) => {
    captured = cb;
    return Promise.resolve(unlisten);
  });

  return {
    getCallback() {
      if (!captured) throw new Error("listen callback not captured yet");
      return captured;
    },
    unlisten,
  };
}

describe("startStream", () => {
  beforeEach(() => {
    mockInvoke.mockReset();
    mockListen.mockReset();
  });

  it("invokes start_stream with path, method, and body", async () => {
    mockInvoke.mockResolvedValue(42);
    setupListen();

    await startStream("/api/chat/sessions/1/send", {
      method: "POST",
      body: { message: "hello" },
      onEvent: vi.fn(),
    });

    expect(mockInvoke).toHaveBeenCalledWith("start_stream", {
      path: "/api/chat/sessions/1/send",
      method: "POST",
      body: { message: "hello" },
    });
  });

  it("defaults method and body to null", async () => {
    mockInvoke.mockResolvedValue(1);
    setupListen();

    await startStream("/api/test", { onEvent: vi.fn() });

    expect(mockInvoke).toHaveBeenCalledWith("start_stream", {
      path: "/api/test",
      method: null,
      body: null,
    });
  });

  it("listens on stream:{id} channel", async () => {
    mockInvoke.mockResolvedValue(7);
    setupListen();

    await startStream("/api/test", { onEvent: vi.fn() });

    expect(mockListen).toHaveBeenCalledWith("stream:7", expect.any(Function));
  });

  it("dispatches event payloads to onEvent callback", async () => {
    mockInvoke.mockResolvedValue(1);
    const listener = setupListen();
    const onEvent = vi.fn();

    await startStream("/api/test", { onEvent });

    listener.getCallback()({ payload: { type: "event", event: "text_delta", data: '{"content":"hi"}' } });

    expect(onEvent).toHaveBeenCalledWith<[StreamEvent]>({
      event: "text_delta",
      data: '{"content":"hi"}',
    });
  });

  it("calls onDone and unlistens on done payload", async () => {
    mockInvoke.mockResolvedValue(1);
    const listener = setupListen();
    const onDone = vi.fn();

    await startStream("/api/test", { onEvent: vi.fn(), onDone });

    listener.getCallback()({ payload: { type: "done" } });

    expect(onDone).toHaveBeenCalledOnce();
    expect(listener.unlisten).toHaveBeenCalledOnce();
  });

  it("calls onError and unlistens on error payload", async () => {
    mockInvoke.mockResolvedValue(1);
    const listener = setupListen();
    const onError = vi.fn();

    await startStream("/api/test", { onEvent: vi.fn(), onError });

    listener.getCallback()({ payload: { type: "error", data: "connection lost" } });

    expect(onError).toHaveBeenCalledOnce();
    const err: Error = onError.mock.calls[0][0];
    expect(err).toBeInstanceOf(Error);
    expect(err.message).toBe("connection lost");
    expect(listener.unlisten).toHaveBeenCalledOnce();
  });

  it("returns a StreamHandle with streamId and cancel", async () => {
    mockInvoke.mockResolvedValue(5);
    setupListen();

    const handle = await startStream("/api/test", { onEvent: vi.fn() });

    expect(handle.streamId).toBe(5);
    expect(typeof handle.cancel).toBe("function");
  });

  it("cancel invokes cancel_stream command", async () => {
    mockInvoke.mockResolvedValueOnce(5); // start_stream
    mockInvoke.mockResolvedValueOnce(undefined); // cancel_stream
    const listener = setupListen();

    const handle = await startStream("/api/test", { onEvent: vi.fn() });
    await handle.cancel();

    expect(mockInvoke).toHaveBeenCalledWith("cancel_stream", { streamId: 5 });
    expect(listener.unlisten).toHaveBeenCalledOnce();
  });
});

describe("startCancellableStream", () => {
  beforeEach(() => {
    mockInvoke.mockReset();
    mockListen.mockReset();
  });

  it("cancel invokes cancel_stream_and_server instead of cancel_stream", async () => {
    mockInvoke.mockResolvedValueOnce(3); // start_stream
    mockInvoke.mockResolvedValueOnce(undefined); // cancel_stream_and_server
    setupListen();

    const handle = await startCancellableStream("/api/test", { onEvent: vi.fn() });
    await handle.cancel();

    expect(mockInvoke).toHaveBeenCalledWith("cancel_stream_and_server", { streamId: 3 });
  });

  it("dispatches events identically to startStream", async () => {
    mockInvoke.mockResolvedValue(1);
    const listener = setupListen();
    const onEvent = vi.fn();

    await startCancellableStream("/api/test", { onEvent });

    listener.getCallback()({ payload: { type: "event", event: "output", data: "line1" } });

    expect(onEvent).toHaveBeenCalledWith({ event: "output", data: "line1" });
  });
});
