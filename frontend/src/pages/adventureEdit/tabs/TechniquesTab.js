import React from 'react';

import { formatTags, sortByTitle } from '../utils';

function TechniquesTab({ techniques, systems, readOnly, locale, t }) {
  return (
    <div className="editor-section split-panel">
      <div className="editor-list">
        {techniques.items.length === 0 && <p className="templates-empty">{t('editor.noTechniques')}</p>}
        {techniques.items.map((item) => (
          <article className="template-card" key={item.id}>
            <h4>{item.title}</h4>
            {item.description && <p>{item.description}</p>}
            <div className="template-meta">
              {t('editor.systemValue', { system: systems.items.find((system) => system.id === item.system)?.title || '—' })}
            </div>
            <div className="template-meta">
              {t('editor.techniqueStats', { difficulty: item.difficulty, tier: item.tier ?? '—', level: item.required_system_level })}
            </div>
            <div className="template-meta">{t('editor.tagsValue', { tags: formatTags(item.tags) || '—' })}</div>
            {!readOnly && (
              <div className="template-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => techniques.startEdit(item)}
                >
                  {t('app.edit')}
                </button>
                <button
                  className="link-button"
                  type="button"
                  onClick={() => techniques.remove(item.id)}
                >
                  {t('app.delete')}
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
      <form className="editor-form editor-panel" onSubmit={techniques.submit}>
        {techniques.error && <div className="error-message">{techniques.error}</div>}
        <label>
          {t('editor.system')}
          <select
            value={techniques.form.system}
            onChange={(event) => techniques.setForm((prev) => ({ ...prev, system: event.target.value }))}
            disabled={readOnly}
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
          {t('editor.name')}
          <input
            value={techniques.form.title}
            onChange={(event) => techniques.setForm((prev) => ({ ...prev, title: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.description')}
          <textarea
            rows="3"
            value={techniques.form.description}
            onChange={(event) =>
              techniques.setForm((prev) => ({ ...prev, description: event.target.value }))
            }
            disabled={readOnly}
          />
        </label>
        <div className="form-row">
          <label>
            {t('editor.difficulty')}
            <input
              type="number"
              min="0"
              value={techniques.form.difficulty}
              onChange={(event) =>
                techniques.setForm((prev) => ({ ...prev, difficulty: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.rank')}
            <input
              type="number"
              min="0"
              value={techniques.form.tier}
              disabled={techniques.form.is_rankless || readOnly}
              onChange={(event) =>
                techniques.setForm((prev) => ({ ...prev, tier: event.target.value }))
              }
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={techniques.form.is_rankless}
              onChange={(event) =>
                techniques.setForm((prev) => ({
                  ...prev,
                  is_rankless: event.target.checked,
                  tier: event.target.checked ? '' : prev.tier,
                }))
              }
              disabled={readOnly}
            />
            {t('editor.ranklessTechnique')}
          </label>
          <label>
            {t('editor.requiredLevel')}
            <input
              type="number"
              min="0"
              value={techniques.form.required_system_level}
              onChange={(event) =>
                techniques.setForm((prev) => ({
                  ...prev,
                  required_system_level: event.target.value,
                }))
              }
              disabled={readOnly}
            />
          </label>
        </div>
        <label>
          {t('editor.tags')}
          <input
            value={techniques.form.tags}
            onChange={(event) => techniques.setForm((prev) => ({ ...prev, tags: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={techniques.saving || readOnly}>
            {t(techniques.editingId ? 'app.save' : 'app.add')}
          </button>
          {techniques.editingId && !readOnly && (
            <button className="secondary-button" type="button" onClick={techniques.resetForm}>
              {t('app.cancel')}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default TechniquesTab;
