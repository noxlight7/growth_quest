import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';

function GamePage({ apiBaseUrl, authRequest, locale, onLocaleChange, t }) {
  const { id } = useParams();
  const runId = Number(id);
  const [characters, setCharacters] = useState([]);
  const [history, setHistory] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [heroState, setHeroState] = useState('');
  const [error, setError] = useState('');
  const [generating, setGenerating] = useState(false);
  const [asHero, setAsHero] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [runInfo, setRunInfo] = useState(null);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [accessibility, setAccessibility] = useState(null);
  const [growthSummary, setGrowthSummary] = useState(null);
  const socketRef = useRef(null);

  const mergeHistoryEntries = (current, incoming) => {
    const merged = [...current];
    const known = new Map();
    merged.forEach((entry) => {
      if (entry?.id !== undefined && entry?.id !== null) {
        known.set(entry.id, entry);
      }
    });
    (incoming || []).forEach((entry) => {
      if (!entry || entry.id === undefined || entry.id === null) return;
      known.set(entry.id, entry);
    });
    return Array.from(known.values()).sort((a, b) => a.id - b.id);
  };

  useEffect(() => {
    const fetchState = async () => {
      try {
        const [
          charsResponse,
          historyResponse,
          runResponse,
          accessibilityResponse,
          growthResponse,
        ] = await Promise.all([
          authRequest({
            method: 'get',
            url: `${apiBaseUrl}/api/adventures/runs/${runId}/characters/party/`,
          }),
          authRequest({
            method: 'get',
            url: `${apiBaseUrl}/api/adventures/runs/${runId}/history/`,
          }),
          authRequest({
            method: 'get',
            url: `${apiBaseUrl}/api/adventures/runs/${runId}/`,
          }),
          authRequest({
            method: 'get',
            url: `${apiBaseUrl}/api/accessibility/profile/`,
          }),
          authRequest({
            method: 'get',
            url: `${apiBaseUrl}/api/adventures/runs/${runId}/growth/summary/`,
          }),
        ]);
        setCharacters(charsResponse.data);
        setHistory((prev) => mergeHistoryEntries(prev, historyResponse.data || []));
        setRunInfo(runResponse.data);
        setAccessibility(accessibilityResponse.data);
        if (accessibilityResponse.data?.locale) {
          onLocaleChange(accessibilityResponse.data.locale);
        }
        setGrowthSummary(growthResponse.data);
      } catch (err) {
        setError(t('game.loadFailed'));
      }
    };
    fetchState();
  }, [apiBaseUrl, authRequest, onLocaleChange, runId, t]);

  useEffect(() => {
    if (accessibility?.high_contrast) {
      document.documentElement.setAttribute('data-high-contrast', 'true');
    } else {
      document.documentElement.removeAttribute('data-high-contrast');
    }
    return () => document.documentElement.removeAttribute('data-high-contrast');
  }, [accessibility?.high_contrast]);

  const refreshGrowth = async () => {
    try {
      const growthResponse = await authRequest({
        method: 'get',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/growth/summary/`,
      });
      setGrowthSummary(growthResponse.data);
    } catch (err) {
      // Gameplay should continue even if growth summary refresh fails.
    }
  };

  const updateAccessibility = async (patch) => {
    const nextProfile = { ...(accessibility || {}), ...patch };
    setAccessibility(nextProfile);
    try {
      const response = await authRequest({
        method: 'put',
        url: `${apiBaseUrl}/api/accessibility/profile/`,
        data: patch,
      });
      setAccessibility(response.data);
      if (response.data?.locale) {
        onLocaleChange(response.data.locale);
      }
      await refreshGrowth();
    } catch (err) {
      setError(t('game.accessibilitySaveFailed'));
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('access');
    if (!token) return;
    let wsUrl;
    try {
      const baseUrl = new URL(apiBaseUrl);
      const protocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      baseUrl.protocol = protocol;
      baseUrl.pathname = `/ws/adventures/${runId}/`;
      baseUrl.search = '';
      baseUrl.searchParams.set('token', token);
      wsUrl = baseUrl.toString();
    } catch (err) {
      return;
    }
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload?.type !== 'history') return;
        const entries = Array.isArray(payload.entries) ? payload.entries : [];
        if (!entries.length) return;
        setHistory((prev) => mergeHistoryEntries(prev, entries));
      } catch (err) {
        // Ignore malformed socket payloads.
      }
    };
    socket.onclose = () => {
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
    return () => {
      socket.close();
    };
  }, [apiBaseUrl, runId]);

  const handleSubmitPrompt = async (event) => {
    event.preventDefault();
    if (!prompt.trim() || submitting || generating || historyBusy) return;
    setError('');
    setSubmitting(true);
    try {
      if (asHero) {
        const response = await authRequest({
          method: 'post',
          url: `${apiBaseUrl}/api/adventures/runs/${runId}/history/hero/`,
          data: {
            content: prompt.trim(),
            hero_state: heroState.trim(),
          },
        });
        const userEntry = response.data.user_entry;
        const npcEntry = response.data.npc_entry;
        const aiEntry = response.data.ai_entry;
        setHistory((prev) => mergeHistoryEntries(prev, [userEntry, npcEntry, aiEntry]));
      } else {
        const response = await authRequest({
          method: 'post',
          url: `${apiBaseUrl}/api/adventures/runs/${runId}/history/`,
          data: {
            content: prompt.trim(),
            hero_state: heroState.trim(),
          },
        });
        if (response.data?.user_entry || response.data?.ai_entry || response.data?.npc_entry) {
          const userEntry = response.data.user_entry;
          const npcEntry = response.data.npc_entry;
          const aiEntry = response.data.ai_entry;
          setHistory((prev) => mergeHistoryEntries(prev, [userEntry, npcEntry, aiEntry]));
        } else {
          setHistory((prev) => mergeHistoryEntries(prev, [response.data]));
        }
      }
      setPrompt('');
      setHeroState('');
      await refreshGrowth();
    } catch (err) {
      const detailKey = {
        'Adventure not started.': 'game.notStarted',
        'Model response is already in progress.': 'game.responseInProgress',
        'Hero not selected.': 'game.heroNotSelected',
        'Content is required.': 'game.contentRequired',
      }[err.response?.data?.detail];
      setError(
        err.response?.data?.safety
          ? t('game.blocked')
          : t(detailKey || 'game.submitFailed')
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleGenerateNext = async () => {
    if (generating || submitting || historyBusy) return;
    setError('');
    setGenerating(true);
    try {
      const response = await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/history/next/`,
      });
      setHistory((prev) => mergeHistoryEntries(prev, [response.data]));
      await refreshGrowth();
    } catch (err) {
      setError(t('game.generateFailed'));
    } finally {
      setGenerating(false);
    }
  };

  const handlePass = async () => {
    if (historyBusy || submitting || generating) return;
    setHistoryBusy(true);
    setError('');
    try {
      const response = await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/history/pass/`,
      });
      const npcEntry = response.data?.npc_entry;
      const aiEntry = response.data?.ai_entry;
      if (npcEntry || aiEntry) {
        setHistory((prev) => mergeHistoryEntries(prev, [npcEntry, aiEntry]));
      }
      await refreshGrowth();
    } catch (err) {
      setError(t('game.passFailed'));
    } finally {
      setHistoryBusy(false);
    }
  };

  const handleRollback = async (entryId) => {
    if (historyBusy || submitting || generating) return;
    setHistoryBusy(true);
    setError('');
    try {
      await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/history/${entryId}/rollback/`,
      });
      setHistory((prev) => prev.filter((entry) => entry.id <= entryId));
      await refreshGrowth();
    } catch (err) {
      setError(t('game.rollbackFailed'));
    } finally {
      setHistoryBusy(false);
    }
  };

  const handleRegenerateLast = async () => {
    if (historyBusy || submitting || generating) return;
    setHistoryBusy(true);
    setError('');
    try {
      const response = await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/history/last/regenerate/`,
      });
      const npcEntry = response.data?.npc_entry;
      const aiEntry = response.data?.ai_entry || response.data;
      setHistory((prev) => {
        if (!prev.length) return prev;
        const lastEntry = prev[prev.length - 1];
        let trimmed = prev.slice(0, -1);
        const npcEntryId = lastEntry?.metadata?.npc_entry_id;
        if (npcEntryId) {
          trimmed = trimmed.filter((entry) => entry.id !== npcEntryId);
        } else if (trimmed.length && trimmed[trimmed.length - 1]?.metadata?.npc_entry) {
          trimmed = trimmed.slice(0, -1);
        }
        return mergeHistoryEntries(trimmed, [npcEntry, aiEntry]);
      });
      await refreshGrowth();
    } catch (err) {
      setError(t('game.regenerateFailed'));
    } finally {
      setHistoryBusy(false);
    }
  };

  const handleExportPdf = async () => {
    if (pdfBusy) return;
    setPdfBusy(true);
    setError('');
    try {
      const response = await authRequest({
        method: 'get',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/history/pdf/`,
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `adventure_${runId}_history.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(t('game.pdfFailed'));
    } finally {
      setPdfBusy(false);
    }
  };

  const handleChoiceCard = (card) => {
    setPrompt(card);
  };

  const rollbackMinId = runInfo?.rollback_min_history_id ?? null;
  const lastEntryId = history.length ? history[history.length - 1].id : null;
  const choiceCards = growthSummary?.choice_cards || [];
  const storySettings = growthSummary?.story_settings || runInfo || {};
  const shortMode = Boolean(storySettings.story_reduced_text_length);
  const simpleMode = Boolean(storySettings.story_simple_language);
  const canViewGmDashboard = growthSummary?.can_view_gm_dashboard;

  return (
    <div className="game-page app-workspace app-workspace-wide">
      <aside className="game-sidebar">
        <h3>{t('game.growth')}</h3>
        <div className="learning-panel">
          <label>
            {t('app.locale')}
            <select
              value={accessibility?.locale || locale}
              onChange={(event) => updateAccessibility({ locale: event.target.value })}
            >
              <option value="ru">{t('locale.ru')}</option>
              <option value="en">{t('locale.en')}</option>
              <option value="zh-CN">{t('locale.zh-CN')}</option>
            </select>
          </label>
          {(simpleMode || shortMode) && (
            <div className="template-meta">
              {t('game.storyStyle')}: {[
                simpleMode ? t('game.simpleLanguage') : null,
                shortMode ? t('game.shortAnswers') : null,
              ]
                .filter(Boolean)
                .join(', ')}
            </div>
          )}
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={accessibility?.high_contrast || false}
              onChange={(event) => updateAccessibility({ high_contrast: event.target.checked })}
            />
            {t('game.highContrast')}
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={accessibility?.choice_cards_enabled ?? true}
              onChange={(event) =>
                updateAccessibility({ choice_cards_enabled: event.target.checked })
              }
            />
            {t('game.choiceCards')}
          </label>
        </div>
        {canViewGmDashboard && (
          <a className="secondary-button teacher-link" href={`/adventures/${runId}/gm`}>
            {t('game.gmDashboard')}
          </a>
        )}
        <h3>{t('game.characters')}</h3>
        {characters.length === 0 && <p className="templates-empty">{t('game.noCharacters')}</p>}
        {characters.map((character) => (
          <div className="character-card" key={character.id}>
            <strong>
              {character.title}
              {character.player_username ? ` (${character.player_username})` : ''}
            </strong>
            <div className="template-meta">
              {t('game.stats', {
                body: character.body_power,
                mind: character.mind_power,
                will: character.will_power,
              })}
            </div>
            {character.age !== null && character.age !== undefined && (
              <div className="template-meta">{t('game.age', { age: character.age })}</div>
            )}
          </div>
        ))}
      </aside>
      <section className="game-main">
        <div className="game-stage-header">
          <div>
            <span className="dashboard-kick">{t('app.play')}</span>
            <h1 className="app-page-title">{runInfo?.title || t('game.growth')}</h1>
          </div>
          <div className="template-meta">
            {history.length ? t('game.historyCount', { count: history.length }) : t('game.emptyHistory')}
          </div>
        </div>
        <div className="history-panel">
          {history.length === 0 && <p className="templates-empty">{t('game.emptyHistory')}</p>}
          {history.map((entry) => (
            <div className="history-entry" key={entry.id}>
              <div className="history-role">{t(`history.${entry.role}`)}</div>
              <div className="history-content">{entry.content}</div>
              <div className="template-actions">
                {(rollbackMinId === null || entry.id >= rollbackMinId) &&
                  entry.id !== lastEntryId && (
                    <button
                      className="link-button"
                      type="button"
                      onClick={() => handleRollback(entry.id)}
                      disabled={historyBusy || submitting || generating}
                      title={t('game.rollbackTitle')}
                    >
                      ↩
                    </button>
                  )}
                {entry.id === lastEntryId && (
                  <button
                    className="link-button"
                    type="button"
                    onClick={handleRegenerateLast}
                    disabled={historyBusy || submitting || generating}
                    title={t('game.regenerateTitle')}
                  >
                    ↻
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
        <form className="prompt-form" onSubmit={handleSubmitPrompt}>
          {error && <div className="error-message">{error}</div>}
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={asHero}
              onChange={(event) => setAsHero(event.target.checked)}
              disabled={submitting || generating || historyBusy}
            />
            {t('game.asHero')}
          </label>
          <textarea
            rows={shortMode ? '2' : '3'}
            placeholder={
              simpleMode ? t('game.promptSimple') : t('game.promptDefault')
            }
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            disabled={submitting || generating || historyBusy}
          />
          <input
            className="hero-state-input"
            type="text"
            placeholder={t('game.heroStatePlaceholder')}
            value={heroState}
            onChange={(event) => setHeroState(event.target.value)}
            disabled={submitting || generating || historyBusy}
          />
          {choiceCards.length > 0 && (
            <div className="choice-cards">
              {choiceCards.map((card) => (
                <button
                  className="choice-card"
                  type="button"
                  key={card}
                  onClick={() => handleChoiceCard(card)}
                  disabled={submitting || generating || historyBusy}
                >
                  {card}
                </button>
              ))}
            </div>
          )}
          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={submitting || generating || historyBusy}
            >
              {t('game.submit')}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={handleGenerateNext}
              disabled={generating || submitting || historyBusy}
            >
              {t('game.continueStory')}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={handlePass}
              disabled={generating || submitting || historyBusy}
            >
              {t('game.pass')}
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={handleExportPdf}
              disabled={pdfBusy || submitting || generating || historyBusy}
            >
              {t('game.savePdf')}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default GamePage;
