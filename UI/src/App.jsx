import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import LoginSuccessPage from "./pages/LoginSuccessPage";
import DashboardPage from "./pages/DashboardPage";
import ExecutionWorkspacePage from "./pages/ExecutionWorkspacePage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* ── Public ──────────────────────────────────── */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/login/success" element={<LoginSuccessPage />} />

          {/* ── Protected ───────────────────────────────── */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<ExecutionWorkspacePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
          </Route>

          {/* ── Fallback ─────────────────────────────────── */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
