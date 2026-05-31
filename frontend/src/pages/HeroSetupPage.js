import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

const emptySystemEntry = { system: '', level: '0', progress_percent: '0', notes: '' };
const emptyTechniqueEntry = { system: '', technique: '', notes: '' };

function HeroSetupPage({ apiBaseUrl, authRequest, locale, t }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const runId = Number(id);
  const npcSlot = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const value = params.get('npc_slot');
    if (!value) return null;
    const slot = Number(value);
    return Number.isFinite(slot) ? slot : null;
  }, [location.search]);
  const isNpcSlot = Number.isFinite(npcSlot) && npcSlot > 0;

  const [bootstrap, setBootstrap] = useState(null);
  const [error, setError] = useState('');
  const [locationId, setLocationId] = useState('');
  const [hero, setHero] = useState({
    title: '',
    race: '',
    age: '',
    body_power: '0',
    mind_power: '0',
    will_power: '0',
  });
  const [systemEntries, setSystemEntries] = useState([{ ...emptySystemEntry }]);
  const [techniqueEntries, setTechniqueEntries] = useState([{ ...emptyTechniqueEntry }]);
  const [saving, setSaving] = useState(false);
  const [selectingHeroId, setSelectingHeroId] = useState(null);

  useEffect(() => {
    const fetchBootstrap = async () => {
      try {
        const response = await authRequest({
          method: 'get',
          url: `${apiBaseUrl}/api/adventures/runs/${runId}/bootstrap/`,
        });
        setBootstrap(response.data);
      } catch (err) {
        setError(t('heroSetup.loadFailed'));
      }
    };
    fetchBootstrap();
  }, [apiBaseUrl, authRequest, runId, t]);

  useEffect(() => {
    if (!bootstrap) return;
    const setup = bootstrap.hero_setup || {};
    setHero((prev) => ({
      ...prev,
      race: setup.require_race ? '' : setup.default_race ? String(setup.default_race) : '',
      age:
        setup.require_age || setup.default_age === null || setup.default_age === undefined
          ? ''
          : String(setup.default_age),
      body_power: setup.require_body_power
        ? ''
        : String(setup.default_body_power ?? 0),
      mind_power: setup.require_mind_power
        ? ''
        : String(setup.default_mind_power ?? 0),
      will_power: setup.require_will_power
        ? ''
        : String(setup.default_will_power ?? 0),
    }));
    setSystemEntries([{ ...emptySystemEntry }]);
    setTechniqueEntries([{ ...emptyTechniqueEntry }]);
  }, [bootstrap]);

  const systemsById = useMemo(() => {
    if (!bootstrap) return {};
    return Object.fromEntries(bootstrap.systems.map((system) => [system.id, system]));
  }, [bootstrap]);

  const availableSystemIds = useMemo(() => {
    if (!bootstrap) return [];
    return systemEntries
      .map((entry) => Number(entry.system))
      .filter((value) => Number.isFinite(value) && value > 0);
  }, [bootstrap, systemEntries]);

  const handleSystemChange = (index, field, value) => {
    setSystemEntries((prev) =>
      prev.map((entry, idx) => (idx === index ? { ...entry, [field]: value } : entry))
    );
  };

  const handleTechniqueChange = (index, field, value) => {
    setTechniqueEntries((prev) =>
      prev.map((entry, idx) => (idx === index ? { ...entry, [field]: value } : entry))
    );
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const setup = bootstrap?.hero_setup || {};
    if (!hero.title.trim()) {
      setError(t('heroSetup.nameRequired'));
      return;
    }
    const sharedLocation = bootstrap?.shared_location;
    if (!sharedLocation && !setup.default_location && !locationId) {
      setError(t('heroSetup.locationRequired'));
      return;
    }
    if (setup.require_race && !hero.race) {
      setError(t('heroSetup.raceRequired'));
      return;
    }
    if (setup.require_age && hero.age === '') {
      setError(t('heroSetup.ageRequired'));
      return;
    }
    if (setup.require_body_power && hero.body_power === '') {
      setError(t('heroSetup.bodyPowerRequired'));
      return;
    }
    if (setup.require_mind_power && hero.mind_power === '') {
      setError(t('heroSetup.mindPowerRequired'));
      return;
    }
    if (setup.require_will_power && hero.will_power === '') {
      setError(t('heroSetup.willPowerRequired'));
      return;
    }
    const selectedSystems = systemEntries.filter((entry) => entry.system);
    const selectedTechniques = techniqueEntries.filter((entry) => entry.technique);
    if (setup.require_systems && selectedSystems.length === 0) {
      setError(t('heroSetup.systemRequired'));
      return;
    }
    if (setup.require_techniques && selectedTechniques.length === 0) {
      setError(t('heroSetup.techniqueRequired'));
      return;
    }
    setError('');
    setSaving(true);
    try {
      const sharedLocationId = bootstrap?.shared_location?.id || null;
      const resolvedHero = {
        title: hero.title,
        race: setup.require_race
          ? hero.race
            ? Number(hero.race)
            : null
          : setup.default_race ?? null,
        age: setup.require_age
          ? hero.age === ''
            ? null
            : Number(hero.age)
          : setup.default_age ?? null,
        body_power: setup.require_body_power
          ? Number(hero.body_power || 0)
          : Number(setup.default_body_power ?? 0),
        mind_power: setup.require_mind_power
          ? Number(hero.mind_power || 0)
          : Number(setup.default_mind_power ?? 0),
        will_power: setup.require_will_power
          ? Number(hero.will_power || 0)
          : Number(setup.default_will_power ?? 0),
      };
      await authRequest({
        method: 'post',
        url: isNpcSlot
          ? `${apiBaseUrl}/api/adventures/runs/${runId}/lobby/slots/${npcSlot}/npc/`
          : `${apiBaseUrl}/api/adventures/runs/${runId}/hero/`,
        data: {
          location_id:
            sharedLocationId || setup.default_location ? null : Number(locationId),
          hero: resolvedHero,
          systems: selectedSystems.map((entry) => ({
            system: Number(entry.system),
            level: Number(entry.level || 0),
            progress_percent: Number(entry.progress_percent || 0),
            notes: entry.notes || '',
          })),
          techniques: selectedTechniques.map((entry) => ({
            technique: Number(entry.technique),
            notes: entry.notes || '',
          })),
        },
      });
      navigate(`/adventures/${runId}/lobby`);
    } catch (err) {
      setError(t(isNpcSlot ? 'heroSetup.createNpcFailed' : 'heroSetup.createAvatarFailed'));
    } finally {
      setSaving(false);
    }
  };

  const handleSelectHero = async (heroId) => {
    const setup = bootstrap?.hero_setup || {};
    const sharedLocation = bootstrap?.shared_location;
    if (!sharedLocation && !setup.default_location && !locationId) {
      setError(t('heroSetup.locationRequired'));
      return;
    }
    setError('');
    setSelectingHeroId(heroId);
    try {
      await authRequest({
        method: 'post',
        url: isNpcSlot
          ? `${apiBaseUrl}/api/adventures/runs/${runId}/lobby/slots/${npcSlot}/npc/`
          : `${apiBaseUrl}/api/adventures/runs/${runId}/hero/`,
        data: {
          hero_id: heroId,
          location_id:
            sharedLocation || setup.default_location ? null : Number(locationId),
        },
      });
      navigate(`/adventures/${runId}/lobby`);
    } catch (err) {
      setError(t(isNpcSlot ? 'heroSetup.selectNpcFailed' : 'heroSetup.selectAvatarFailed'));
    } finally {
      setSelectingHeroId(null);
    }
  };

  const sortedRaces = useMemo(() => {
    if (!bootstrap) return [];
    return [...bootstrap.races].sort((a, b) => a.title.localeCompare(b.title, locale));
  }, [bootstrap, locale]);

  const sortedSystems = useMemo(() => {
    if (!bootstrap) return [];
    return [...bootstrap.systems].sort((a, b) => a.title.localeCompare(b.title, locale));
  }, [bootstrap, locale]);

  const sortedTechniques = useMemo(() => {
    if (!bootstrap) return [];
    return [...bootstrap.techniques].sort((a, b) => a.title.localeCompare(b.title, locale));
  }, [bootstrap, locale]);

  const sortedLocations = useMemo(() => {
    if (!bootstrap) return [];
    return [...bootstrap.locations].sort((a, b) => a.title.localeCompare(b.title, locale));
  }, [bootstrap, locale]);

  const heroSetup = bootstrap?.hero_setup || {};

  if (!bootstrap) {
    return (
      <div className="hero-setup">
        <h2>{t(isNpcSlot ? 'heroSetup.npcTitle' : 'heroSetup.avatarTitle')}</h2>
        {error && <div className="error-message">{error}</div>}
        <p>{t('app.loading')}</p>
      </div>
    );
  }

  const sharedLocation = bootstrap.shared_location;
  const playerSlot = bootstrap.player_slot;
  const availableHeroes = isNpcSlot
    ? bootstrap.available_npc_heroes || []
    : bootstrap.available_heroes || [];
  const locationLocked = Boolean(sharedLocation) || Boolean(heroSetup.default_location);
  const formLocked = !isNpcSlot && Boolean(playerSlot?.hero_id);

  return (
    <div className="hero-setup">
      <h2>{t(isNpcSlot ? 'heroSetup.npcTitle' : 'heroSetup.avatarTitle')}</h2>
      {error && <div className="error-message">{error}</div>}
      {!isNpcSlot && playerSlot?.hero_id && (
        <div className="template-meta">{t('heroSetup.avatarSelected', { avatar: playerSlot.hero_title })}</div>
      )}
      {locationLocked ? (
        <div className="template-meta">
          {t('heroSetup.startLocation', { location: sharedLocation?.title || t('heroSetup.templateDefault') })}
        </div>
      ) : (
        <label>
          {t('editor.startLocation')}
          <select
            value={locationId}
            onChange={(event) => setLocationId(event.target.value)}
            disabled={formLocked}
          >
            <option value="">{t('editor.selectLocation')}</option>
            {sortedLocations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.title}
              </option>
            ))}
          </select>
        </label>
      )}
      {availableHeroes.length > 0 && (
        <div className="editor-subsection">
          <h3>{t(isNpcSlot ? 'heroSetup.availableCharacters' : 'heroSetup.availableHeroes')}</h3>
          {availableHeroes.map((heroItem) => (
            <div className="template-card" key={heroItem.id}>
              <strong>{heroItem.title}</strong>
              <div className="template-meta">
                {t(heroItem.is_primary ? 'heroSetup.primaryHero' : 'heroSetup.avatar')}
              </div>
              {isNpcSlot && (
                <div className="template-meta">
                  {t(heroItem.is_player ? 'heroSetup.playerCharacter' : 'heroSetup.npc')}
                </div>
              )}
              <div className="template-actions">
                {heroItem.is_taken ? (
                  <span className="template-meta">{t('heroSetup.taken')}</span>
                ) : (
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => handleSelectHero(heroItem.id)}
                    disabled={formLocked || selectingHeroId === heroItem.id}
                  >
                    {t('app.select')}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      <form className="editor-form" onSubmit={handleSubmit}>
        <label>
          {t(isNpcSlot ? 'heroSetup.npcName' : 'heroSetup.avatarName')}
          <input
            value={hero.title}
            onChange={(event) => setHero((prev) => ({ ...prev, title: event.target.value }))}
            disabled={formLocked}
          />
        </label>
        {heroSetup.require_race && (
          <label>
            {t('editor.race')}
            <select
              value={hero.race}
              onChange={(event) => setHero((prev) => ({ ...prev, race: event.target.value }))}
              disabled={formLocked}
            >
              <option value="">{t('editor.notSelected')}</option>
              {sortedRaces.map((race) => (
                <option key={race.id} value={race.id}>
                  {race.title}
                </option>
              ))}
            </select>
          </label>
        )}
        {heroSetup.require_age && (
          <label>
            {t('editor.age')}
            <input
              type="number"
              min="0"
              value={hero.age}
              onChange={(event) => setHero((prev) => ({ ...prev, age: event.target.value }))}
              disabled={formLocked}
            />
          </label>
        )}
        {(heroSetup.require_body_power ||
          heroSetup.require_mind_power ||
          heroSetup.require_will_power) && (
          <div className="form-row">
            {heroSetup.require_body_power && (
              <label>
                {t('editor.bodyPower')}
                <input
                  type="number"
                  min="0"
                  value={hero.body_power}
                  onChange={(event) =>
                    setHero((prev) => ({ ...prev, body_power: event.target.value }))
                  }
                  disabled={formLocked}
                />
              </label>
            )}
            {heroSetup.require_mind_power && (
              <label>
                {t('editor.mindPower')}
                <input
                  type="number"
                  min="0"
                  value={hero.mind_power}
                  onChange={(event) =>
                    setHero((prev) => ({ ...prev, mind_power: event.target.value }))
                  }
                  disabled={formLocked}
                />
              </label>
            )}
            {heroSetup.require_will_power && (
              <label>
                {t('editor.willPower')}
                <input
                  type="number"
                  min="0"
                  value={hero.will_power}
                  onChange={(event) =>
                    setHero((prev) => ({ ...prev, will_power: event.target.value }))
                  }
                  disabled={formLocked}
                />
              </label>
            )}
          </div>
        )}
        <div className="editor-subsection">
          <h3>{t('editor.systemKnowledge')}</h3>
          {systemEntries.map((entry, index) => (
            <div className="form-row" key={`system-${index}`}>
              <label>
                {t('editor.system')}
                <select
                  value={entry.system}
                  onChange={(event) => handleSystemChange(index, 'system', event.target.value)}
                  disabled={formLocked}
                >
                  <option value="">{t('editor.selectSystem')}</option>
                  {sortedSystems.map((system) => (
                    <option key={system.id} value={system.id}>
                      {system.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t('editor.level')}
                <input
                  type="number"
                  min="0"
                  value={entry.level}
                  onChange={(event) => handleSystemChange(index, 'level', event.target.value)}
                  disabled={formLocked}
                />
              </label>
              <label>
                {t('editor.progressPercent')}
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={entry.progress_percent}
                  onChange={(event) =>
                    handleSystemChange(index, 'progress_percent', event.target.value)
                  }
                  disabled={formLocked}
                />
              </label>
              <label>
                {t('editor.notes')}
                <input
                  value={entry.notes}
                  onChange={(event) => handleSystemChange(index, 'notes', event.target.value)}
                  disabled={formLocked}
                />
              </label>
            </div>
          ))}
          <button
            className="secondary-button"
            type="button"
            onClick={() => setSystemEntries((prev) => [...prev, { ...emptySystemEntry }])}
            disabled={formLocked}
          >
            {t('heroSetup.addSystem')}
          </button>
        </div>
        <div className="editor-subsection">
          <h3>{t('editor.learnedTechniques')}</h3>
          {techniqueEntries.map((entry, index) => (
            <div className="form-row" key={`technique-${index}`}>
              <label>
                {t('editor.system')}
                <select
                  value={entry.system}
                  onChange={(event) => handleTechniqueChange(index, 'system', event.target.value)}
                  disabled={formLocked}
                >
                  <option value="">{t('editor.selectSystem')}</option>
                  {availableSystemIds.map((systemId) => (
                    <option key={systemId} value={systemId}>
                      {systemsById[systemId]?.title || '—'}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t('editor.technique')}
                <select
                  value={entry.technique}
                  onChange={(event) =>
                    handleTechniqueChange(index, 'technique', event.target.value)
                  }
                  disabled={!entry.system || formLocked}
                >
                  <option value="">{t('editor.selectTechnique')}</option>
                  {sortedTechniques
                    .filter((technique) => technique.system === Number(entry.system))
                    .map((technique) => (
                      <option key={technique.id} value={technique.id}>
                        {technique.title}
                      </option>
                    ))}
                </select>
              </label>
              <label>
                {t('editor.notes')}
                <input
                  value={entry.notes}
                  onChange={(event) => handleTechniqueChange(index, 'notes', event.target.value)}
                  disabled={formLocked}
                />
              </label>
            </div>
          ))}
          <button
            className="secondary-button"
            type="button"
            onClick={() => setTechniqueEntries((prev) => [...prev, { ...emptyTechniqueEntry }])}
            disabled={formLocked}
          >
            {t('heroSetup.addTechnique')}
          </button>
        </div>
        <div className="form-actions">
          <button
            className="primary-button"
            type="submit"
            disabled={saving || formLocked}
          >
            {t(isNpcSlot ? 'heroSetup.createNpc' : 'heroSetup.createAvatar')}
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => navigate(`/adventures/${runId}/lobby`)}
          >
            {t('heroSetup.backToLobby')}
          </button>
        </div>
      </form>
    </div>
  );
}

export default HeroSetupPage;
