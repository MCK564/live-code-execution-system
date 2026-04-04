import { request } from "./client";

export function createCodeSession(body) {
  return request("/code-sessions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateCodeSession(sessionId, body) {
  return request(`/code-sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function runCodeSession(sessionId) {
  return request(`/code-sessions/${sessionId}/run`, {
    method: "POST",
  });
}

export function getExecutionResult(executionId) {
  return request(`/executions/${executionId}`, {
    method: "GET",
  });
}
