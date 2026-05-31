import React from 'react';
import { Link } from 'react-router-dom';
import { LOCALE_LABELS, SUPPORTED_LOCALES } from '../i18n';

/**
 * Header component.
 *
 * Displays the application logo and navigation. If a user is
 * authenticated, a logout button is shown; otherwise a login button
 * appears. A “Home” link is positioned on the left.
 */
function Header({ onLoginClick, onLogout, user, theme, onToggleTheme, locale, onLocaleChange, t }) {
  const showAdminLink = user?.admin_level >= 2;
  const showModerationLink = user?.admin_level >= 1;

  return (
    <header className="header">
      <div className="header-left">
        <Link className="play-button" to="/">
          {t('header.home')}
        </Link>
      </div>
      <div className="header-right">
        {showModerationLink && (
          <Link className="auth-button" to="/moderation">
            {t('header.moderation')}
          </Link>
        )}
        {showAdminLink && (
          <Link className="auth-button" to="/admin">
            {t('header.admin')}
          </Link>
        )}
        <label className="locale-control">
          <span>{t('app.locale')}</span>
          <select
            className="locale-select"
            value={locale}
            onChange={(event) => onLocaleChange(event.target.value)}
          >
            {SUPPORTED_LOCALES.map((item) => (
              <option key={item} value={item}>
                {LOCALE_LABELS[item]}
              </option>
            ))}
          </select>
        </label>
        <button className="auth-button theme-toggle" type="button" onClick={onToggleTheme}>
          {theme === 'dark' ? t('header.lightTheme') : t('header.darkTheme')}
        </button>
        {user ? (
          <>
            <span className="welcome">{user.username}</span>
            <button className="auth-button" onClick={onLogout}>
              {t('header.logout')}
            </button>
          </>
        ) : (
          <button className="auth-button" onClick={onLoginClick}>
            {t('header.login')}
          </button>
        )}
      </div>
    </header>
  );
}

export default Header;
