import { useEffect, useMemo, useRef, useState } from "react";
import {
  createCodeSession,
  getExecutionResult,
  runCodeSession,
  updateCodeSession,
} from "../api/codeExecutionApi";
import { createAnalyzerSocket } from "../api/analyzerSocket";
import CodeEditorPanel from "../components/CodeEditorPanel";
import AnalysisScorePill from "../components/AnalysisScorePill";
import EditorToolbar from "../components/EditorToolbar";
import ErrorAlert from "../components/ErrorAlert";
import OutputTabsPanel from "../components/OutputTabsPanel";
import SessionMeta from "../components/SessionMeta";
import StatusPill from "../components/StatusPill";
import WorkspaceHeader from "../components/WorkspaceHeader";
import { TERMINAL_STATUSES } from "../utils/executionStatus";
import {
  LANGUAGE_OPTIONS,
  LANGUAGE_TEMPLATES,
} from "../utils/languageTemplates";

const ANALYZER_SOCKET_SESSION_ID = "workspace-live-analysis";
const DEFAULT_ANALYSIS_RESULT = {
  alerts: [],
  score: 100,
  summary: "No issues detected.",
  parse_error: null,
};

export default function ExecutionWorkspacePage() {
  const [language, setLanguage] = useState("python");
  const [sourceCode, setSourceCode] = useState(LANGUAGE_TEMPLATES.python);
  const [sessionId, setSessionId] = useState("");
  const [sessionStatus, setSessionStatus] = useState("");
  const [executionId, setExecutionId] = useState("");
  const [executionStatus, setExecutionStatus] = useState("");
  const [stdout, setStdout] = useState("");
  const [stderr, setStderr] = useState("");
  const [executionTimeMs, setExecutionTimeMs] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const [lastSavedAt, setLastSavedAt] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [analysisResult, setAnalysisResult] = useState({
    alerts: [],
    score: 100,
    summary: "No issues detected.",
    parse_error: null,
  });
  const [activeOutputTab, setActiveOutputTab] = useState("runtime");

  const autoSaveTimeoutRef = useRef(null);
  const pollIntervalRef = useRef(null);
  const analyzeTimeoutRef = useRef(null);
  const analyzerSocketRef = useRef(null);
  const analyzeReconnectTimeoutRef = useRef(null);
  const pendingAnalyzePayloadRef = useRef(null);
  const expectedAnalyzeVersionRef = useRef(0);
  const isClosingAnalyzerRef = useRef(false);

  const runningLabel = useMemo(() => {
    if (!executionStatus) return "Idle";
    if (TERMINAL_STATUSES.has(executionStatus)) return "Finished";
    return "Processing";
  }, [executionStatus]);

  const analysisIssueCount = analysisResult?.alerts?.length || 0;

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  const sendAnalyzePayload = (payload) => {
    pendingAnalyzePayloadRef.current = payload;
    const socket = analyzerSocketRef.current;
    if (!socket) return;

    const sent = socket.sendAnalyzeRequest(payload);
    if (sent) {
      pendingAnalyzePayloadRef.current = null;
    }
  };

  const connectAnalyzerSocket = () => {
    if (analyzerSocketRef.current) {
      analyzerSocketRef.current.close(1000, "Refreshing analyzer socket");
    }

    analyzerSocketRef.current = createAnalyzerSocket(ANALYZER_SOCKET_SESSION_ID, {
      onOpen: () => {
        setAnalysisError("");
        const payload = pendingAnalyzePayloadRef.current;
        if (payload) {
          const sent = analyzerSocketRef.current?.sendAnalyzeRequest(payload);
          if (sent) {
            pendingAnalyzePayloadRef.current = null;
          }
        }
      },
      onClose: () => {
        analyzerSocketRef.current = null;
        if (isClosingAnalyzerRef.current) {
          return;
        }

        setAnalysisError("Analyzer connection lost. Reconnecting...");
        if (analyzeReconnectTimeoutRef.current) {
          clearTimeout(analyzeReconnectTimeoutRef.current);
        }
        analyzeReconnectTimeoutRef.current = setTimeout(() => {
          connectAnalyzerSocket();
        }, 1500);
      },
      onSocketError: (message) => {
        setAnalysisError(message);
      },
      onAnalyzerError: (message, payload) => {
        if (
          typeof payload?.version === "number" &&
          payload.version !== expectedAnalyzeVersionRef.current
        ) {
          return;
        }

        setAnalysisError(message);
        setIsAnalyzing(false);
      },
      onResult: (payload) => {
        if (payload.version !== expectedAnalyzeVersionRef.current) {
          return;
        }

        setAnalysisError("");
        setAnalysisResult(payload.result || DEFAULT_ANALYSIS_RESULT);
        setIsAnalyzing(false);
      },
    });
  };

  const updateSession = async ({
    targetSessionId,
    targetLanguage = language,
    targetSource = sourceCode,
    silent = false,
  } = {}) => {
    const id = targetSessionId || sessionId;
    if (!id) return null;

    try {
      if (!silent) setIsSaving(true);
      const updated = await updateCodeSession(id, {
        language: targetLanguage,
        source_code: targetSource,
      });
      setSessionStatus(updated?.status || "");
      setLastSavedAt(new Date().toLocaleTimeString());
      return updated;
    } finally {
      if (!silent) setIsSaving(false);
    }
  };

  const createSession = async () => {
    const created = await createCodeSession({ language });
    setSessionId(created?.session_id || "");
    setSessionStatus(created?.status || "");
    await updateSession({
      targetSessionId: created?.session_id,
      targetLanguage: language,
      targetSource: sourceCode,
      silent: true,
    });
    return created?.session_id || "";
  };

  const pollExecution = async (id) => {
    const result = await getExecutionResult(id);
    if (!result) return;

    const currentStatus = result.status || "";
    setExecutionStatus(currentStatus);
    setStdout(result.stdout || "");
    setStderr(result.stderr || "");
    setExecutionTimeMs(
      result.execution_time_ms !== null && result.execution_time_ms !== undefined
        ? String(result.execution_time_ms)
        : "",
    );

    if (TERMINAL_STATUSES.has(currentStatus)) {
      stopPolling();
    }
  };

  useEffect(() => {
    return () => {
      stopPolling();
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
      if (analyzeTimeoutRef.current) {
        clearTimeout(analyzeTimeoutRef.current);
      }
      if (analyzeReconnectTimeoutRef.current) {
        clearTimeout(analyzeReconnectTimeoutRef.current);
      }
      isClosingAnalyzerRef.current = true;
      analyzerSocketRef.current?.close(1000, "Component unmounted");
    };
  }, []);

  useEffect(() => {
    isClosingAnalyzerRef.current = false;
    connectAnalyzerSocket();

    return () => {
      isClosingAnalyzerRef.current = true;
    };
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }

    autoSaveTimeoutRef.current = setTimeout(async () => {
      try {
        setError("");
        await updateSession();
      } catch (saveError) {
        setError(saveError.message);
      }
    }, 1200);
  }, [language, sourceCode, sessionId]);

  useEffect(() => {
    if (analyzeTimeoutRef.current) {
      clearTimeout(analyzeTimeoutRef.current);
    }

    if (!sourceCode.trim()) {
      expectedAnalyzeVersionRef.current += 1;
      pendingAnalyzePayloadRef.current = null;
      setIsAnalyzing(false);
      setAnalysisError("");
      setAnalysisResult({
        alerts: [],
        score: 100,
        summary: "No code to analyze.",
        parse_error: null,
      });
      return;
    }

    analyzeTimeoutRef.current = setTimeout(() => {
      const nextVersion = expectedAnalyzeVersionRef.current + 1;
      expectedAnalyzeVersionRef.current = nextVersion;
      setIsAnalyzing(true);
      setAnalysisError("");
      sendAnalyzePayload({
        version: nextVersion,
        request_id: String(nextVersion),
        language,
        source_code: sourceCode,
      });
    }, 700);
  }, [language, sourceCode]);

  const handleLanguageChange = (nextLanguage) => {
    const prevTemplate = LANGUAGE_TEMPLATES[language];
    const nextTemplate = LANGUAGE_TEMPLATES[nextLanguage] || "";
    setLanguage(nextLanguage);
    if (!sessionId || sourceCode === prevTemplate) {
      setSourceCode(nextTemplate);
    }
  };

  const handleCreateSession = async () => {
    try {
      setError("");
      await createSession();
    } catch (createError) {
      setError(createError.message);
    }
  };

  const handleSave = async () => {
    try {
      setError("");
      if (!sessionId) {
        await createSession();
        return;
      }
      await updateSession();
    } catch (saveError) {
      setError(saveError.message);
    }
  };

  const handleRunCode = async () => {
    try {
      setError("");
      setIsRunning(true);
      stopPolling();

      let activeSessionId = sessionId;
      if (!activeSessionId) {
        activeSessionId = await createSession();
      } else {
        await updateSession({
          targetSessionId: activeSessionId,
          targetLanguage: language,
          targetSource: sourceCode,
          silent: true,
        });
      }

      const runPayload = await runCodeSession(activeSessionId);
      const runExecutionId = runPayload?.execution_id || "";
      setExecutionId(runExecutionId);
      setExecutionStatus(runPayload?.status || "");
      setStdout("");
      setStderr("");
      setExecutionTimeMs("");

      await pollExecution(runExecutionId);
      if (!TERMINAL_STATUSES.has(runPayload?.status || "")) {
        pollIntervalRef.current = setInterval(async () => {
          try {
            await pollExecution(runExecutionId);
          } catch (pollError) {
            stopPolling();
            setError(pollError.message);
          }
        }, 1500);
      }
    } catch (runError) {
      setError(runError.message);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-ink via-slate-950 to-slate-900 text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-grid-fade bg-[size:36px_36px] opacity-30" />
      <main className="relative mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <WorkspaceHeader />

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          <div className="space-y-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-5 shadow-glass backdrop-blur">
            <EditorToolbar
              language={language}
              languageOptions={LANGUAGE_OPTIONS}
              isSaving={isSaving}
              isRunning={isRunning}
              onLanguageChange={handleLanguageChange}
              onCreateSession={handleCreateSession}
              onResetTemplate={() =>
                setSourceCode(LANGUAGE_TEMPLATES[language] || sourceCode)
              }
              onSave={handleSave}
              onRun={handleRunCode}
            />

            <SessionMeta
              sessionId={sessionId}
              executionId={executionId}
              lastSavedAt={lastSavedAt}
              runningLabel={runningLabel}
            />

            <div className="flex flex-wrap gap-2">
              <StatusPill label="Session" status={sessionStatus} />
              <StatusPill label="Execution" status={executionStatus} />
              <AnalysisScorePill
                score={analysisResult?.score}
                issueCount={analysisIssueCount}
              />
            </div>

            <CodeEditorPanel
              sourceCode={sourceCode}
              onChange={setSourceCode}
            />

            <ErrorAlert error={error} />
          </div>
              
          <OutputTabsPanel
            activeTab={activeOutputTab}
            onChangeTab={setActiveOutputTab}
            stdout={stdout}
            stderr={stderr}
            executionTimeMs={executionTimeMs}
            analysisResult={analysisResult}
            analysisError={analysisError}
            isAnalyzing={isAnalyzing}
          />
        </section>
      </main>
    </div>
  );
}
