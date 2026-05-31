import React from 'react';

const COMPETENCIES = [
  'empathy',
  'cooperation',
  'self_regulation',
  'responsible_decision',
  'restorative_action',
  'help_seeking',
  'inclusion',
];

const INTERVENTION_KINDS = ['dilemma', 'repair', 'perspective', 'choice_cards'];

const objectiveId = (value) => {
  if (!value) return '';
  if (typeof value === 'object') return value.id || '';
  return value;
};

const getObjectiveTitle = (objectives, id, t) => {
  const normalizedId = Number(objectiveId(id));
  const objective = objectives.items.find((item) => item.id === normalizedId);
  return objective?.title || t('editor.objectiveNotSelected');
};

const payloadSummary = (payload) => {
  if (!payload || typeof payload !== 'object') return '—';
  if (Array.isArray(payload.cards)) return payload.cards.join(' / ');
  return payload.constraint || payload.hint || payload.description || JSON.stringify(payload);
};

function GrowthTab({ objectives, reflectionPrompts, interventions, readOnly, t }) {
  return (
    <div className="editor-section split-panel">
      <div className="editor-list">
        <section className="editor-subsection">
          <h3>{t('editor.growthObjectives')}</h3>
          {objectives.items.length === 0 && (
            <p className="templates-empty">{t('editor.noGrowthObjectives')}</p>
          )}
          {objectives.items.map((item) => (
            <article className="template-card" key={item.id}>
              <h4>{item.title}</h4>
              <div className="template-meta">
                {t('editor.objectiveMeta', {
                  competency: t(`competency.${item.competency}`),
                  weight: item.weight,
                  status: t(item.is_active ? 'status.active' : 'status.inactive'),
                })}
              </div>
              {item.description && <p>{item.description}</p>}
              {!readOnly && (
                <div className="template-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => objectives.startEdit(item)}
                  >
                    {t('app.edit')}
                  </button>
                  <button
                    className="link-button"
                    type="button"
                    onClick={() => objectives.remove(item.id)}
                  >
                    {t('app.delete')}
                  </button>
                </div>
              )}
            </article>
          ))}
        </section>

        <section className="editor-subsection">
          <h3>{t('editor.debriefPrompts')}</h3>
          {reflectionPrompts.items.length === 0 && (
            <p className="templates-empty">{t('editor.noDebriefPrompts')}</p>
          )}
          {reflectionPrompts.items.map((item) => (
            <article className="template-card" key={item.id}>
              <h4>{getObjectiveTitle(objectives, item.objective, t)}</h4>
              <div className="template-meta">
                {t(`trigger.${item.trigger_kind}`)} / {t(item.is_active ? 'status.active' : 'status.inactive')}
              </div>
              <p>{item.question}</p>
              {!readOnly && (
                <div className="template-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => reflectionPrompts.startEdit(item)}
                  >
                    {t('app.edit')}
                  </button>
                  <button
                    className="link-button"
                    type="button"
                    onClick={() => reflectionPrompts.remove(item.id)}
                  >
                    {t('app.delete')}
                  </button>
                </div>
              )}
            </article>
          ))}
        </section>

        <section className="editor-subsection">
          <h3>{t('editor.interventions')}</h3>
          {interventions.items.length === 0 && (
            <p className="templates-empty">{t('editor.noInterventions')}</p>
          )}
          {interventions.items.map((item) => (
            <article className="template-card" key={item.id}>
              <h4>{t(`intervention.${item.kind}`)}</h4>
              <div className="template-meta">
                {getObjectiveTitle(objectives, item.objective, t)} /{' '}
                {t(item.is_active ? 'status.active' : 'status.inactive')}
              </div>
              <p>{payloadSummary(item.payload)}</p>
              {!readOnly && (
                <div className="template-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => interventions.startEdit(item)}
                  >
                    {t('app.edit')}
                  </button>
                  <button
                    className="link-button"
                    type="button"
                    onClick={() => interventions.remove(item.id)}
                  >
                    {t('app.delete')}
                  </button>
                </div>
              )}
            </article>
          ))}
        </section>
      </div>

      <div className="editor-panel">
        <form className="editor-form" onSubmit={objectives.submit}>
          <h3>{t(objectives.editingId ? 'editor.editObjective' : 'editor.addObjective')}</h3>
          {objectives.error && <div className="error-message">{objectives.error}</div>}
          <label>
            {t('editor.code')}
            <input
              value={objectives.form.code}
              onChange={(event) =>
                objectives.setForm((prev) => ({ ...prev, code: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.name')}
            <input
              value={objectives.form.title}
              onChange={(event) =>
                objectives.setForm((prev) => ({ ...prev, title: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.competency')}
            <select
              value={objectives.form.competency}
              onChange={(event) =>
                objectives.setForm((prev) => ({ ...prev, competency: event.target.value }))
              }
              disabled={readOnly}
            >
              {COMPETENCIES.map((value) => (
                <option key={value} value={value}>
                  {t(`competency.${value}`)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('editor.weight')}
            <input
              type="number"
              value={objectives.form.weight}
              onChange={(event) =>
                objectives.setForm((prev) => ({ ...prev, weight: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.description')}
            <textarea
              rows="2"
              value={objectives.form.description}
              onChange={(event) =>
                objectives.setForm((prev) => ({ ...prev, description: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={objectives.form.is_active}
              onChange={(event) =>
                objectives.setForm((prev) => ({ ...prev, is_active: event.target.checked }))
              }
              disabled={readOnly}
            />
            {t('status.active')}
          </label>
          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={objectives.saving || readOnly}>
              {t(objectives.editingId ? 'app.save' : 'app.add')}
            </button>
            {objectives.editingId && !readOnly && (
              <button className="secondary-button" type="button" onClick={objectives.resetForm}>
                {t('app.cancel')}
              </button>
            )}
          </div>
        </form>

        <form className="editor-form" onSubmit={reflectionPrompts.submit}>
          <h3>{t(reflectionPrompts.editingId ? 'editor.editDebrief' : 'editor.addDebrief')}</h3>
          {reflectionPrompts.error && <div className="error-message">{reflectionPrompts.error}</div>}
          <label>
            {t('editor.objective')}
            <select
              value={reflectionPrompts.form.objective}
              onChange={(event) =>
                reflectionPrompts.setForm((prev) => ({ ...prev, objective: event.target.value }))
              }
              disabled={readOnly}
            >
              <option value="">{t('editor.selectObjective')}</option>
              {objectives.items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('editor.trigger')}
            <select
              value={reflectionPrompts.form.trigger_kind}
              onChange={(event) =>
                reflectionPrompts.setForm((prev) => ({ ...prev, trigger_kind: event.target.value }))
              }
              disabled={readOnly}
            >
              <option value="key_choice">{t('trigger.key_choice')}</option>
              <option value="user_turn">{t('trigger.user_turn')}</option>
              <option value="ai_turn">{t('trigger.ai_turn')}</option>
            </select>
          </label>
          <label>
            {t('editor.question')}
            <textarea
              rows="3"
              value={reflectionPrompts.form.question}
              onChange={(event) =>
                reflectionPrompts.setForm((prev) => ({ ...prev, question: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={reflectionPrompts.form.is_active}
              onChange={(event) =>
                reflectionPrompts.setForm((prev) => ({ ...prev, is_active: event.target.checked }))
              }
              disabled={readOnly}
            />
            {t('status.active')}
          </label>
          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={reflectionPrompts.saving || readOnly}
            >
              {t(reflectionPrompts.editingId ? 'app.save' : 'app.add')}
            </button>
            {reflectionPrompts.editingId && !readOnly && (
              <button
                className="secondary-button"
                type="button"
                onClick={reflectionPrompts.resetForm}
              >
                {t('app.cancel')}
              </button>
            )}
          </div>
        </form>

        <form className="editor-form" onSubmit={interventions.submit}>
          <h3>{t(interventions.editingId ? 'editor.editIntervention' : 'editor.addIntervention')}</h3>
          {interventions.error && <div className="error-message">{interventions.error}</div>}
          <label>
            {t('editor.objective')}
            <select
              value={interventions.form.objective}
              onChange={(event) =>
                interventions.setForm((prev) => ({ ...prev, objective: event.target.value }))
              }
              disabled={readOnly}
            >
              <option value="">{t('editor.selectObjective')}</option>
              {objectives.items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('editor.kind')}
            <select
              value={interventions.form.kind}
              onChange={(event) =>
                interventions.setForm((prev) => ({ ...prev, kind: event.target.value }))
              }
              disabled={readOnly}
            >
              {INTERVENTION_KINDS.map((kind) => (
                <option key={kind} value={kind}>
                  {t(`intervention.${kind}`)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('editor.constraint')}
            <textarea
              rows="3"
              value={interventions.form.constraint}
              onChange={(event) =>
                interventions.setForm((prev) => ({ ...prev, constraint: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label>
            {t('editor.choiceCards')}
            <textarea
              rows="4"
              value={interventions.form.cards}
              onChange={(event) =>
                interventions.setForm((prev) => ({ ...prev, cards: event.target.value }))
              }
              disabled={readOnly}
            />
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={interventions.form.is_active}
              onChange={(event) =>
                interventions.setForm((prev) => ({ ...prev, is_active: event.target.checked }))
              }
              disabled={readOnly}
            />
            {t('status.active')}
          </label>
          <div className="form-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={interventions.saving || readOnly}
            >
              {t(interventions.editingId ? 'app.save' : 'app.add')}
            </button>
            {interventions.editingId && !readOnly && (
              <button className="secondary-button" type="button" onClick={interventions.resetForm}>
                {t('app.cancel')}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

export default GrowthTab;
