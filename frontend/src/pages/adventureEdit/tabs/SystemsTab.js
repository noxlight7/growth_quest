import React from 'react';

import { formatTags } from '../utils';

function SystemsTab({ systems, readOnly, t }) {
  return (
    <div className="editor-section split-panel">
      <div className="editor-list">
        {systems.items.length === 0 && <p className="templates-empty">{t('editor.noSystems')}</p>}
        {systems.items.map((item) => (
          <article className="template-card" key={item.id}>
            <h4>{item.title}</h4>
            {item.description && <p>{item.description}</p>}
            <div className="template-meta">
              {t('editor.systemWeights', { body: item.w_body, mind: item.w_mind, will: item.w_will })}
            </div>
            {item.formula_hint && <div className="template-meta">{t('editor.formulaValue', { formula: item.formula_hint })}</div>}
            <div className="template-meta">{t('editor.tagsValue', { tags: formatTags(item.tags) || '—' })}</div>
            {!readOnly && (
              <div className="template-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => systems.startEdit(item)}
                >
                  {t('app.edit')}
                </button>
                <button className="link-button" type="button" onClick={() => systems.remove(item.id)}>
                  {t('app.delete')}
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
      <form className="editor-form editor-panel" onSubmit={systems.submit}>
        {systems.error && <div className="error-message">{systems.error}</div>}
        <label>
          {t('editor.name')}
          <input
            value={systems.form.title}
            onChange={(event) => systems.setForm((prev) => ({ ...prev, title: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.description')}
          <textarea
            rows="3"
            value={systems.form.description}
            onChange={(event) => systems.setForm((prev) => ({ ...prev, description: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <div className="form-row">
          <label>
            {t('editor.bodyWeight')}
            <input
              type="number"
              min="0"
              value={systems.form.w_body}
              onChange={(event) => systems.setForm((prev) => ({ ...prev, w_body: event.target.value }))}
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.mindWeight')}
            <input
              type="number"
              min="0"
              value={systems.form.w_mind}
              onChange={(event) => systems.setForm((prev) => ({ ...prev, w_mind: event.target.value }))}
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.willWeight')}
            <input
              type="number"
              min="0"
              value={systems.form.w_will}
              onChange={(event) => systems.setForm((prev) => ({ ...prev, w_will: event.target.value }))}
              disabled={readOnly}
            />
          </label>
        </div>
        <label>
          {t('editor.formula')}
          <textarea
            rows="2"
            value={systems.form.formula_hint}
            onChange={(event) =>
              systems.setForm((prev) => ({ ...prev, formula_hint: event.target.value }))
            }
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.tags')}
          <input
            value={systems.form.tags}
            onChange={(event) => systems.setForm((prev) => ({ ...prev, tags: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={systems.saving || readOnly}>
            {t(systems.editingId ? 'app.save' : 'app.add')}
          </button>
          {systems.editingId && !readOnly && (
            <button className="secondary-button" type="button" onClick={systems.resetForm}>
              {t('app.cancel')}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default SystemsTab;
