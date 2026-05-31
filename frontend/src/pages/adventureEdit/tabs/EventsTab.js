import React from 'react';

import { sortByTitle } from '../utils';

function EventsTab({ events, locations, readOnly, locale, t }) {
  return (
    <div className="editor-section split-panel">
      <div className="editor-list">
        {events.items.length === 0 && <p className="templates-empty">{t('editor.noEvents')}</p>}
        {events.items.map((item) => (
          <article className="template-card" key={item.id}>
            <h4>{item.title}</h4>
            <div className="template-meta">{t('editor.statusValue', { status: t(`status.${item.status}`) })}</div>
            <div className="template-meta">
              {t('editor.locationValue', {
                location: item.location
                  ? locations.items.find((loc) => loc.id === item.location)?.title || '—'
                  : t('editor.global'),
              })}
            </div>
            {item.trigger_hint && <p>{t('editor.triggerValue', { trigger: item.trigger_hint })}</p>}
            {item.state && <div className="template-meta">{t('editor.stateValue', { state: item.state })}</div>}
            {!readOnly && (
              <div className="template-actions">
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => events.startEdit(item)}
                >
                  {t('app.edit')}
                </button>
                <button className="link-button" type="button" onClick={() => events.remove(item.id)}>
                  {t('app.delete')}
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
      <form className="editor-form editor-panel" onSubmit={events.submit}>
        {events.error && <div className="error-message">{events.error}</div>}
        <label>
          {t('editor.name')}
          <input
            value={events.form.title}
            onChange={(event) => events.setForm((prev) => ({ ...prev, title: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.status')}
          <select
            value={events.form.status}
            onChange={(event) => events.setForm((prev) => ({ ...prev, status: event.target.value }))}
            disabled={readOnly}
          >
            <option value="inactive">{t('status.inactive')}</option>
            <option value="active">{t('status.active')}</option>
            <option value="resolved">{t('status.resolved')}</option>
          </select>
        </label>
        <label>
          {t('editor.location')}
          <select
            value={events.form.location}
            onChange={(event) => events.setForm((prev) => ({ ...prev, location: event.target.value }))}
            disabled={readOnly}
          >
            <option value="">{t('editor.global')}</option>
            {sortByTitle(locations.items, locale).map((location) => (
              <option key={location.id} value={location.id}>
                {location.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('editor.startTrigger')}
          <textarea
            rows="2"
            value={events.form.trigger_hint}
            onChange={(event) => events.setForm((prev) => ({ ...prev, trigger_hint: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <label>
          {t('editor.currentState')}
          <textarea
            rows="2"
            value={events.form.state}
            onChange={(event) => events.setForm((prev) => ({ ...prev, state: event.target.value }))}
            disabled={readOnly}
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit" disabled={events.saving || readOnly}>
            {t(events.editingId ? 'app.save' : 'app.add')}
          </button>
          {events.editingId && !readOnly && (
            <button className="secondary-button" type="button" onClick={events.resetForm}>
              {t('app.cancel')}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default EventsTab;
