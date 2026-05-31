import React, { useState } from 'react';
import axios from 'axios';

/**
 * Register form component.
 *
 * Presents inputs for username, email, password and password confirmation.
 * When the form is submitted it calls the backend to create a new user,
 * then immediately obtains a JWT and fetches the user's profile. Upon
 * success, it invokes `onRegisterSuccess` with the user data.
 */
function RegisterForm({ onClose, onSwitchToLogin, onRegisterSuccess, apiBaseUrl, t }) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'));
      return;
    }
    try {
      // Create the user
      await axios.post(`${apiBaseUrl}/api/users/register/`, {
        username,
        email,
        password,
        password2: confirmPassword,
      });
      // Auto‑login after registration
      const tokenResponse = await axios.post(`${apiBaseUrl}/api/auth/token/`, {
        username,
        password,
      });
      const { access, refresh } = tokenResponse.data;
      localStorage.setItem('access', access);
      localStorage.setItem('refresh', refresh);
      const userResponse = await axios.get(`${apiBaseUrl}/api/users/me/`, {
        headers: { Authorization: `Bearer ${access}` },
      });
      onRegisterSuccess({ user: userResponse.data });
    } catch (err) {
      const data = err.response?.data;
      if (data) {
        const firstKey = Object.keys(data)[0];
        const errorKeyByField = {
          username: 'auth.usernameUnavailable',
          email: 'auth.emailInvalidOrTaken',
          password: 'auth.passwordRequirements',
          password2: 'auth.passwordMismatch',
        };
        setError(t(errorKeyByField[firstKey] || 'auth.registerError'));
      } else {
        setError(t('auth.registerError'));
      }
    }
  };

  return (
    <div className="modal">
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} aria-label={t('app.close')}>×</button>
        <h3>{t('auth.registerTitle')}</h3>
        {error && <p className="error-message">{error}</p>}
        <form onSubmit={handleSubmit}>
          <label>
            {t('auth.username')}
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </label>
          <label>
            {t('auth.email')}
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
          <label>
            {t('auth.confirmPassword')}
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </label>
          <button type="submit" className="submit-button">
            {t('auth.submitRegister')}
          </button>
        </form>
        <p className="switch-form">
          {t('auth.hasAccount')}{' '}
          <button type="button" className="link-button" onClick={onSwitchToLogin}>
            {t('auth.submitLogin')}
          </button>
        </p>
      </div>
    </div>
  );
}

export default RegisterForm;
