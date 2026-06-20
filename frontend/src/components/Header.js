import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

function Header({
  onLoginClick,
  onRegisterClick,
  onLogout,
  user,
  theme,
  onToggleTheme,
  locale,
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

  /* ─── App header ─── */
  return (
    <header className="header">
      <div className="header-left">
        <Link className="play-button" to={user ? "/dashboard" : "/"}>
          {t("header.home")}
        </Link>
      </div>
      <div className="header-right">
        {showModerationLink && (
          <Link className="auth-button" to="/moderation">
            {t("header.moderation")}
          </Link>
        )}
        {showAdminLink && (
          <Link className="auth-button" to="/admin">
            {t("header.admin")}
          </Link>
        )}
        <button
          className="auth-button theme-toggle"
          type="button"
          onClick={onToggleTheme}
        >
          {theme === "dark" ? t("header.lightTheme") : t("header.darkTheme")}
        </button>
        {user ? (
          <>
            <span className="welcome">{user.username}</span>
            <button className="auth-button" onClick={onLogout}>
              {t("header.logout")}
            </button>
          </>
        ) : (
          <button className="auth-button" onClick={onLoginClick}>
            {t("header.login")}
          </button>
        )}
      </div>
    </header>
  );
}

export default Header;
