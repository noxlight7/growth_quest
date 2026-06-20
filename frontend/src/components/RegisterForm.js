import React, { useState } from "react";
import axios from "axios";

function RegisterForm({
  onClose,
  onSwitchToLogin,
  onRegisterSuccess,
  apiBaseUrl,
  t,
}) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError(t("auth.passwordMismatch"));
      return;
    }
    try {
      await axios.post(`${apiBaseUrl}/api/users/register/`, {
        username,
        email,
        password,
        password2: confirmPassword,
      });
      const tokenResponse = await axios.post(`${apiBaseUrl}/api/auth/token/`, {
        username,
        password,
      });
      const { access, refresh } = tokenResponse.data;
      localStorage.setItem("access", access);
      localStorage.setItem("refresh", refresh);
      const userResponse = await axios.get(`${apiBaseUrl}/api/users/me/`, {
        headers: { Authorization: `Bearer ${access}` },
      });
      onRegisterSuccess({ user: userResponse.data });
    } catch (err) {
      const data = err.response?.data;
      if (data) {
        const firstKey = Object.keys(data)[0];
        const errorKeyByField = {
          username: "auth.usernameUnavailable",
          email: "auth.emailInvalidOrTaken",
          password: "auth.passwordRequirements",
          password2: "auth.passwordMismatch",
        };
        setError(t(errorKeyByField[firstKey] || "auth.registerError"));
      } else {
        setError(t("auth.registerError"));
      }
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

        <h3 className="l-modal-title">{t("auth.registerTitle")}</h3>
        <div className="l-modal-rule" />

        {error && <div className="l-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="l-form-group">
            <label className="l-label">{t("auth.username")}</label>
            <input
              type="text"
              className="l-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="l-form-group">
            <label className="l-label">{t("auth.email")}</label>
            <input
              type="email"
              className="l-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
          <div className="l-form-group">
            <label className="l-label">{t("auth.confirmPassword")}</label>
            <input
              type="password"
              className="l-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="l-submit">
            {t("auth.submitRegister")}
          </button>
        </form>

        <div className="l-switch">
          {t("auth.hasAccount")}{" "}
          <button
            type="button"
            className="l-switch-btn"
            onClick={onSwitchToLogin}
          >
            {t("auth.submitLogin")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default RegisterForm;
