import React from 'react';

import { formatTags, sortByTitle } from '../utils';

function CharactersTab({
  characters,
  races,
  locations,
  systems,
  techniques,
  activeCharacterId,
  setActiveCharacterId,
  activeCharacter,
  activeCharacterSystems,
  activeCharacterTechniques,
  availableSystemsForTechniques,
  characterSystems,
  characterTechniques,
  readOnly,
  locale,
  t,
}) {
  return (
    <div className="editor-section split-panel characters-layout">
      <div className="editor-list characters-list">
        {characters.items.length === 0 && <p className="templates-empty">{t('editor.noCharacters')}</p>}
        {characters.items.map((item) => (
          <article className="template-card" key={item.id}>
            <h4>{item.title}</h4>
            {item.description && <p>{item.description}</p>}
            <div className="template-meta">
              {t('editor.characterRole', {
                role: t(item.is_player ? 'editor.player' : 'editor.npc'),
                party: t(item.in_party ? 'editor.inParty' : 'editor.outsideParty'),
              })}
            </div>
            <div className="template-meta">
              {t('editor.characterStats', { body: item.body_power, mind: item.mind_power, will: item.will_power })}
            </div>
            <div className="template-meta">{t('editor.tagsValue', { tags: formatTags(item.tags) || '—' })}</div>
            <div className="template-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  characters.startEdit(item);
                  setActiveCharacterId(item.id);
                }}
              >
                {t(readOnly ? 'app.open' : 'app.edit')}
              </button>
              {!readOnly && (
                <button
                  className="link-button"
                  type="button"
                  onClick={() => {
                    if (activeCharacterId === item.id) {
                      setActiveCharacterId(null);
                    }
                    characters.remove(item.id);
                  }}
                >
                  {t('app.delete')}
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
      <div className="editor-stack editor-panel characters-panel">
        <form className="editor-form" onSubmit={characters.submit}>
          {characters.error && <div className="error-message">{characters.error}</div>}
          <label>
            {t('editor.characterName')}
            <input
              value={characters.form.title}
              onChange={(event) =>
                characters.setForm((prev) => ({ ...prev, title: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.description')}
          <textarea
            rows="3"
            value={characters.form.description}
            onChange={(event) =>
              characters.setForm((prev) => ({ ...prev, description: event.target.value }))
            }
            disabled={readOnly}
          />
          </label>
          <div className="form-row">
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={characters.form.is_player}
                onChange={(event) =>
                  characters.setForm((prev) => ({
                    ...prev,
                    is_player: event.target.checked,
                    in_party: event.target.checked ? true : prev.in_party,
                  }))
                }
                disabled={readOnly}
              />
              {t('editor.playerCharacter')}
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={characters.form.in_party}
                onChange={(event) =>
                  characters.setForm((prev) => ({
                    ...prev,
                    in_party: event.target.checked,
                  }))
                }
                disabled={readOnly}
              />
              {t('editor.inParty')}
            </label>
          </div>
          <div className="form-row">
            <label>
              {t('editor.age')}
            <input
              type="number"
              min="0"
              value={characters.form.age}
              onChange={(event) =>
                characters.setForm((prev) => ({ ...prev, age: event.target.value }))
              }
              disabled={readOnly}
            />
            </label>
            <label>
              {t('editor.bodyPower')}
            <input
              type="number"
              min="0"
              value={characters.form.body_power}
              onChange={(event) =>
                characters.setForm((prev) => ({ ...prev, body_power: event.target.value }))
              }
              disabled={readOnly}
            />
            </label>
            <label>
              {t('editor.mindPower')}
            <input
              type="number"
              min="0"
              value={characters.form.mind_power}
              onChange={(event) =>
                characters.setForm((prev) => ({ ...prev, mind_power: event.target.value }))
              }
              disabled={readOnly}
            />
            </label>
            <label>
              {t('editor.willPower')}
            <input
              type="number"
              min="0"
              value={characters.form.will_power}
              onChange={(event) =>
                characters.setForm((prev) => ({ ...prev, will_power: event.target.value }))
              }
              disabled={readOnly}
            />
            </label>
          </div>
          <div className="form-row">
            <label>
              {t('editor.bodyProgress')}
            <input
              type="number"
              min="0"
              max="100"
              value={characters.form.body_power_progress}
              onChange={(event) =>
                characters.setForm((prev) => ({
                  ...prev,
                  body_power_progress: event.target.value,
                }))
              }
              disabled={readOnly}
            />
            </label>
            <label>
              {t('editor.mindProgress')}
            <input
              type="number"
              min="0"
              max="100"
              value={characters.form.mind_power_progress}
              onChange={(event) =>
                characters.setForm((prev) => ({
                  ...prev,
                  mind_power_progress: event.target.value,
                }))
              }
              disabled={readOnly}
            />
            </label>
            <label>
              {t('editor.willProgress')}
            <input
              type="number"
              min="0"
              max="100"
              value={characters.form.will_power_progress}
              onChange={(event) =>
                characters.setForm((prev) => ({
                  ...prev,
                  will_power_progress: event.target.value,
                }))
              }
              disabled={readOnly}
            />
            </label>
          </div>
          <div className="form-row">
            <label>
              {t('editor.race')}
              <select
                value={characters.form.race}
                onChange={(event) =>
                  characters.setForm((prev) => ({ ...prev, race: event.target.value }))
                }
                disabled={readOnly}
              >
                <option value="">{t('editor.notSelected')}</option>
                {sortByTitle(races.items, locale).map((race) => (
                  <option key={race.id} value={race.id}>
                    {race.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('editor.location')}
              <select
                value={characters.form.location}
                onChange={(event) =>
                  characters.setForm((prev) => ({ ...prev, location: event.target.value }))
                }
                disabled={readOnly}
              >
                <option value="">{t('editor.notSelected')}</option>
                {sortByTitle(locations.items, locale).map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.title}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            {t('editor.tags')}
          <input
            value={characters.form.tags}
            onChange={(event) =>
              characters.setForm((prev) => ({ ...prev, tags: event.target.value }))
            }
            disabled={readOnly}
          />
          </label>
          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={characters.saving || readOnly}
            >
              {t(characters.editingId ? 'app.save' : 'app.add')}
            </button>
            {characters.editingId && !readOnly && (
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  characters.resetForm();
                  setActiveCharacterId(null);
                }}
              >
                {t('app.cancel')}
              </button>
            )}
          </div>
        </form>
        <div className="editor-subsection">
          <h3>{t('editor.sectionForCharacter', { section: t('editor.systemKnowledge'), character: activeCharacter?.title ? `: ${activeCharacter.title}` : '' })}</h3>
          <div className="editor-list">
            {!activeCharacterId && (
              <p className="templates-empty">{t('editor.selectCharacterForKnowledge')}</p>
            )}
            {activeCharacterId && activeCharacterSystems.length === 0 && (
              <p className="templates-empty">{t('editor.noEntries')}</p>
            )}
            {activeCharacterSystems.map((item) => (
              <article className="template-card" key={item.id}>
                <h4>{characters.items.find((char) => char.id === item.character)?.title || '—'}</h4>
                <div className="template-meta">
                  {t('editor.systemValue', { system: systems.items.find((system) => system.id === item.system)?.title || '—' })}
                </div>
                <div className="template-meta">
                  {t('editor.levelProgress', { level: item.level, progress: item.progress_percent ?? 0 })}
                </div>
                {item.notes && <p>{item.notes}</p>}
                {!readOnly && (
                  <div className="template-actions">
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => {
                        characterSystems.startEdit(item);
                        setActiveCharacterId(item.character);
                      }}
                    >
                      {t('app.edit')}
                    </button>
                    <button
                      className="link-button"
                      type="button"
                      onClick={() => characterSystems.remove(item.id)}
                    >
                      {t('app.delete')}
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
          <form
            className="editor-form"
            onSubmit={(event) => {
              if (!activeCharacterId) {
                event.preventDefault();
                return;
              }
              characterSystems.submit(event);
            }}
          >
            {characterSystems.error && <div className="error-message">{characterSystems.error}</div>}
            <label>
              {t('editor.system')}
              <select
                value={characterSystems.form.system}
                onChange={(event) =>
                  characterSystems.setForm((prev) => ({
                    ...prev,
                    system: event.target.value,
                  }))
                }
                disabled={!activeCharacterId || readOnly}
              >
                <option value="">{t('editor.selectSystem')}</option>
                {sortByTitle(systems.items, locale).map((system) => (
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
                value={characterSystems.form.level}
                onChange={(event) =>
                  characterSystems.setForm((prev) => ({
                    ...prev,
                    level: event.target.value,
                  }))
                }
                disabled={!activeCharacterId || readOnly}
              />
            </label>
            <label>
              {t('editor.progressPercent')}
              <input
                type="number"
                min="0"
                max="100"
                value={characterSystems.form.progress_percent}
                onChange={(event) =>
                  characterSystems.setForm((prev) => ({
                    ...prev,
                    progress_percent: event.target.value,
                  }))
                }
                disabled={!activeCharacterId || readOnly}
              />
            </label>
            <label>
              {t('editor.notes')}
              <textarea
                rows="2"
                value={characterSystems.form.notes}
                onChange={(event) =>
                  characterSystems.setForm((prev) => ({
                    ...prev,
                    notes: event.target.value,
                  }))
                }
                disabled={!activeCharacterId || readOnly}
              />
            </label>
            <div className="form-actions">
              <button
                className="primary-button"
                type="submit"
                disabled={characterSystems.saving || !activeCharacterId || readOnly}
              >
                {t(characterSystems.editingId ? 'app.save' : 'app.add')}
              </button>
              {characterSystems.editingId && !readOnly && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={characterSystems.resetForm}
                >
                  {t('app.cancel')}
                </button>
              )}
            </div>
          </form>
        </div>
        <div className="editor-subsection">
          <h3>{t('editor.sectionForCharacter', { section: t('editor.learnedTechniques'), character: activeCharacter?.title ? `: ${activeCharacter.title}` : '' })}</h3>
          <div className="editor-list">
            {!activeCharacterId && (
              <p className="templates-empty">{t('editor.selectCharacterForTechniques')}</p>
            )}
            {activeCharacterId && activeCharacterTechniques.length === 0 && (
              <p className="templates-empty">{t('editor.noEntries')}</p>
            )}
            {activeCharacterTechniques.map((item) => (
              <article className="template-card" key={item.id}>
                <h4>{characters.items.find((char) => char.id === item.character)?.title || '—'}</h4>
                <div className="template-meta">
                  {t('editor.techniqueValue', { technique: techniques.items.find((technique) => technique.id === item.technique)?.title || '—' })}
                </div>
                {item.notes && <p>{item.notes}</p>}
                {!readOnly && (
                  <div className="template-actions">
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => {
                        characterTechniques.startEdit(item);
                        setActiveCharacterId(item.character);
                      }}
                    >
                      {t('app.edit')}
                    </button>
                    <button
                      className="link-button"
                      type="button"
                      onClick={() => characterTechniques.remove(item.id)}
                    >
                      {t('app.delete')}
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
          <form
            className="editor-form"
            onSubmit={(event) => {
              if (!activeCharacterId) {
                event.preventDefault();
                return;
              }
              characterTechniques.submit(event);
            }}
          >
            {characterTechniques.error && (
              <div className="error-message">{characterTechniques.error}</div>
            )}
            <label>
              {t('editor.system')}
              <select
                value={characterTechniques.form.system}
                onChange={(event) =>
                  characterTechniques.setForm((prev) => ({
                    ...prev,
                    system: event.target.value,
                    technique: '',
                  }))
                }
                disabled={!activeCharacterId || readOnly}
              >
                <option value="">{t('editor.selectSystem')}</option>
                {sortByTitle(availableSystemsForTechniques, locale).map((system) => (
                  <option key={system.id} value={system.id}>
                    {system.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('editor.technique')}
              <select
                value={characterTechniques.form.technique}
                onChange={(event) =>
                  characterTechniques.setForm((prev) => ({
                    ...prev,
                    technique: event.target.value,
                  }))
                }
                disabled={!activeCharacterId || !characterTechniques.form.system || readOnly}
              >
                <option value="">{t('editor.selectTechnique')}</option>
                {sortByTitle(
                  techniques.items.filter((technique) =>
                    characterTechniques.form.system
                      ? technique.system === Number(characterTechniques.form.system)
                      : false
                  ),
                  locale
                ).map((technique) => (
                  <option key={technique.id} value={technique.id}>
                    {technique.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t('editor.notes')}
              <textarea
                rows="2"
                value={characterTechniques.form.notes}
                onChange={(event) =>
                  characterTechniques.setForm((prev) => ({
                    ...prev,
                    notes: event.target.value,
                  }))
                }
                disabled={!activeCharacterId || readOnly}
              />
            </label>
            <div className="form-actions">
              <button
                className="primary-button"
                type="submit"
                disabled={characterTechniques.saving || !activeCharacterId || readOnly}
              >
                {t(characterTechniques.editingId ? 'app.save' : 'app.add')}
              </button>
              {characterTechniques.editingId && !readOnly && (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={characterTechniques.resetForm}
                >
                  {t('app.cancel')}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default CharactersTab;
