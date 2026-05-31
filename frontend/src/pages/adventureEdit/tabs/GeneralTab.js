import React from 'react';

import { sortByTitle } from '../utils';

function GeneralTab({
  generalForm,
  generalError,
  savingGeneral,
  handleGeneralChange,
  saveGeneral,
  isTemplate,
  exportError,
  exporting,
  handleExportAdventure,
  sourceStoryLocale,
  translationLocale,
  setTranslationLocale,
  translationError,
  translating,
  handleTranslateAdventure,
  readOnly,
  canSubmitForModeration,
  submittingModeration,
  submitModerationError,
  handleSubmitForModeration,
  characters,
  heroSetupSummary,
  heroSetupForm,
  setHeroSetupForm,
  heroSetupError,
  saveHeroSetup,
  savingHeroSetup,
  locations,
  races,
  locale,
  t,
}) {
  return (
    <>
      <form className="editor-form" onSubmit={saveGeneral}>
        {generalError && <div className="error-message">{generalError}</div>}
        <label>
          {t('editor.name')}
          <input
            name="title"
            value={generalForm.title}
            onChange={handleGeneralChange}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.description')}
          <textarea
            name="description"
            rows="3"
            value={generalForm.description}
            onChange={handleGeneralChange}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.aiInstructions')}
          <textarea
            name="spec_instructions"
            rows="3"
            value={generalForm.spec_instructions}
            onChange={handleGeneralChange}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.intro')}
          <textarea
            name="intro"
            rows="3"
            value={generalForm.intro}
            onChange={handleGeneralChange}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('game.storyLocale')}
          <select
            name="story_locale"
            value={generalForm.story_locale}
            onChange={handleGeneralChange}
            disabled={readOnly}
          >
            <option value="en">{t('locale.en')}</option>
            <option value="ru">{t('locale.ru')}</option>
            <option value="zh-CN">{t('locale.zh-CN')}</option>
          </select>
        </label>
        <div className="editor-subsection">
          <h3>{t('editor.storyModules')}</h3>
          <div className="template-meta">
            {t('editor.storyModulesNote')}
          </div>
          <label className="checkbox-row">
            <input
              type="checkbox"
              name="facilitator_enabled"
              checked={generalForm.facilitator_enabled !== false}
              onChange={handleGeneralChange}
              disabled={readOnly}
            />
            {t('editor.enableGm')}
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              name="story_simple_language"
              checked={Boolean(generalForm.story_simple_language)}
              onChange={handleGeneralChange}
              disabled={readOnly}
            />
            {t('editor.simpleLanguage')}
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              name="story_reduced_text_length"
              checked={Boolean(generalForm.story_reduced_text_length)}
              onChange={handleGeneralChange}
              disabled={readOnly}
            />
            {t('editor.shortAnswers')}
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              name="growth_analysis_enabled"
              checked={Boolean(generalForm.growth_analysis_enabled)}
              onChange={handleGeneralChange}
              disabled={readOnly}
            />
            {t('teacher.growthAnalysisEnabled')}
          </label>
          <div className="template-meta">
            {t('editor.growthAnalysisNote')}
          </div>
          <label className="checkbox-row">
            <input
              type="checkbox"
              name="narrative_consequences_enabled"
              checked={Boolean(generalForm.narrative_consequences_enabled)}
              onChange={handleGeneralChange}
              disabled={readOnly}
            />
            {t('teacher.narrativeConsequencesEnabled')}
          </label>
          <div className="template-meta">
            {t('editor.narrativeConsequencesNote')}
          </div>
        </div>
        <label>
          {t('editor.primaryHeroes')}
          <select
            multiple
            name="primary_heroes"
            value={generalForm.primary_heroes}
            onChange={handleGeneralChange}
            disabled={readOnly}
          >
            {sortByTitle(characters.items, locale).map((character) => (
              <option key={character.id} value={character.id}>
                {character.title}
              </option>
            ))}
          </select>
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={savingGeneral || readOnly}>
            {t('app.save')}
          </button>
          {isTemplate && (
            <button
              className="secondary-button"
              type="button"
              onClick={handleExportAdventure}
              disabled={exporting}
            >
              {t('editor.exportJson')}
            </button>
          )}
          {isTemplate && canSubmitForModeration && (
            <button
              className="primary-button"
              type="button"
              onClick={handleSubmitForModeration}
              disabled={submittingModeration}
            >
              {t('moderation.publish')}
            </button>
          )}
        </div>
        {exportError && <div className="error-message">{exportError}</div>}
        {submitModerationError && <div className="error-message">{submitModerationError}</div>}
        {isTemplate && !readOnly && (
          <div className="editor-subsection">
            <h3>{t('editor.translation')}</h3>
            <div className="template-meta">
              {t('editor.translationNote')}
            </div>
            <label>
              {t('editor.translationLocale')}
              <select
                value={translationLocale}
                onChange={(event) => setTranslationLocale(event.target.value)}
                disabled={translating}
              >
                <option value="en" disabled={sourceStoryLocale === 'en'}>
                  {t('locale.en')}
                </option>
                <option value="ru" disabled={sourceStoryLocale === 'ru'}>
                  {t('locale.ru')}
                </option>
                <option value="zh-CN" disabled={sourceStoryLocale === 'zh-CN'}>
                  {t('locale.zh-CN')}
                </option>
              </select>
            </label>
            <div className="form-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={handleTranslateAdventure}
                disabled={translating || translationLocale === sourceStoryLocale}
              >
                {t(translating ? 'editor.translating' : 'editor.createTranslation')}
              </button>
            </div>
            {translationError && <div className="error-message">{translationError}</div>}
          </div>
        )}
      </form>
      {isTemplate && generalForm.primary_heroes.length === 0 && (
        <form className="editor-form" onSubmit={saveHeroSetup}>
          <div className="editor-subsection">
            <h3>{t('editor.heroSetup')}</h3>
            <div className="template-meta">
              {t('editor.requiredFields', { fields: heroSetupSummary.requiredFields.join(', ') || '—' })}
            </div>
            <div className="template-meta">
              {t('editor.defaultFields', { fields: heroSetupSummary.presetFields.join(', ') || '—' })}
            </div>
          </div>
          {heroSetupError && <div className="error-message">{heroSetupError}</div>}
          <label>
            {t('editor.startLocation')}
            <select
              value={heroSetupForm.default_location}
              onChange={(event) =>
                setHeroSetupForm((prev) => ({
                  ...prev,
                  default_location: event.target.value,
                }))
              }
              disabled={readOnly}
            >
              <option value="">{t('editor.createAtStart')}</option>
              {sortByTitle(locations.items, locale).map((location) => (
                <option key={location.id} value={location.id}>
                  {location.title}
                </option>
              ))}
            </select>
          </label>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={heroSetupForm.require_race}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({
                    ...prev,
                    require_race: event.target.checked,
                  }))
                }
                disabled={readOnly}
              />
              {t('editor.selectRaceAtStart')}
            </label>
            <label>
              {t('editor.defaultRace')}
              <select
                value={heroSetupForm.default_race}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({ ...prev, default_race: event.target.value }))
                }
                disabled={heroSetupForm.require_race || readOnly}
              >
                <option value="">{t('editor.notSet')}</option>
                {sortByTitle(races.items, locale).map((race) => (
                  <option key={race.id} value={race.id}>
                    {race.title}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={heroSetupForm.require_age}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({
                    ...prev,
                    require_age: event.target.checked,
                  }))
                }
                disabled={readOnly}
              />
              {t('editor.selectAgeAtStart')}
            </label>
            <label>
              {t('editor.defaultAge')}
              <input
                type="number"
                min="0"
                value={heroSetupForm.default_age}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({ ...prev, default_age: event.target.value }))
                }
                disabled={heroSetupForm.require_age || readOnly}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={heroSetupForm.require_body_power}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({
                    ...prev,
                    require_body_power: event.target.checked,
                  }))
                }
                disabled={readOnly}
              />
              {t('editor.selectBodyPowerAtStart')}
            </label>
            <label>
              {t('editor.defaultBodyPower')}
              <input
                type="number"
                min="0"
                value={heroSetupForm.default_body_power}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({ ...prev, default_body_power: event.target.value }))
                }
                disabled={heroSetupForm.require_body_power || readOnly}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={heroSetupForm.require_mind_power}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({
                    ...prev,
                    require_mind_power: event.target.checked,
                  }))
                }
                disabled={readOnly}
              />
              {t('editor.selectMindPowerAtStart')}
            </label>
            <label>
              {t('editor.defaultMindPower')}
              <input
                type="number"
                min="0"
                value={heroSetupForm.default_mind_power}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({ ...prev, default_mind_power: event.target.value }))
                }
                disabled={heroSetupForm.require_mind_power || readOnly}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              <input
                type="checkbox"
                checked={heroSetupForm.require_will_power}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({
                    ...prev,
                    require_will_power: event.target.checked,
                  }))
                }
                disabled={readOnly}
              />
              {t('editor.selectWillPowerAtStart')}
            </label>
            <label>
              {t('editor.defaultWillPower')}
              <input
                type="number"
                min="0"
                value={heroSetupForm.default_will_power}
                onChange={(event) =>
                  setHeroSetupForm((prev) => ({ ...prev, default_will_power: event.target.value }))
                }
                disabled={heroSetupForm.require_will_power || readOnly}
              />
            </label>
          </div>
          <div className="form-row">
            <div className="template-meta">{t('editor.knowledgeAtStart')}</div>
          </div>
          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={savingHeroSetup || readOnly}
            >
              {t('editor.saveHeroSetup')}
            </button>
          </div>
        </form>
      )}
    </>
  );
}

export default GeneralTab;
