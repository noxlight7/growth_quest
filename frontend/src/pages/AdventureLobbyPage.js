import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

function AdventureLobbyPage({ apiBaseUrl, authRequest, t }) {
  const { id } = useParams();
  const runId = Number(id);
  const location = useLocation();
  const navigate = useNavigate();

  const [lobby, setLobby] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [copyStatus, setCopyStatus] = useState('');
  const [npcBusy, setNpcBusy] = useState(false);
  const socketRef = useRef(null);

  const decodeJwtPayload = useCallback((token) => {
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
    } catch (err) {
      return null;
    }
  }, []);

  const getViewerId = useCallback(() => {
    const token = localStorage.getItem('access');
    if (!token) return null;
    const payload = decodeJwtPayload(token);
    const rawId = payload?.user_id ?? null;
    const numericId = Number(rawId);
    return Number.isFinite(numericId) ? numericId : null;
  }, [decodeJwtPayload]);

  const normalizeLobby = useCallback((raw) => {
    if (!raw) return raw;
    const viewerId = getViewerId();
    const ownerId = raw.owner_id ?? raw.ownerId ?? null;
    const normalizedOwnerId = ownerId !== null ? Number(ownerId) : null;
    const playerSlot =
      raw.players?.find((player) => player?.user_id === viewerId) ??
      raw.player_slot ??
      null;
    const isOwner =
      viewerId !== null && normalizedOwnerId !== null
        ? normalizedOwnerId === viewerId
        : raw.is_owner ?? false;
    return {
      ...raw,
      player_slot: playerSlot,
      is_owner: isOwner,
    };
  }, [getViewerId]);

  const inviteToken = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('invite');
  }, [location.search]);

  const fetchLobby = useCallback(async () => {
    const response = await authRequest({
      method: 'get',
      url: `${apiBaseUrl}/api/adventures/runs/${runId}/lobby/`,
    });
    setLobby(normalizeLobby(response.data));
  }, [apiBaseUrl, authRequest, normalizeLobby, runId]);

  useEffect(() => {
    let active = true;
    const init = async () => {
      setError('');
      setLoading(true);
      try {
        if (inviteToken) {
          await authRequest({
            method: 'post',
            url: `${apiBaseUrl}/api/adventures/runs/${runId}/join/`,
            data: { token: inviteToken },
          });
          navigate(`/adventures/${runId}/lobby`, { replace: true });
        }
        await fetchLobby();
      } catch (err) {
        if (active) {
          setError(t('lobby.loadFailed'));
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    init();
    return () => {
      active = false;
    };
  }, [apiBaseUrl, authRequest, fetchLobby, inviteToken, navigate, runId, t]);

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
        if (payload?.type !== 'lobby') return;
        setLobby(normalizeLobby(payload.payload));
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
  }, [apiBaseUrl, normalizeLobby, runId]);

  const slots = useMemo(() => {
    if (!lobby) return [];
    const maxPlayers = lobby.max_players || 0;
    const players = lobby.players || [];
    const map = new Map(players.map((player) => [player.slot_number, player]));
    return Array.from({ length: maxPlayers }, (_, index) => map.get(index + 1) || null);
  }, [lobby]);

  const inviteUrl = useMemo(() => {
    if (!lobby?.invite_token) return '';
    return `${window.location.origin}/adventures/${runId}/lobby?invite=${lobby.invite_token}`;
  }, [lobby, runId]);

  const handleCopy = async () => {
    if (!inviteUrl) return;
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopyStatus(t('lobby.copySuccess'));
    } catch (err) {
      setCopyStatus(t('lobby.copyFailed'));
    }
  };

  const handleStart = async () => {
    setStarting(true);
    setError('');
    try {
      await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/start/`,
      });
      await fetchLobby();
    } catch (err) {
      setError(t('lobby.startFailed'));
    } finally {
      setStarting(false);
    }
  };

  const handleAssignNpc = async (slotNumber) => {
    if (npcBusy) return;
    setNpcBusy(true);
    setError('');
    try {
      await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/lobby/slots/${slotNumber}/npc/`,
        data: {},
      });
      await fetchLobby();
    } catch (err) {
      setError(t('lobby.assignNpcFailed'));
    } finally {
      setNpcBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="lobby-page app-workspace">
        <div className="app-page-top">
          <span className="dashboard-kick">{t('templates.lobby')}</span>
          <h1 className="app-page-title">{t('lobby.title')}</h1>
        </div>
        {error && <div className="error-message">{error}</div>}
        <p>{t('app.loading')}</p>
      </div>
    );
  }

  if (!lobby) {
    return (
      <div className="lobby-page app-workspace">
        <div className="app-page-top">
          <span className="dashboard-kick">{t('templates.lobby')}</span>
          <h1 className="app-page-title">{t('lobby.title')}</h1>
        </div>
        {error && <div className="error-message">{error}</div>}
        <p>{t('lobby.notFound')}</p>
      </div>
    );
  }

  const adventure = lobby.adventure || {};
  const sharedLocation = lobby.shared_location;
  const playerSlot = lobby.player_slot;
  const isStarted = Boolean(adventure.started_at);
  const primaryHeroes = (lobby.available_heroes || []).filter((hero) => hero.is_primary);
  const primaryHeroTitle = primaryHeroes.length
    ? primaryHeroes.map((hero) => hero.title).join(', ')
    : t('lobby.notSetPlural');

  return (
    <div className="lobby-page app-workspace">
      <section className="templates-section lobby-hero-section">
        <div className="templates-header">
          <div>
            <span className="dashboard-kick">{t('templates.lobby')}</span>
            <h1 className="app-page-title">{t('lobby.title')}</h1>
          </div>
          <div className="templates-actions">
            {lobby.is_owner && !isStarted && (
              <button
                className="primary-button"
                type="button"
                onClick={handleStart}
                disabled={!lobby.can_start || starting}
              >
                {t('lobby.start')}
              </button>
            )}
            {isStarted && (
              <Link className="primary-button" to={`/adventures/${runId}/play`}>
                {t('app.play')}
              </Link>
            )}
          </div>
        </div>
        {error && <div className="error-message">{error}</div>}
        <article className="template-card lobby-summary-card">
          <h4>{adventure.title}</h4>
          {adventure.description && <p>{adventure.description}</p>}
          <div className="template-meta">
            {t('lobby.primaryHeroes', { heroes: primaryHeroTitle })}
          </div>
          <div className="template-meta">
            {t('lobby.startLocation', { location: sharedLocation?.title || t('lobby.notSelected') })}
          </div>
        </article>
      </section>

      <section className="templates-section">
        <div className="templates-header">
          <h3>{t('lobby.inviteLink')}</h3>
        </div>
        <div className="template-card lobby-invite-card">
          <div className="lobby-invite">
            <input value={inviteUrl} readOnly />
            <button
              className="secondary-button"
              type="button"
              onClick={handleCopy}
              disabled={!inviteUrl}
            >
              {t('app.copy')}
            </button>
          </div>
          {copyStatus && <div className="template-meta">{copyStatus}</div>}
        </div>
      </section>

      <section className="templates-section">
        <div className="templates-header">
          <h3>{t('lobby.slots')}</h3>
          <div className="templates-actions">
            <Link className="secondary-button" to={`/adventures/${runId}/hero`}>
              {t('lobby.chooseAvatar')}
            </Link>
          </div>
        </div>
        <div className="templates-grid">
          {slots.map((slot, index) => (
            <article className="template-card" key={`slot-${index + 1}`}>
              <h4>{t('lobby.slot', { number: index + 1 })}</h4>
              {slot ? (
                <>
                  {slot.is_npc ? (
                    <>
                      <div className="template-meta">{t('lobby.npc')}</div>
                      <div className="template-meta">
                        {t('lobby.avatar', { avatar: slot.hero_title || t('lobby.notSelected') })}
                      </div>
                      {lobby.is_owner && !isStarted && !slot.hero_id && (
                        <div className="template-actions">
                          <Link
                            className="secondary-button"
                            to={`/adventures/${runId}/hero?npc_slot=${slot.slot_number}`}
                          >
                            {t('lobby.chooseHero')}
                          </Link>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="template-meta">{t('lobby.player', { username: slot.username })}</div>
                      <div className="template-meta">
                        {t('lobby.avatar', { avatar: slot.hero_title || t('lobby.notSelected') })}
                      </div>
                    </>
                  )}
                </>
              ) : (
                <>
                  <div className="template-meta">{t('lobby.available')}</div>
                  {lobby.is_owner && !isStarted && (
                    <div className="template-actions">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => handleAssignNpc(index + 1)}
                        disabled={npcBusy}
                      >
                        {t('lobby.assignNpc')}
                      </button>
                    </div>
                  )}
                </>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="templates-section">
        <div className="templates-header">
          <h3>{t('lobby.yourAvatar')}</h3>
        </div>
        <div className="template-card">
          {playerSlot?.hero_title ? (
            <div className="template-meta">{t('lobby.youControl', { avatar: playerSlot.hero_title })}</div>
          ) : (
            <div className="template-meta">{t('lobby.avatarNotSelected')}</div>
          )}
          <div className="template-actions">
            <Link className="primary-button" to={`/adventures/${runId}/hero`}>
              {t('lobby.chooseOrCreate')}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

export default AdventureLobbyPage;
