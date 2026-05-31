import React from 'react';

import { formatTags } from '../utils';

function OtherInfoTab({ otherInfo, readOnly, t }) {
  return (
    <div className="editor-section split-panel">
      <div className="editor-list">
        {otherInfo.items.length === 0 && <p className="templates-empty">{t('editor.noEntries')}</p>}
        {otherInfo.items.map((item) => (
          <article className="template-card" key={item.id}>
            <h4>{item.title}</h4>
            {item.category && <div className="template-meta">{t('editor.categoryValue', { category: item.category })}</div>}
            {item.description && <p>{item.description}</p>}
            <div className="template-meta">{t('editor.tagsValue', { tags: formatTags(item.tags) || '—' })}</div>
            {!readOnly && (
              <div className="template-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => otherInfo.startEdit(item)}
                >
                  {t('app.edit')}
                </button>
                <button className="link-button" type="button" onClick={() => otherInfo.remove(item.id)}>
                  {t('app.delete')}
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
      <form className="editor-form editor-panel" onSubmit={otherInfo.submit}>
        {otherInfo.error && <div className="error-message">{otherInfo.error}</div>}
        <label>
          {t('editor.category')}
          <input
            value={otherInfo.form.category}
            onChange={(event) => otherInfo.setForm((prev) => ({ ...prev, category: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.heading')}
          <input
            value={otherInfo.form.title}
            onChange={(event) => otherInfo.setForm((prev) => ({ ...prev, title: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.description')}
          <textarea
            rows="3"
            value={otherInfo.form.description}
            onChange={(event) =>
              otherInfo.setForm((prev) => ({ ...prev, description: event.target.value }))
            }
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.tags')}
          <input
            value={otherInfo.form.tags}
            onChange={(event) => otherInfo.setForm((prev) => ({ ...prev, tags: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={otherInfo.saving || readOnly}>
            {t(otherInfo.editingId ? 'app.save' : 'app.add')}
          </button>
          {otherInfo.editingId && !readOnly && (
            <button className="secondary-button" type="button" onClick={otherInfo.resetForm}>
              {t('app.cancel')}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default OtherInfoTab;
