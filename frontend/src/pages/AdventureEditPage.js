import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { tabs } from './adventureEdit/constants';
import useAdventureEntity from './adventureEdit/hooks/useAdventureEntity';
import { formatTags, serializeTags, toInt, toOptionalInt } from './adventureEdit/utils';
import GeneralTab from './adventureEdit/tabs/GeneralTab';
import LocationsTab from './adventureEdit/tabs/LocationsTab';
import CharactersTab from './adventureEdit/tabs/CharactersTab';
import RacesTab from './adventureEdit/tabs/RacesTab';
import SystemsTab from './adventureEdit/tabs/SystemsTab';
import TechniquesTab from './adventureEdit/tabs/TechniquesTab';
import EventsTab from './adventureEdit/tabs/EventsTab';
import GrowthTab from './adventureEdit/tabs/GrowthTab';
import FactionsTab from './adventureEdit/tabs/FactionsTab';
import OtherInfoTab from './adventureEdit/tabs/OtherInfoTab';

const getObjectiveId = (value) => {
  if (!value) return '';
  if (typeof value === 'object') return value.id ? String(value.id) : '';
  return String(value);
};

const formatCards = (cards) => {
  if (Array.isArray(cards)) return cards.join('\n');
  if (cards && typeof cards === 'object') {
    return Object.values(cards)
      .flat()
      .filter(Boolean)
      .join('\n');
  }
  return '';
};

const serializeLines = (value) =>
  value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);

const getDefaultTranslationLocale = (sourceLocale) => (sourceLocale === 'en' ? 'ru' : 'en');

function AdventureEditPage({ user, apiBaseUrl, authRequest, entityScope = 'templates', locale, t }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const adventureId = Number(id);
  const [activeTab, setActiveTab] = useState('general');
  const [activeCharacterId, setActiveCharacterId] = useState(null);
  const [adventure, setAdventure] = useState(null);
  const [submitError, setSubmitError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [generalForm, setGeneralForm] = useState({
    title: '',
    description: '',
    spec_instructions: '',
    intro: '',
    story_locale: 'en',
    facilitator_enabled: true,
    story_simple_language: false,
    story_reduced_text_length: false,
    growth_analysis_enabled: false,
    narrative_consequences_enabled: false,
    primary_heroes: [],
  });
  const [generalError, setGeneralError] = useState('');
  const [savingGeneral, setSavingGeneral] = useState(false);
  const [exportError, setExportError] = useState('');
  const [exporting, setExporting] = useState(false);
  const [translationLocale, setTranslationLocale] = useState('ru');
  const [translationError, setTranslationError] = useState('');
  const [translating, setTranslating] = useState(false);
  const [heroSetupForm, setHeroSetupForm] = useState({
    default_location: '',
    require_race: true,
    default_race: '',
    require_age: false,
    default_age: '',
    require_body_power: true,
    default_body_power: '',
    require_mind_power: true,
    default_mind_power: '',
    require_will_power: true,
    default_will_power: '',
  });
  const [heroSetupError, setHeroSetupError] = useState('');
  const [savingHeroSetup, setSavingHeroSetup] = useState(false);

  const baseEndpoint = `${apiBaseUrl}/api/adventures/${entityScope}/${adventureId}/`;
  const heroSetupEndpoint = `${baseEndpoint}hero-setup/`;
  const isTemplate = entityScope === 'templates';
  const readOnly = Boolean(adventure && adventure.can_edit === false);

  const locations = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}locations/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      title: '',
      description: '',
      x: '0',
      y: '0',
      width: '1',
      height: '1',
      tags: '',
    },
    mapItemToForm: (item) => ({
      title: item.title || '',
      description: item.description || '',
      x: String(item.x ?? 0),
      y: String(item.y ?? 0),
      width: String(item.width ?? 1),
      height: String(item.height ?? 1),
      tags: formatTags(item.tags),
    }),
    buildPayload: (form) => ({
      title: form.title,
      description: form.description,
      x: toInt(form.x, 0),
      y: toInt(form.y, 0),
      width: toInt(form.width, 1),
      height: toInt(form.height, 1),
      tags: serializeTags(form.tags),
    }),
  });

  const races = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}races/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      title: '',
      description: '',
      life_span: '100',
      tags: '',
    },
    mapItemToForm: (item) => ({
      title: item.title || '',
      description: item.description || '',
      life_span: String(item.life_span ?? 100),
      tags: formatTags(item.tags),
    }),
    buildPayload: (form) => ({
      title: form.title,
      description: form.description,
      life_span: toInt(form.life_span, 100),
      tags: serializeTags(form.tags),
    }),
  });

  const systems = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}systems/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      title: '',
      description: '',
      w_body: '0',
      w_mind: '100',
      w_will: '0',
      formula_hint: '',
      tags: '',
    },
    mapItemToForm: (item) => ({
      title: item.title || '',
      description: item.description || '',
      w_body: String(item.w_body ?? 0),
      w_mind: String(item.w_mind ?? 0),
      w_will: String(item.w_will ?? 0),
      formula_hint: item.formula_hint || '',
      tags: formatTags(item.tags),
    }),
    buildPayload: (form) => ({
      title: form.title,
      description: form.description,
      w_body: toInt(form.w_body, 0),
      w_mind: toInt(form.w_mind, 0),
      w_will: toInt(form.w_will, 0),
      formula_hint: form.formula_hint,
      tags: serializeTags(form.tags),
    }),
  });

  const techniques = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}techniques/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      system: '',
      title: '',
      description: '',
      difficulty: '0',
      tier: '0',
      is_rankless: false,
      required_system_level: '0',
      tags: '',
    },
    mapItemToForm: (item) => ({
      system: item.system ? String(item.system) : '',
      title: item.title || '',
      description: item.description || '',
      difficulty: String(item.difficulty ?? 0),
      tier: item.tier === null || item.tier === undefined ? '' : String(item.tier),
      is_rankless: item.tier === null,
      required_system_level: String(item.required_system_level ?? 0),
      tags: formatTags(item.tags),
    }),
    buildPayload: (form) => ({
      system: form.system ? Number(form.system) : null,
      title: form.title,
      description: form.description,
      difficulty: toInt(form.difficulty, 0),
      tier: form.is_rankless ? null : toOptionalInt(form.tier) ?? 0,
      required_system_level: toInt(form.required_system_level, 0),
      tags: serializeTags(form.tags),
    }),
  });

  const factions = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}factions/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      title: '',
      description: '',
      tags: '',
    },
    mapItemToForm: (item) => ({
      title: item.title || '',
      description: item.description || '',
      tags: formatTags(item.tags),
    }),
    buildPayload: (form) => ({
      title: form.title,
      description: form.description,
      tags: serializeTags(form.tags),
    }),
  });

  const events = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}events/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      title: '',
      status: 'inactive',
      location: '',
      trigger_hint: '',
      state: '',
    },
    mapItemToForm: (item) => ({
      title: item.title || '',
      status: item.status || 'inactive',
      location: item.location ? String(item.location) : '',
      trigger_hint: item.trigger_hint || '',
      state: item.state || '',
    }),
    buildPayload: (form) => ({
      title: form.title,
      status: form.status,
      location: form.location ? Number(form.location) : null,
      trigger_hint: form.trigger_hint,
      state: form.state,
    }),
  });

  const learningObjectives = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}learning-objectives/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      code: '',
      title: '',
      description: '',
      competency: 'empathy',
      weight: '1',
      is_active: true,
    },
    mapItemToForm: (item) => ({
      code: item.code || '',
      title: item.title || '',
      description: item.description || '',
      competency: item.competency || 'empathy',
      weight: String(item.weight ?? 1),
      is_active: item.is_active !== false,
    }),
    buildPayload: (form) => ({
      code: form.code,
      title: form.title,
      description: form.description,
      competency: form.competency,
      weight: toInt(form.weight, 1),
      is_active: Boolean(form.is_active),
    }),
  });

  const reflectionPrompts = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}reflection-prompts/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      objective: '',
      trigger_kind: 'key_choice',
      question: '',
      is_active: true,
    },
    mapItemToForm: (item) => ({
      objective: getObjectiveId(item.objective),
      trigger_kind: item.trigger_kind || 'key_choice',
      question: item.question || '',
      is_active: item.is_active !== false,
    }),
    buildPayload: (form) => ({
      objective: form.objective ? Number(form.objective) : null,
      trigger_kind: form.trigger_kind,
      question: form.question,
      is_active: Boolean(form.is_active),
    }),
  });

  const pedagogicalInterventions = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}pedagogical-interventions/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      objective: '',
      kind: 'dilemma',
      constraint: '',
      cards: '',
      is_active: true,
    },
    mapItemToForm: (item) => {
      const payload = item.payload && typeof item.payload === 'object' ? item.payload : {};
      return {
        objective: getObjectiveId(item.objective),
        kind: item.kind || 'dilemma',
        constraint: payload.constraint || payload.hint || payload.description || '',
        cards: formatCards(payload.cards),
        is_active: item.is_active !== false,
      };
    },
    buildPayload: (form) => ({
      objective: form.objective ? Number(form.objective) : null,
      kind: form.kind,
      payload:
        form.kind === 'choice_cards'
          ? { cards: serializeLines(form.cards) }
          : { constraint: form.constraint },
      is_active: Boolean(form.is_active),
    }),
  });

  const otherInfo = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}other-info/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      category: '',
      title: '',
      description: '',
      tags: '',
    },
    mapItemToForm: (item) => ({
      category: item.category || '',
      title: item.title || '',
      description: item.description || '',
      tags: formatTags(item.tags),
    }),
    buildPayload: (form) => ({
      category: form.category,
      title: form.title,
      description: form.description,
      tags: serializeTags(form.tags),
    }),
  });

  const characters = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}characters/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      title: '',
      description: '',
      is_player: false,
      in_party: false,
      age: '',
      body_power: '0',
      body_power_progress: '0',
      mind_power: '0',
      mind_power_progress: '0',
      will_power: '0',
      will_power_progress: '0',
      race: '',
      location: '',
      tags: '',
    },
    mapItemToForm: (item) => ({
      title: item.title || '',
      description: item.description || '',
      is_player: Boolean(item.is_player),
      in_party: Boolean(item.in_party),
      age: item.age === null || item.age === undefined ? '' : String(item.age),
      body_power: String(item.body_power ?? 0),
      body_power_progress: String(item.body_power_progress ?? 0),
      mind_power: String(item.mind_power ?? 0),
      mind_power_progress: String(item.mind_power_progress ?? 0),
      will_power: String(item.will_power ?? 0),
      will_power_progress: String(item.will_power_progress ?? 0),
      race: item.race ? String(item.race) : '',
      location: item.location ? String(item.location) : '',
      tags: formatTags(item.tags),
    }),
    buildPayload: (form) => ({
      title: form.title,
      description: form.description,
      is_player: Boolean(form.is_player),
      in_party: Boolean(form.in_party),
      age: toOptionalInt(form.age),
      body_power: toInt(form.body_power, 0),
      body_power_progress: toInt(form.body_power_progress, 0),
      mind_power: toInt(form.mind_power, 0),
      mind_power_progress: toInt(form.mind_power_progress, 0),
      will_power: toInt(form.will_power, 0),
      will_power_progress: toInt(form.will_power_progress, 0),
      race: form.race ? Number(form.race) : null,
      location: form.location ? Number(form.location) : null,
      tags: serializeTags(form.tags),
    }),
    onSaved: (item) => {
      setActiveCharacterId(item.id);
    },
  });

  const characterSystems = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}character-systems/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      system: '',
      level: '0',
      progress_percent: '0',
      notes: '',
    },
    mapItemToForm: (item) => ({
      system: item.system ? String(item.system) : '',
      level: String(item.level ?? 0),
      progress_percent: String(item.progress_percent ?? 0),
      notes: item.notes || '',
    }),
    buildPayload: (form) => ({
      character: activeCharacterId,
      system: form.system ? Number(form.system) : null,
      level: toInt(form.level, 0),
      progress_percent: toInt(form.progress_percent, 0),
      notes: form.notes,
    }),
  });

  const characterTechniques = useAdventureEntity({
    adventureId,
    endpoint: `${baseEndpoint}character-techniques/`,
    authRequest,
    readOnly,
    t,
    initialForm: {
      system: '',
      technique: '',
      notes: '',
    },
    mapItemToForm: (item) => {
      const technique = techniques.items.find((entry) => entry.id === item.technique);
      return {
        system: technique?.system ? String(technique.system) : '',
        technique: item.technique ? String(item.technique) : '',
        notes: item.notes || '',
      };
    },
    buildPayload: (form) => ({
      character: activeCharacterId,
      technique: form.technique ? Number(form.technique) : null,
      notes: form.notes,
    }),
  });

  useEffect(() => {
    if (!user || !adventureId) return;
    const fetchAdventure = async () => {
      try {
        const response = await authRequest({ method: 'get', url: baseEndpoint });
        setAdventure(response.data);
        setTranslationLocale(getDefaultTranslationLocale(response.data.story_locale || 'en'));
        setGeneralForm({
          title: response.data.title || '',
          description: response.data.description || '',
          spec_instructions: response.data.spec_instructions || '',
          intro: response.data.intro || '',
          story_locale: response.data.story_locale || 'en',
          facilitator_enabled: response.data.facilitator_enabled !== false,
          story_simple_language: Boolean(response.data.story_simple_language),
          story_reduced_text_length: Boolean(response.data.story_reduced_text_length),
          growth_analysis_enabled: Boolean(response.data.growth_analysis_enabled),
          narrative_consequences_enabled: Boolean(response.data.narrative_consequences_enabled),
          primary_heroes: (response.data.primary_heroes || []).map((heroId) => String(heroId)),
        });
      } catch (error) {
        setAdventure(null);
      }
    };
    fetchAdventure();
  }, [user, adventureId, authRequest, baseEndpoint]);

  useEffect(() => {
    if (!user || !adventureId) return;
    const fetchHeroSetup = async () => {
      if (!isTemplate) return;
      try {
        const response = await authRequest({ method: 'get', url: heroSetupEndpoint });
        setHeroSetupForm({
          default_location: response.data.default_location ? String(response.data.default_location) : '',
          require_race: Boolean(response.data.require_race),
          default_race: response.data.default_race ? String(response.data.default_race) : '',
          require_age: Boolean(response.data.require_age),
          default_age:
            response.data.default_age === null || response.data.default_age === undefined
              ? ''
              : String(response.data.default_age),
          require_body_power: Boolean(response.data.require_body_power),
          default_body_power:
            response.data.default_body_power === null || response.data.default_body_power === undefined
              ? ''
              : String(response.data.default_body_power),
          require_mind_power: Boolean(response.data.require_mind_power),
          default_mind_power:
            response.data.default_mind_power === null || response.data.default_mind_power === undefined
              ? ''
              : String(response.data.default_mind_power),
          require_will_power: Boolean(response.data.require_will_power),
          default_will_power:
            response.data.default_will_power === null || response.data.default_will_power === undefined
              ? ''
              : String(response.data.default_will_power),
        });
      } catch (error) {
        setHeroSetupError(t('editor.heroSetupLoadFailed'));
      }
    };
    fetchHeroSetup();
  }, [user, adventureId, authRequest, heroSetupEndpoint, isTemplate, t]);

  const activeCharacter = characters.items.find((entry) => entry.id === activeCharacterId) || null;
  const activeCharacterSystems = characterSystems.items.filter(
    (entry) => entry.character === activeCharacterId
  );
  const activeCharacterTechniques = characterTechniques.items.filter(
    (entry) => entry.character === activeCharacterId
  );
  const availableSystemsForTechniques = systems.items.filter((system) =>
    activeCharacterSystems.some((entry) => entry.system === system.id)
  );

  const heroSetupSummary = (() => {
    const requiredFields = [];
    const presetFields = [];
    const raceTitle =
      heroSetupForm.default_race &&
      races.items.find((race) => race.id === Number(heroSetupForm.default_race))?.title;
    const pushField = (label, isRequired, value) => {
      if (isRequired) {
        requiredFields.push(label);
      } else {
        presetFields.push(`${label}: ${value}`);
      }
    };
    const locationTitle =
      heroSetupForm.default_location &&
      locations.items.find((location) => location.id === Number(heroSetupForm.default_location))
        ?.title;
    presetFields.push(t('editor.summaryField', { label: t('editor.startLocation'), value: locationTitle || '—' }));
    pushField(t('editor.race'), heroSetupForm.require_race, raceTitle || '—');
    pushField(t('editor.age'), heroSetupForm.require_age, heroSetupForm.default_age || '—');
    pushField(t('editor.bodyPower'), heroSetupForm.require_body_power, heroSetupForm.default_body_power || '—');
    pushField(t('editor.mindPower'), heroSetupForm.require_mind_power, heroSetupForm.default_mind_power || '—');
    pushField(t('editor.willPower'), heroSetupForm.require_will_power, heroSetupForm.default_will_power || '—');
    return { requiredFields, presetFields };
  })();

  const handleGeneralChange = (event) => {
    if (readOnly) return;
    const { name, value } = event.target;
    if (event.target.type === 'checkbox') {
      setGeneralForm((prev) => ({ ...prev, [name]: event.target.checked }));
      return;
    }
    if (name === 'primary_heroes') {
      const selected = Array.from(event.target.selectedOptions, (option) => option.value);
      setGeneralForm((prev) => ({ ...prev, primary_heroes: selected }));
      return;
    }
    setGeneralForm((prev) => ({ ...prev, [name]: value }));
  };

  const saveGeneral = async (event) => {
    event.preventDefault();
    if (readOnly) return;
    setGeneralError('');
    setSavingGeneral(true);
    try {
      const response = await authRequest({
        method: 'put',
        url: baseEndpoint,
        data: {
          title: generalForm.title,
          description: generalForm.description,
          spec_instructions: generalForm.spec_instructions,
          intro: generalForm.intro,
          story_locale: generalForm.story_locale,
          facilitator_enabled: generalForm.facilitator_enabled,
          story_simple_language: generalForm.story_simple_language,
          story_reduced_text_length: generalForm.story_reduced_text_length,
          growth_analysis_enabled: generalForm.growth_analysis_enabled,
          narrative_consequences_enabled: generalForm.narrative_consequences_enabled,
          primary_heroes: generalForm.primary_heroes.map((heroId) => Number(heroId)),
        },
      });
      setAdventure(response.data);
      if (translationLocale === response.data.story_locale) {
        setTranslationLocale(getDefaultTranslationLocale(response.data.story_locale));
      }
    } catch (error) {
      setGeneralError(t('editor.saveFailed'));
    } finally {
      setSavingGeneral(false);
    }
  };

  const saveHeroSetup = async (event) => {
    event.preventDefault();
    if (!isTemplate) return;
    if (readOnly) return;
    setHeroSetupError('');
    setSavingHeroSetup(true);
    try {
      await authRequest({
        method: 'put',
        url: heroSetupEndpoint,
        data: {
          default_location: heroSetupForm.default_location
            ? Number(heroSetupForm.default_location)
            : null,
          require_race: heroSetupForm.require_race,
          default_race: heroSetupForm.default_race ? Number(heroSetupForm.default_race) : null,
          require_age: heroSetupForm.require_age,
          default_age: toOptionalInt(heroSetupForm.default_age),
          require_body_power: heroSetupForm.require_body_power,
          default_body_power: toOptionalInt(heroSetupForm.default_body_power),
          require_mind_power: heroSetupForm.require_mind_power,
          default_mind_power: toOptionalInt(heroSetupForm.default_mind_power),
          require_will_power: heroSetupForm.require_will_power,
          default_will_power: toOptionalInt(heroSetupForm.default_will_power),
          require_systems: false,
          require_techniques: false,
        },
      });
    } catch (error) {
      setHeroSetupError(t('editor.heroSetupSaveFailed'));
    } finally {
      setSavingHeroSetup(false);
    }
  };

  const handleExportAdventure = async () => {
    if (!isTemplate) return;
    setExportError('');
    setExporting(true);
    try {
      const response = await authRequest({
        method: 'get',
        url: `${apiBaseUrl}/api/adventures/templates/${adventureId}/export/`,
      });
      const blob = new Blob([JSON.stringify(response.data, null, 2)], {
        type: 'application/json;charset=utf-8',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${generalForm.title || 'adventure'}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setExportError(t('editor.exportFailed'));
    } finally {
      setExporting(false);
    }
  };

  const handleTranslateAdventure = async () => {
    if (!isTemplate || readOnly || translating) return;
    setTranslationError('');
    setTranslating(true);
    try {
      const response = await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/templates/${adventureId}/translate/`,
        data: { target_locale: translationLocale },
      });
      navigate(`/adventures/${response.data.id}/edit`);
    } catch (error) {
      setTranslationError(t('editor.translationFailed'));
    } finally {
      setTranslating(false);
    }
  };

  const canSubmitForModeration =
    isTemplate &&
    adventure &&
    adventure.can_edit &&
    !adventure.is_under_moderation &&
    !adventure.is_published;

  const handleSubmitForModeration = async () => {
    if (!canSubmitForModeration) return;
    setSubmitError('');
    setSubmitting(true);
    try {
      await authRequest({
        method: 'post',
        url: `${apiBaseUrl}/api/adventures/templates/${adventureId}/submit/`,
      });
      setAdventure((prev) => (prev ? { ...prev, is_under_moderation: true } : prev));
    } catch (error) {
      setSubmitError(t('editor.submitModerationFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  if (!user) {
    return <h2>{t('editor.loginRequired')}</h2>;
  }

  return (
    <div className="adventure-editor">
      <div className="editor-header">
        <div>
          <h2>{adventure ? adventure.title : t('editor.title')}</h2>
          <p className="editor-subtitle">
            {readOnly
              ? t('editor.readOnly')
              : t('editor.subtitle')}
          </p>
          {adventure?.is_under_moderation && (
            <p className="template-meta">{t('editor.underModeration')}</p>
          )}
          {adventure?.is_published && (
            <p className="template-meta">{t('editor.published')}</p>
          )}
        </div>
        <Link className="secondary-button" to="/">
          {t('editor.backToList')}
        </Link>
      </div>

      <div className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            type="button"
            onClick={() => setActiveTab(tab.id)}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'general' && (
          <GeneralTab
            generalForm={generalForm}
            generalError={generalError}
            savingGeneral={savingGeneral}
            handleGeneralChange={handleGeneralChange}
            saveGeneral={saveGeneral}
            isTemplate={isTemplate}
            exportError={exportError}
            exporting={exporting}
            handleExportAdventure={handleExportAdventure}
            sourceStoryLocale={adventure?.story_locale || generalForm.story_locale}
            translationLocale={translationLocale}
            setTranslationLocale={setTranslationLocale}
            translationError={translationError}
            translating={translating}
            handleTranslateAdventure={handleTranslateAdventure}
            readOnly={readOnly}
            canSubmitForModeration={canSubmitForModeration}
            submittingModeration={submitting}
            submitModerationError={submitError}
            handleSubmitForModeration={handleSubmitForModeration}
            characters={characters}
            heroSetupSummary={heroSetupSummary}
            heroSetupForm={heroSetupForm}
            setHeroSetupForm={setHeroSetupForm}
            heroSetupError={heroSetupError}
            saveHeroSetup={saveHeroSetup}
            savingHeroSetup={savingHeroSetup}
            locations={locations}
            races={races}
            locale={locale}
            t={t}
          />
        )}
        {activeTab === 'locations' && <LocationsTab locations={locations} readOnly={readOnly} t={t} />}
        {activeTab === 'characters' && (
          <CharactersTab
            characters={characters}
            races={races}
            locations={locations}
            systems={systems}
            techniques={techniques}
            activeCharacterId={activeCharacterId}
            setActiveCharacterId={setActiveCharacterId}
            activeCharacter={activeCharacter}
            activeCharacterSystems={activeCharacterSystems}
            activeCharacterTechniques={activeCharacterTechniques}
            availableSystemsForTechniques={availableSystemsForTechniques}
            characterSystems={characterSystems}
            characterTechniques={characterTechniques}
            readOnly={readOnly}
            locale={locale}
            t={t}
          />
        )}
        {activeTab === 'races' && <RacesTab races={races} readOnly={readOnly} t={t} />}
        {activeTab === 'systems' && <SystemsTab systems={systems} readOnly={readOnly} t={t} />}
        {activeTab === 'techniques' && (
          <TechniquesTab techniques={techniques} systems={systems} readOnly={readOnly} locale={locale} t={t} />
        )}
        {activeTab === 'events' && (
          <EventsTab events={events} locations={locations} readOnly={readOnly} locale={locale} t={t} />
        )}
        {activeTab === 'growth' && (
          <GrowthTab
            objectives={learningObjectives}
            reflectionPrompts={reflectionPrompts}
            interventions={pedagogicalInterventions}
            readOnly={readOnly}
            t={t}
          />
        )}
        {activeTab === 'factions' && <FactionsTab factions={factions} readOnly={readOnly} t={t} />}
        {activeTab === 'other' && <OtherInfoTab otherInfo={otherInfo} readOnly={readOnly} t={t} />}
      </div>
    </div>
  );
}

export default AdventureEditPage;
