import React from 'react';

import { formatTags } from '../utils';

function RacesTab({ races, readOnly, t }) {
  return (
    <div className="editor-section split-panel">
      <div className="editor-list">
        {races.items.length === 0 && <p className="templates-empty">{t('editor.noRaces')}</p>}
        {races.items.map((item) => (
          <article className="template-card" key={item.id}>
            <h4>{item.title}</h4>
            {item.description && <p>{item.description}</p>}
            <div className="template-meta">{t('editor.lifeSpanValue', { value: item.life_span ?? 100 })}</div>
            <div className="template-meta">{t('editor.tagsValue', { tags: formatTags(item.tags) || '—' })}</div>
            {!readOnly && (
              <div className="template-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => races.startEdit(item)}
                >
                  {t('app.edit')}
                </button>
                <button className="link-button" type="button" onClick={() => races.remove(item.id)}>
                  {t('app.delete')}
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
      <form className="editor-form editor-panel" onSubmit={races.submit}>
        {races.error && <div className="error-message">{races.error}</div>}
        <label>
          {t('editor.name')}
          <input
            value={races.form.title}
            onChange={(event) => races.setForm((prev) => ({ ...prev, title: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.description')}
          <textarea
            rows="3"
            value={races.form.description}
            onChange={(event) => races.setForm((prev) => ({ ...prev, description: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.lifeSpan')}
          <input
            type="number"
            min="0"
            value={races.form.life_span}
            onChange={(event) => races.setForm((prev) => ({ ...prev, life_span: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.tags')}
          <input
            value={races.form.tags}
            onChange={(event) => races.setForm((prev) => ({ ...prev, tags: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={races.saving || readOnly}>
            {t(races.editingId ? 'app.save' : 'app.add')}
          </button>
          {races.editingId && !readOnly && (
            <button className="secondary-button" type="button" onClick={races.resetForm}>
              {t('app.cancel')}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default RacesTab;
