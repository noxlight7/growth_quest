import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

function GmDashboardPage({ apiBaseUrl, authRequest, t }) {
  const { id } = useParams();
  const runId = Number(id);
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState('');
  const [savingSettings, setSavingSettings] = useState(false);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const response = await authRequest({
          method: 'get',
          url: `${apiBaseUrl}/api/adventures/runs/${runId}/gm/dashboard/`,
        });
        setDashboard(response.data);
      } catch (err) {
        setError(t('teacher.loadFailed'));
      }
    };
    fetchDashboard();
  }, [apiBaseUrl, authRequest, runId, t]);

  const handlePortfolioExport = async () => {
    try {
      const response = await authRequest({
        method: 'get',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/portfolio/export/`,
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `adventure_${runId}_portfolio.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(t('teacher.exportFailed'));
    }
  };

  const updateStorySettings = async (patch) => {
    if (!dashboard || savingSettings) return;
    const nextSettings = { ...(dashboard.story_settings || {}), ...patch };
    setDashboard((prev) => ({ ...prev, story_settings: nextSettings }));
    setSavingSettings(true);
    try {
      const response = await authRequest({
        method: 'put',
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/gm/dashboard/`,
        data: patch,
      });
      setDashboard((prev) => ({
        ...prev,
        story_settings: response.data.story_settings || nextSettings,
      }));
    } catch (err) {
      setError(t('teacher.settingsFailed'));
    } finally {
      setSavingSettings(false);
    }
  };

  if (error) {
    return <div className="error-message">{error}</div>;
  }
  if (!dashboard) {
    return <p className="templates-empty">{t('app.loading')}</p>;
  }

  return (
    <div className="teacher-dashboard">
      <div className="teacher-header">
        <div>
          <h2>{t('teacher.title')}</h2>
        </div>
        <button className="secondary-button" type="button" onClick={handlePortfolioExport}>
          {t('teacher.export')}
        </button>
      </div>

      <section className="teacher-grid">
        <div className="teacher-panel">
          <h3>{t('teacher.storySettings')}</h3>
          <p className="template-meta">{t('teacher.storySettingsNote')}</p>
          <label>
            {t('game.storyLocale')}
            <select
              value={dashboard.story_settings?.story_locale || 'en'}
              onChange={(event) => updateStorySettings({ story_locale: event.target.value })}
              disabled={savingSettings}
            >
              <option value="en">{t('locale.en')}</option>
              <option value="ru">{t('locale.ru')}</option>
              <option value="zh-CN">{t('locale.zh-CN')}</option>
            </select>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={dashboard.story_settings?.facilitator_enabled !== false}
              onChange={(event) =>
                updateStorySettings({ facilitator_enabled: event.target.checked })
              }
              disabled={savingSettings}
            />
            {t('teacher.gmEnabled')}
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={Boolean(dashboard.story_settings?.story_simple_language)}
              onChange={(event) =>
                updateStorySettings({ story_simple_language: event.target.checked })
              }
              disabled={savingSettings}
            />
            {t('game.simpleLanguage')}
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={Boolean(dashboard.story_settings?.story_reduced_text_length)}
              onChange={(event) =>
                updateStorySettings({ story_reduced_text_length: event.target.checked })
              }
              disabled={savingSettings}
            />
            {t('game.shortAnswers')}
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={Boolean(dashboard.story_settings?.growth_analysis_enabled)}
              onChange={(event) =>
                updateStorySettings({ growth_analysis_enabled: event.target.checked })
              }
              disabled={savingSettings}
            />
            {t('teacher.growthAnalysisEnabled')}
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={Boolean(dashboard.story_settings?.narrative_consequences_enabled)}
              onChange={(event) =>
                updateStorySettings({ narrative_consequences_enabled: event.target.checked })
              }
              disabled={savingSettings}
            />
            {t('teacher.narrativeConsequencesEnabled')}
          </label>
        </div>

        <div className="teacher-panel">
          <h3>{t('teacher.competencies')}</h3>
          {dashboard.competencies.length === 0 && (
            <p className="templates-empty">{t('teacher.noEvidence')}</p>
          )}
          {dashboard.competencies.map((row) => (
            <div key={row.competency}>
              <div className="competency-row">
                <span>{t(`competency.${row.competency}`)}</span>
                <strong>{t('teacher.observationCount', { count: row.count })}</strong>
              </div>
              <div className="template-meta">
                {t('teacher.averageMarker', {
                  score: Number(row.avg_score || 0).toFixed(1),
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="teacher-panel">
          <h3>{t('teacher.reflections')}</h3>
          <p>{t('teacher.responses', { count: dashboard.reflection_completion.responses })}</p>
          <p>
            {t('teacher.activePrompts', {
              count: dashboard.reflection_completion.active_prompts,
            })}
          </p>
          <p>{t('teacher.learners', { count: dashboard.reflection_completion.learners })}</p>
        </div>
      </section>

      <section className="teacher-panel">
        <h3>{t('teacher.latestEvidence')}</h3>
        {dashboard.latest_evidence.map((item) => (
          <article className="evidence-item" key={item.id}>
            <strong>{t(`competency.${item.competency}`)}</strong>
            <span>{item.marker}</span>
            <p>{item.rationale}</p>
          </article>
        ))}
      </section>

      <section className="teacher-panel">
        <h3>{t('teacher.openRepairOpportunities')}</h3>
        {(dashboard.open_repair_opportunities || []).length === 0 && (
          <p className="templates-empty">{t('teacher.noEvidence')}</p>
        )}
        {(dashboard.open_repair_opportunities || []).map((item) => (
          <article className="evidence-item" key={item.id}>
            <strong>{t(`competency.${item.competency}`)}</strong>
            <span>{t(`status.${item.status}`)}</span>
            <p>{item.title}</p>
            {item.suggested_action && <p>{item.suggested_action}</p>}
          </article>
        ))}
      </section>

      <section className="teacher-panel">
        <h3>{t('teacher.latestConsequences')}</h3>
        {(dashboard.latest_consequence_markers || []).length === 0 && (
          <p className="templates-empty">{t('teacher.noEvidence')}</p>
        )}
        {(dashboard.latest_consequence_markers || []).map((item) => (
          <article className="evidence-item" key={item.id}>
            <strong>{item.competency ? t(`competency.${item.competency}`) : t(`consequence.${item.kind}`)}</strong>
            <span>{t(`consequence.${item.kind}`)}</span>
            <p>{item.title}</p>
          </article>
        ))}
      </section>

      <section className="teacher-panel">
        <h3>{t('teacher.narrativeConsequences')}</h3>
        {(dashboard.latest_narrative_consequences || []).length === 0 && (
          <p className="templates-empty">{t('teacher.noEvidence')}</p>
        )}
        {(dashboard.latest_narrative_consequences || []).map((item) => (
          <article className="evidence-item" key={item.id}>
            <strong>{item.title}</strong>
            <span>{t('teacher.consequenceMeta', { status: t(`status.${item.status}`), importance: item.importance })}</span>
            <p>{item.summary}</p>
          </article>
        ))}
      </section>

      <section className="teacher-panel">
        <h3>{t('teacher.safetyIncidents')}</h3>
        {dashboard.safety_incidents.length === 0 && (
          <p className="templates-empty">{t('teacher.noSafety')}</p>
        )}
        {dashboard.safety_incidents.map((item) => (
          <article className="evidence-item" key={item.id}>
            <strong>{t(`risk.${item.risk_level}`)}</strong>
            <span>{item.categories.map((category) => t(`safety.${category}`)).join(', ')}</span>
            <p>{item.notes === 'Rule-based MVP review.' ? t('safety.ruleBasedReview') : item.notes}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

export default GmDashboardPage;
