import React from 'react';

import { formatTags } from '../utils';

function LocationsTab({ locations, readOnly, t }) {
  return (
    <div className="editor-section split-panel">
      <div className="editor-list">
        {locations.items.length === 0 && <p className="templates-empty">{t('editor.noLocations')}</p>}
        {locations.items.map((item) => (
          <article className="template-card" key={item.id}>
            <h4>{item.title}</h4>
            {item.description && <p>{item.description}</p>}
            <div className="template-meta">
              {t('editor.locationGeometry', { x: item.x, y: item.y, width: item.width, height: item.height })}
            </div>
            <div className="template-meta">{t('editor.tagsValue', { tags: formatTags(item.tags) || '—' })}</div>
            {!readOnly && (
              <div className="template-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => locations.startEdit(item)}
                >
                  {t('app.edit')}
                </button>
                <button
                  className="link-button"
                  type="button"
                  onClick={() => locations.remove(item.id)}
                >
                  {t('app.delete')}
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
      <form className="editor-form editor-panel" onSubmit={locations.submit}>
        {locations.error && <div className="error-message">{locations.error}</div>}
        <label>
          {t('editor.name')}
          <input
            value={locations.form.title}
            onChange={(event) => locations.setForm((prev) => ({ ...prev, title: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.description')}
          <textarea
            rows="3"
            value={locations.form.description}
            onChange={(event) =>
              locations.setForm((prev) => ({ ...prev, description: event.target.value }))
            }
            disabled={readOnly}
          />
        </label>
        <div className="form-row">
          <label>
            X
            <input
              type="number"
              value={locations.form.x}
              onChange={(event) => locations.setForm((prev) => ({ ...prev, x: event.target.value }))}
              disabled={readOnly}
            />
          </label>
          <label>
            Y
            <input
              type="number"
              value={locations.form.y}
              onChange={(event) => locations.setForm((prev) => ({ ...prev, y: event.target.value }))}
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.width')}
            <input
              type="number"
              min="1"
              value={locations.form.width}
              onChange={(event) =>
                locations.setForm((prev) => ({ ...prev, width: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.height')}
            <input
              type="number"
              min="1"
              value={locations.form.height}
              onChange={(event) =>
                locations.setForm((prev) => ({ ...prev, height: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
        </div>
        <label>
          {t('editor.tags')}
          <input
            value={locations.form.tags}
            onChange={(event) => locations.setForm((prev) => ({ ...prev, tags: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <div className="form-actions">
          <button
            className="primary-button"
            type="submit"
            disabled={locations.saving || readOnly}
          >
            {t(locations.editingId ? 'app.save' : 'app.add')}
          </button>
          {locations.editingId && !readOnly && (
            <button className="secondary-button" type="button" onClick={locations.resetForm}>
              {t('app.cancel')}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default LocationsTab;
