import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

function ModerationPage({ user, apiBaseUrl, authRequest, locale, t }) {
  const [queue, setQueue] = useState([]);
  const [published, setPublished] = useState([]);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [loadingPublished, setLoadingPublished] = useState(true);
  const [error, setError] = useState('');

  const isModerator = user?.admin_level >= 1;

  const fetchQueue = useCallback(async () => {
    setLoadingQueue(true);
    try {
      const response = await authRequest({
        method: 'get',
        url: `${apiBaseUrl}/api/adventures/moderation/queue/`,
      });
      setQueue(response.data);
    } catch (err) {
      setError(t('moderation.queueLoadFailed'));
    } finally {
      setLoadingQueue(false);
    }
  }, [apiBaseUrl, authRequest, t]);

  const fetchPublished = useCallback(async () => {
    setLoadingPublished(true);
    try {
      const response = await authRequest({
        method: 'get',
        url: `${apiBaseUrl}/api/adventures/moderation/published/`,
      });
      setPublished(response.data);
    } catch (err) {
      setError(t('moderation.publishedLoadFailed'));
    } finally {
      setLoadingPublished(false);
    }
  }, [apiBaseUrl, authRequest, t]);

  useEffect(() => {
    if (!isModerator) return;
    fetchQueue();
    fetchPublished();
  }, [isModerator, fetchQueue, fetchPublished]);

  const handleDecision = async (adventureId, decision) => {
    setError('');
    try {
      await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/moderation/${adventureId}/${decision}/`,
      });
      setQueue((prev) => prev.filter((item) => item.adventure_id !== adventureId));
      if (decision === 'publish') {
        fetchPublished();
      }
    } catch (err) {
      setError(t('moderation.actionFailed'));
    }
  };

  if (!isModerator) {
    return (
      <section className="moderation-page">
        <h2>{t('header.moderation')}</h2>
        <p className="admin-note">{t('moderation.restricted')}</p>
      </section>
    );
  }

  return (
    <section className="moderation-page">
      <div className="moderation-header">
        <div>
          <h2>{t('moderation.queue')}</h2>
          <p className="admin-note">{t('moderation.queueNote')}</p>
        </div>
      </div>
      {error && <p className="error-message">{error}</p>}
      <div className="moderation-list">
        {loadingQueue && <p>{t('app.loading')}</p>}
        {!loadingQueue && queue.length === 0 && (
          <p className="admin-note">{t('moderation.queueEmpty')}</p>
        )}
        {!loadingQueue && queue.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>{t('moderation.adventure')}</th>
                <th>{t('moderation.author')}</th>
                <th>{t('moderation.submitted')}</th>
                <th>{t('app.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {queue.map((entry) => (
                <tr key={entry.adventure_id}>
                  <td>{entry.title}</td>
                  <td>{entry.author_username}</td>
                  <td>{new Date(entry.submitted_at).toLocaleString(locale)}</td>
                  <td className="moderation-actions">
                    <Link className="secondary-button" to={`/adventures/${entry.adventure_id}/edit`}>
                      {t('app.open')}
                    </Link>
                    <button
                      className="primary-button"
                      type="button"
                      onClick={() => handleDecision(entry.adventure_id, 'publish')}
                    >
                      {t('moderation.publish')}
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => handleDecision(entry.adventure_id, 'reject')}
                    >
                      {t('moderation.reject')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="moderation-header">
        <div>
          <h2>{t('moderation.published')}</h2>
          <p className="admin-note">{t('moderation.publishedNote')}</p>
        </div>
      </div>
      <div className="moderation-list">
        {loadingPublished && <p>{t('app.loading')}</p>}
        {!loadingPublished && published.length === 0 && (
          <p className="admin-note">{t('moderation.publishedEmpty')}</p>
        )}
        {!loadingPublished && published.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>{t('moderation.adventure')}</th>
                <th>{t('moderation.author')}</th>
                <th>{t('moderation.publishedAt')}</th>
                <th>{t('app.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {published.map((entry) => (
                <tr key={entry.adventure_id}>
                  <td>{entry.title}</td>
                  <td>{entry.author_username}</td>
                  <td>{new Date(entry.published_at).toLocaleString(locale)}</td>
                  <td className="moderation-actions">
                    <Link className="secondary-button" to={`/adventures/${entry.adventure_id}/edit`}>
                      {t('app.open')}
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

export default ModerationPage;
