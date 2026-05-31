import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom';
import Header from './components/Header';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import AdventureEditPage from './pages/AdventureEditPage';
import GamePage from './pages/GamePage';
import HeroSetupPage from './pages/HeroSetupPage';
import AdventureLobbyPage from './pages/AdventureLobbyPage';
import TemplatesPage from './pages/TemplatesPage';
import AdminPage from './pages/AdminPage';
import ModerationPage from './pages/ModerationPage';
import GmDashboardPage from './pages/GmDashboardPage';
import { createTranslator, getInitialLocale, normalizeLocale } from './i18n';

// Base URL for the API. This value can be overridden by providing
// REACT_APP_API_URL in your environment (see .env.example).
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function LegacyGmRouteRedirect() {
  const { id } = useParams();
  return <Navigate to={`/adventures/${id}/gm`} replace />;
}

const getInitialTheme = () => {
  if (typeof window === 'undefined') return 'light';
  const storedTheme = localStorage.getItem('theme');
  if (storedTheme) return storedTheme;
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
};

const decodeJwtPayload = (token) => {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
        .join('')
    );
    return JSON.parse(json);
  } catch (error) {
    return null;
  }
};

const isTokenExpired = (token) => {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return false;
  const now = Math.floor(Date.now() / 1000);
  return payload.exp <= now + 30;
};

function App() {
  const [user, setUser] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [theme, setTheme] = useState(getInitialTheme);
  const [locale, setLocale] = useState(getInitialLocale);
  const t = useMemo(() => createTranslator(locale), [locale]);

  const handleLoginClick = () => {
    setShowLogin(true);
    setShowRegister(false);
  };

  const handleLogout = useCallback(() => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    setUser(null);
  }, []);

  const handleLoginSuccess = (data) => {
    setUser(data.user);
    setShowLogin(false);
    setShowRegister(false);
  };

  const handleRegisterClick = () => {
    setShowRegister(true);
    setShowLogin(false);
  };

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleLocaleChange = useCallback((nextLocale) => {
    setLocale(normalizeLocale(nextLocale));
  }, []);

  const handleRefreshToken = useCallback(async () => {
    const refresh = localStorage.getItem('refresh');
    if (!refresh) return false;
    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/token/refresh/`, {
        refresh,
      });
      localStorage.setItem('access', response.data.access);
      // Optionally update refresh token if the backend rotates it
      return true;
    } catch (error) {
      handleLogout();
      return false;
    }
  }, [handleLogout]);

  const authRequest = useCallback(
    async (config) => {
      let token = localStorage.getItem('access');
      if (token && isTokenExpired(token)) {
        const refreshed = await handleRefreshToken();
        if (refreshed) {
          token = localStorage.getItem('access');
        }
      } else if (!token) {
        const refreshed = await handleRefreshToken();
        if (refreshed) {
          token = localStorage.getItem('access');
        }
      }
      if (!token) {
        throw new Error('No access token');
      }
      try {
        return await axios({
          ...config,
          headers: {
            ...(config.headers || {}),
            'Accept-Language': locale,
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (error) {
        if (error.response?.status === 401) {
          const refreshed = await handleRefreshToken();
          if (refreshed) {
            const retryToken = localStorage.getItem('access');
            return await axios({
              ...config,
              headers: {
                ...(config.headers || {}),
                'Accept-Language': locale,
                Authorization: `Bearer ${retryToken}`,
              },
            });
          }
        }
        throw error;
      }
    },
    [handleRefreshToken, locale]
  );

  // On mount, check if there is a stored access token and fetch the current user
  useEffect(() => {
    const token = localStorage.getItem('access');
    if (!token) return;
    const fetchUser = async () => {
      try {
        const response = await authRequest({
          method: 'get',
          url: `${API_BASE_URL}/api/users/me/`,
        });
        setUser(response.data);
      } catch (error) {
        setUser(null);
      }
    };
    fetchUser();
  }, [authRequest]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute('lang', locale);
    localStorage.setItem('locale', locale);
  }, [locale]);

  return (
    <BrowserRouter>
      <div className="App">
        <Header
          onLoginClick={handleLoginClick}
          onLogout={handleLogout}
          onToggleTheme={handleToggleTheme}
          theme={theme}
          locale={locale}
          onLocaleChange={handleLocaleChange}
          t={t}
          user={user}
        />
        <main className="container">
          <Routes>
            <Route
              path="/"
              element={
                <TemplatesPage
                  user={user}
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  t={t}
                />
              }
            />
            <Route
              path="/adventures/:id/edit"
              element={
                <AdventureEditPage
                  user={user}
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  locale={locale}
                  t={t}
                />
              }
            />
            <Route
              path="/adventures/runs/:id/edit"
              element={
                <AdventureEditPage
                  user={user}
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  entityScope="runs"
                  locale={locale}
                  t={t}
                />
              }
            />
            <Route
              path="/adventures/:id/hero"
              element={<HeroSetupPage apiBaseUrl={API_BASE_URL} authRequest={authRequest} locale={locale} t={t} />}
            />
            <Route
              path="/adventures/:id/lobby"
              element={<AdventureLobbyPage apiBaseUrl={API_BASE_URL} authRequest={authRequest} t={t} />}
            />
            <Route
              path="/adventures/:id/play"
              element={
                <GamePage
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  locale={locale}
                  onLocaleChange={handleLocaleChange}
                  t={t}
                />
              }
            />
            <Route
              path="/adventures/:id/gm"
              element={
                <GmDashboardPage
                  apiBaseUrl={API_BASE_URL}
                  authRequest={authRequest}
                  t={t}
                />
              }
            />
            <Route path="/adventures/:id/facilitator" element={<LegacyGmRouteRedirect />} />
            <Route path="/adventures/:id/teacher" element={<LegacyGmRouteRedirect />} />
            <Route
              path="/admin"
              element={
                <AdminPage user={user} apiBaseUrl={API_BASE_URL} authRequest={authRequest} t={t} />
              }
            />
            <Route
              path="/moderation"
              element={
                <ModerationPage user={user} apiBaseUrl={API_BASE_URL} authRequest={authRequest} locale={locale} t={t} />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        {showLogin && (
          <div className="modal-overlay">
            <LoginForm
              onClose={() => setShowLogin(false)}
              onSwitchToRegister={handleRegisterClick}
              onLoginSuccess={handleLoginSuccess}
              apiBaseUrl={API_BASE_URL}
              t={t}
            />
          </div>
        )}
        {showRegister && (
          <div className="modal-overlay">
            <RegisterForm
              onClose={() => setShowRegister(false)}
              onSwitchToLogin={handleLoginClick}
              onRegisterSuccess={handleLoginSuccess}
              apiBaseUrl={API_BASE_URL}
              t={t}
            />
          </div>
        )}
      </div>
    </BrowserRouter>
  );
}

export default App;
