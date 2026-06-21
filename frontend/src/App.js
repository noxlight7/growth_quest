import React, { useState, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useParams,
  useLocation,
} from "react-router-dom";
import Header from "./components/Header";
import LoginForm from "./components/LoginForm";
import RegisterForm from "./components/RegisterForm";
import AdventureEditPage from "./pages/AdventureEditPage";
import GamePage from "./pages/GamePage";
import HeroSetupPage from "./pages/HeroSetupPage";
import AdventureLobbyPage from "./pages/AdventureLobbyPage";
import TemplatesPage from "./pages/TemplatesPage";
import LandingPage from "./pages/LandingPage";
import AdminPage from "./pages/AdminPage";
import ModerationPage from "./pages/ModerationPage";
import GmDashboardPage from "./pages/GmDashboardPage";
import { createTranslator, normalizeLocale } from "./i18n";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

function LegacyGmRouteRedirect() {
  const { id } = useParams();
  return <Navigate to={`/adventures/${id}/gm`} replace />;
}

const getInitialTheme = () => {
  if (typeof window === "undefined") return "light";
  const storedTheme = localStorage.getItem("theme");
  if (storedTheme) return storedTheme;
  if (
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  )
    return "dark";
  return "light";
};

/* ─── Auto-detect browser language ─── */
const getBrowserLocale = () => {
  const stored = localStorage.getItem("locale");
  if (stored) return normalizeLocale(stored);
  const lang = (
    navigator.language ||
    navigator.userLanguage ||
    "en"
  ).toLowerCase();
  if (lang.startsWith("ru")) return "ru";
  if (lang.startsWith("zh")) return "zh";
  return "en";
};

const decodeJwtPayload = (token) => {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => `%${`00${c.charCodeAt(0).toString(16)}`.slice(-2)}`)
        .join(""),
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
};

const isTokenExpired = (token) => {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return false;
  return payload.exp <= Math.floor(Date.now() / 1000) + 30;
};

function ProtectedRoute({ user, children }) {
  if (!user) return <Navigate to="/" replace />;
  return children;
}

function AppContent() {
  const location = useLocation();
  const isLanding = location.pathname === "/";

  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [theme, setTheme] = useState(getInitialTheme);
  const [locale, setLocale] = useState(getBrowserLocale);
  const t = useMemo(() => createTranslator(locale), [locale]);

  const handleLoginClick = useCallback(() => {
    setShowLogin(true);
    setShowRegister(false);
  }, []);
  const handleRegisterClick = useCallback(() => {
    setShowRegister(true);
    setShowLogin(false);
  }, []);
  const handleLogout = useCallback(() => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    setUser(null);
  }, []);
  const handleLoginSuccess = useCallback((data) => {
    setUser(data.user);
    setShowLogin(false);
    setShowRegister(false);
  }, []);
  const handleToggleTheme = useCallback(
    () => setTheme((p) => (p === "dark" ? "light" : "dark")),
    [],
  );
  const handleLocaleChange = useCallback(
    (next) => setLocale(normalizeLocale(next)),
    [],
  );

  const handleRefreshToken = useCallback(async () => {
    const refresh = localStorage.getItem("refresh");
    if (!refresh) return false;
    try {
      const res = await axios.post(`${API_BASE_URL}/api/auth/token/refresh/`, {
        refresh,
      });
      localStorage.setItem("access", res.data.access);
      return true;
    } catch {
      handleLogout();
      return false;
    }
  }, [handleLogout]);

  const authRequest = useCallback(
    async (config) => {
      let token = localStorage.getItem("access");
      if (token && isTokenExpired(token)) {
        const ok = await handleRefreshToken();
        if (ok) token = localStorage.getItem("access");
      } else if (!token) {
        const ok = await handleRefreshToken();
        if (ok) token = localStorage.getItem("access");
      }
      if (!token) throw new Error("No access token");
      try {
        return await axios({
          ...config,
          headers: {
            ...(config.headers || {}),
            "Accept-Language": locale,
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (error) {
        if (error.response?.status === 401) {
          const ok = await handleRefreshToken();
          if (ok) {
            const retry = localStorage.getItem("access");
            return await axios({
              ...config,
              headers: {
                ...(config.headers || {}),
                "Accept-Language": locale,
                Authorization: `Bearer ${retry}`,
              },
            });
          }
        }
        throw error;
      }
    },
    [handleRefreshToken, locale],
  );

  useEffect(() => {
    const token = localStorage.getItem("access");
    if (!token) return;
    (async () => {
      try {
        const r = await authRequest({
          method: "get",
          url: `${API_BASE_URL}/api/users/me/`,
        });
        setUser(r.data);
      } catch {
        setUser(null);
      }
    })();
  }, [authRequest]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);
  useEffect(() => {
    document.documentElement.setAttribute("lang", locale);
    localStorage.setItem("locale", locale);
  }, [locale]);

  return (
    <div className="App">
      <Header
        onLoginClick={handleLoginClick}
        onRegisterClick={handleRegisterClick}
        onLogout={handleLogout}
        onToggleTheme={handleToggleTheme}
        theme={theme}
        onLocaleChange={handleLocaleChange}
        t={t}
        user={user}
      />
      <main className={isLanding ? "" : "container"}>
        <Routes>
          <Route
            path="/"
            element={
              <LandingPage
                user={user}
                t={t}
                onLoginClick={handleLoginClick}
                onRegisterClick={handleRegisterClick}
              />
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute user={user}>
                <TemplatesPage
                  user={user}
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/adventures/:id/edit"
            element={
              <ProtectedRoute user={user}>
                <AdventureEditPage
                  user={user}
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  locale={locale}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/adventures/runs/:id/edit"
            element={
              <ProtectedRoute user={user}>
                <AdventureEditPage
                  user={user}
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  entityScope="runs"
                  locale={locale}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/adventures/:id/hero"
            element={
              <ProtectedRoute user={user}>
                <HeroSetupPage
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  locale={locale}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/adventures/:id/lobby"
            element={
              <ProtectedRoute user={user}>
                <AdventureLobbyPage
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/adventures/:id/play"
            element={
              <ProtectedRoute user={user}>
                <GamePage
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  locale={locale}
                  onLocaleChange={handleLocaleChange}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/adventures/:id/gm"
            element={
              <ProtectedRoute user={user}>
                <GmDashboardPage
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/adventures/:id/facilitator"
            element={
              <ProtectedRoute user={user}>
                <LegacyGmRouteRedirect />
              </ProtectedRoute>
            }
          />
          <Route
            path="/adventures/:id/teacher"
            element={
              <ProtectedRoute user={user}>
                <LegacyGmRouteRedirect />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute user={user}>
                <AdminPage
                  user={user}
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="/moderation"
            element={
              <ProtectedRoute user={user}>
                <ModerationPage
                  user={user}
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  locale={locale}
                  t={t}
                />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      {showLogin && (
        <LoginForm
          onClose={() => setShowLogin(false)}
          onSwitchToRegister={handleRegisterClick}
          onLoginSuccess={handleLoginSuccess}
          apiBaseUrl={API_BASE_URL}
          t={t}
        />
      )}
      {showRegister && (
        <RegisterForm
          onClose={() => setShowRegister(false)}
          onSwitchToLogin={handleLoginClick}
          onRegisterSuccess={handleLoginSuccess}
          apiBaseUrl={API_BASE_URL}
          t={t}
        />
      )}
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
