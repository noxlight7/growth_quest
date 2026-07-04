import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

function Header({
  onLoginClick,
  onRegisterClick,
  onLogout,
  user,
  theme,
  onToggleTheme,
  t,
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const isLanding = location.pathname === "/";
  const showAdminLink = user?.admin_level >= 2;
  const showModerationLink = user?.admin_level >= 1;

  /* ─── Landing header ─── */
  if (isLanding) {
    return (
      <header className="header header-landing">
        <div className="header-left">
          <Link className="landing-logo" to="/">
            GQ
          </Link>
        </div>
        <div className="header-right">
          <button
            className="theme-switch-landing"
            type="button"
            onClick={onToggleTheme}
            title={theme === "dark" ? "Light mode" : "Dark mode"}
          >
            <span
              className={`theme-switch-dot${theme === "dark" ? " theme-switch-dot-dark" : ""}`}
            />
            <span className="theme-switch-label">
              {theme === "dark" ? "☀" : "☾"}
            </span>
          </button>

          <div className="landing-auth-group">
            {user ? (
              <button
                className="landing-nav-btn landing-nav-btn-primary"
                type="button"
                onClick={() => navigate("/dashboard")}
              >
                {t("header.dashboard")}&nbsp;&nbsp;→
              </button>
            ) : (
              <>
                <button
                  className="landing-nav-btn"
                  type="button"
                  onClick={onRegisterClick}
                >
                  {t("header.signUp")}
                </button>
                <button
                  className="landing-nav-btn landing-nav-btn-primary"
                  type="button"
                  onClick={onLoginClick}
                >
                  {t("header.signIn")}
                </button>
              </>
            )}
          </div>
        </div>
      </header>
    );
  }

  /* ─── App header (внутренний) ─── */
  return (
    <header className="header header-app">
      <div className="header-left">
        <Link className="app-logo" to={user ? "/dashboard" : "/"}>
          GQ
        </Link>
      </div>
      <div className="header-right">
        {showModerationLink && (
          <Link className="app-nav-btn" to="/moderation">
            {t("header.moderation")}
          </Link>
        )}
        {showAdminLink && (
          <Link className="app-nav-btn" to="/admin">
            {t("header.admin")}
          </Link>
        )}

        <button
          className="theme-switch-landing"
          type="button"
          onClick={onToggleTheme}
          title={theme === "dark" ? "Light mode" : "Dark mode"}
        >
          <span
            className={`theme-switch-dot${theme === "dark" ? " theme-switch-dot-dark" : ""}`}
          />
          <span className="theme-switch-label">
            {theme === "dark" ? "☀" : "☾"}
          </span>
        </button>

        <div className="landing-auth-group">
          {user ? (
            <>
              <span className="app-welcome">{user.username}</span>
              <button
                className="app-nav-btn app-nav-btn-primary"
                onClick={onLogout}
              >
                {t("header.logout")}
              </button>
            </>
          ) : (
            <button
              className="app-nav-btn app-nav-btn-primary"
              onClick={onLoginClick}
            >
              {t("header.login")}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
