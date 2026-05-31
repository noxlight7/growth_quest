import React from 'react';

import { formatTags } from '../utils';

function FactionsTab({ factions, readOnly, t }) {
  return (
    <div className="editor-section split-panel">
      <div className="editor-list">
        {factions.items.length === 0 && <p className="templates-empty">{t('editor.noFactions')}</p>}
        {factions.items.map((item) => (
          <article className="template-card" key={item.id}>
            <h4>{item.title}</h4>
            {item.description && <p>{item.description}</p>}
            <div className="template-meta">{t('editor.tagsValue', { tags: formatTags(item.tags) || '—' })}</div>
            {!readOnly && (
              <div className="template-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => factions.startEdit(item)}
                >
                  {t('app.edit')}
                </button>
                <button className="link-button" type="button" onClick={() => factions.remove(item.id)}>
                  {t('app.delete')}
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
      <form className="editor-form editor-panel" onSubmit={factions.submit}>
        {factions.error && <div className="error-message">{factions.error}</div>}
        <label>
          {t('editor.name')}
          <input
            value={factions.form.title}
            onChange={(event) => factions.setForm((prev) => ({ ...prev, title: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.description')}
          <textarea
            rows="3"
            value={factions.form.description}
            onChange={(event) =>
              factions.setForm((prev) => ({ ...prev, description: event.target.value }))
            }
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.tags')}
          <input
            value={factions.form.tags}
            onChange={(event) => factions.setForm((prev) => ({ ...prev, tags: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={factions.saving || readOnly}>
            {t(factions.editingId ? 'app.save' : 'app.add')}
          </button>
          {factions.editingId && !readOnly && (
            <button className="secondary-button" type="button" onClick={factions.resetForm}>
              {t('app.cancel')}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default FactionsTab;
