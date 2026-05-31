import React, { useState } from 'react';
import axios from 'axios';

/**
 * Login form component.
 *
 * Presents inputs for username and password. On submit, obtains JWT
 * tokens from the backend and then fetches the user's profile. On
 * success, invokes `onLoginSuccess` with the user data; on failure,
 * displays an error message.
 */
function LoginForm({ onClose, onSwitchToRegister, onLoginSuccess, apiBaseUrl, t }) {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      // Obtain access and refresh tokens
      const tokenResponse = await axios.post(`${apiBaseUrl}/api/auth/token/`, {
        username: identifier,
        password,
      });
      const { access, refresh } = tokenResponse.data;
      localStorage.setItem('access', access);
      localStorage.setItem('refresh', refresh);
      // Fetch current user profile
      const userResponse = await axios.get(`${apiBaseUrl}/api/users/me/`, {
        headers: { Authorization: `Bearer ${access}` },
      });
      onLoginSuccess({ user: userResponse.data });
    } catch (err) {
      setError(t('auth.badCredentials'));
    }
  };

  return (
    <div className="modal">
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} aria-label={t('app.close')}>×</button>
        <h3>{t('auth.loginTitle')}</h3>
        {error && <p className="error-message">{error}</p>}
        <form onSubmit={handleSubmit}>
          <label>
            {t('auth.identifier')}
            <input
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
            />
          </label>
          <label>
            {t('auth.password')}
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          <button type="submit" className="submit-button">
            {t('auth.submitLogin')}
          </button>
        </form>
        <p className="switch-form">
          {t('auth.noAccount')}{' '}
          <button type="button" className="link-button" onClick={onSwitchToRegister}>
            {t('auth.submitRegister')}
          </button>
        </p>
      </div>
    </div>
  );
}

export default LoginForm;
