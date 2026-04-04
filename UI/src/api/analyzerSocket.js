import { buildWebSocketUrl } from "./client";

export function createAnalyzerSocket(sessionId, handlers = {}) {
  const socket = new WebSocket(
    buildWebSocketUrl(`/analyzer/ws/${encodeURIComponent(sessionId)}`),
  );

  socket.addEventListener("open", () => {
    handlers.onOpen?.();
  });

  socket.addEventListener("close", (event) => {
    handlers.onClose?.(event);
  });

  socket.addEventListener("error", () => {
    handlers.onSocketError?.("Analyzer WebSocket connection failed.");
  });

  socket.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data);

      if (payload?.type === "analyze.result") {
        handlers.onResult?.(payload);
        return;
      }

      if (payload?.type === "analyze.error") {
        handlers.onAnalyzerError?.(payload.message, payload);
      }
    } catch {
      handlers.onSocketError?.("Received an invalid message from analyzer.");
    }
  });

  return {
    close(code, reason) {
      socket.close(code, reason);
    },
    getReadyState() {
      return socket.readyState;
    },
    sendAnalyzeRequest(payload) {
      if (socket.readyState !== WebSocket.OPEN) {
        return false;
      }

      socket.send(
        JSON.stringify({
          type: "analyze.request",
          ...payload,
        }),
      );
      return true;
    },
  };
}
