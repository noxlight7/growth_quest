import React, { useState } from "react";
import axios from "axios";

function LoginForm({
  onClose,
  onSwitchToRegister,
  onLoginSuccess,
  apiBaseUrl,
  t,
}) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const tokenResponse = await axios.post(`${apiBaseUrl}/api/auth/token/`, {
        username: identifier,
        password,
      });
      const { access, refresh } = tokenResponse.data;
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      const userResponse = await axios.get(`${apiBaseUrl}/api/users/me/`, {
        headers: { Authorization: `Bearer ${access}` },
      });
      onLoginSuccess({ user: userResponse.data });
    } catch (err) {
      setError(t("auth.badCredentials"));
    }
  };

  return (
    <div className="l-modal-overlay" onClick={onClose}>
      <div className="l-modal" onClick={(e) => e.stopPropagation()}>
        <button
          className="l-modal-close"
          onClick={onClose}
          aria-label={t("app.close")}
        >
          ×
        </button>

        <h3 className="l-modal-title">{t("auth.loginTitle")}</h3>
        <div className="l-modal-rule" />

        {error && <div className="l-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="l-form-group">
            <label className="l-label">{t("auth.identifier")}</label>
            <input
              type="text"
              className="l-input"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
            />
          </div>
          <div className="l-form-group">
            <label className="l-label">{t("auth.password")}</label>
            <input
              type="password"
              className="l-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="l-submit">
            {t("auth.submitLogin")}
          </button>
        </form>

        <div className="l-switch">
          {t("auth.noAccount")}{" "}
          <button
            type="button"
            className="l-switch-btn"
            onClick={onSwitchToRegister}
          >
            {t("auth.submitRegister")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default LoginForm;
