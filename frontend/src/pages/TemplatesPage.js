import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

function TemplatesPage({ user, apiBaseUrl, authRequest, t }) {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [runs, setRuns] = useState([]);
  const [published, setPublished] = useState([]);
  const [showCreateAdventure, setShowCreateAdventure] = useState(false);
  const [createForm, setCreateForm] = useState({ title: "", description: "" });
  const [createError, setCreateError] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [importError, setImportError] = useState("");
  const [isImporting, setIsImporting] = useState(false);

  useEffect(() => {
    if (!user) {
      setTemplates([]);
      setPublished([]);
      return;
    }
    const fetchTemplates = async () => {
      try {
        const response = await authRequest({
          method: "get",
          url: `${apiBaseUrl}/api/adventures/templates/`,
        });
        setTemplates(response.data);
        const runsResponse = await authRequest({
          method: "get",
          url: `${apiBaseUrl}/api/adventures/runs/`,
        });
        setRuns(runsResponse.data);
        const publishedResponse = await authRequest({
          method: "get",
          url: `${apiBaseUrl}/api/adventures/moderation/published/`,
        });
        setPublished(publishedResponse.data);
      } catch (error) {
        setTemplates([]);
        setRuns([]);
        setPublished([]);
      }
    };
    fetchTemplates();
  }, [user, apiBaseUrl, authRequest]);

  const handleCreateChange = (event) => {
    const { name, value } = event.target;
    setCreateForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateAdventure = async (event) => {
    event.preventDefault();
    if (!createForm.title.trim()) {
      setCreateError(t("templates.titleRequired"));
      return;
    }
    setCreateError("");
    setIsCreating(true);
    try {
      const response = await authRequest({
        method: "post",
        url: `${apiBaseUrl}/api/adventures/templates/`,
        data: { title: createForm.title, description: createForm.description },
      });
      setTemplates((prev) => [response.data, ...prev]);
      setShowCreateAdventure(false);
      setCreateForm({ title: "", description: "" });
    } catch (error) {
      setCreateError(t("templates.createFailed"));
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteTemplate = async (templateId) => {
    if (!window.confirm(t("templates.deleteTemplateConfirm"))) return;
    try {
      await authRequest({
        method: "delete",
        url: `${apiBaseUrl}/api/adventures/templates/${templateId}/`,
      });
      setTemplates((prev) => prev.filter((item) => item.id !== templateId));
    } catch (error) {
      setImportError(t("templates.deleteFailed"));
    }
  };

  const handleDeleteRun = async (runId) => {
    if (!window.confirm(t("templates.deleteRunConfirm"))) return;
    try {
      await authRequest({
        method: "delete",
        url: `${apiBaseUrl}/api/adventures/runs/${runId}/`,
      });
      setRuns((prev) => prev.filter((item) => item.id !== runId));
    } catch (error) {
      setImportError(t("templates.deleteFailed"));
    }
  };

  const handleStartAdventure = async (templateId) => {
    try {
      const response = await authRequest({
        method: "post",
        url: `${apiBaseUrl}/api/adventures/templates/${templateId}/start/`,
      });
      const run = response.data;
      setRuns((prev) => [run, ...prev]);
      navigate(`/adventures/${run.id}/lobby`);
    } catch (error) {
      setImportError(t("templates.startFailed"));
    }
  };

  const handleImportAdventure = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setImportError("");
    setIsImporting(true);
    try {
      const text = await file.text();
      const payload = JSON.parse(text);
      const response = await authRequest({
        method: "post",
        url: `${apiBaseUrl}/api/adventures/templates/import/`,
        data: payload,
      });
      setTemplates((prev) => [response.data, ...prev]);
    } catch (error) {
      setImportError(t("templates.importFailed"));
    } finally {
      event.target.value = "";
      setIsImporting(false);
    }
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-inner">
        <div className="dashboard-top">
          <span className="dashboard-kick">Dashboard</span>
          <h1 className="dashboard-greeting">
            {t("templates.greeting", { username: user.username })}
          </h1>
        </div>

        {/* Section 1: Templates */}
        <section className="dash-section">
          <div className="dash-section-head">
            <h2 className="dash-section-title">
              {t("templates.yourTemplates")}
            </h2>
            <div className="dash-actions">
              <label className="dash-btn dash-btn-outline file-button">
                {t("templates.importJson")}
                <input
                  type="file"
                  accept="application/json"
                  onChange={handleImportAdventure}
                  disabled={isImporting}
                />
              </label>
              <button
                className="dash-btn dash-btn-primary"
                type="button"
                onClick={() => setShowCreateAdventure(true)}
              >
                {t("templates.createAdventure")}
              </button>
            </div>
          </div>

          {importError && <div className="l-error">{importError}</div>}

          {templates.length === 0 ? (
            <p className="dash-empty">{t("templates.noTemplates")}</p>
          ) : (
            <div className="dash-grid">
              {templates.map((template) => (
                <article className="dash-card" key={template.id}>
                  <h4 className="dash-card-title">{template.title}</h4>
                  {template.description && (
                    <p className="dash-card-desc">{template.description}</p>
                  )}
                  <div className="dash-card-actions">
                    <Link
                      className="dash-btn dash-btn-outline"
                      to={`/adventures/${template.id}/edit`}
                    >
                      {t("app.edit")}
                    </Link>
                    <button
                      className="dash-btn dash-btn-primary"
                      type="button"
                      onClick={() => handleStartAdventure(template.id)}
                    >
                      {t("app.start")}
                    </button>
                    <button
                      className="dash-link-btn"
                      type="button"
                      onClick={() => handleDeleteTemplate(template.id)}
                    >
                      {t("app.delete")}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {/* Section 2: Runs */}
        <section className="dash-section">
          <div className="dash-section-head">
            <h2 className="dash-section-title">{t("templates.startedRuns")}</h2>
          </div>
          {runs.length === 0 ? (
            <p className="dash-empty">{t("templates.noRuns")}</p>
          ) : (
            <div className="dash-grid">
              {runs.map((run) => (
                <article className="dash-card" key={run.id}>
                  <h4 className="dash-card-title">{run.title}</h4>
                  {run.description && (
                    <p className="dash-card-desc">{run.description}</p>
                  )}
                  <div className="dash-card-actions">
                    <Link
                      className="dash-btn dash-btn-outline"
                      to={`/adventures/runs/${run.id}/edit`}
                    >
                      {t("app.edit")}
                    </Link>
                    <Link
                      className="dash-btn dash-btn-outline"
                      to={`/adventures/${run.id}/lobby`}
                    >
                      {t("templates.lobby")}
                    </Link>
                    {run.started_at && (
                      <Link
                        className="dash-btn dash-btn-primary"
                        to={`/adventures/${run.id}/play`}
                      >
                        {t("app.play")}
                      </Link>
                    )}
                    <button
                      className="dash-link-btn"
                      type="button"
                      onClick={() => handleDeleteRun(run.id)}
                    >
                      {t("app.delete")}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {/* Section 3: Published */}
        <section className="dash-section">
          <div className="dash-section-head">
            <h2 className="dash-section-title">{t("templates.published")}</h2>
          </div>
          {published.length === 0 ? (
            <p className="dash-empty">{t("templates.noPublished")}</p>
          ) : (
            <div className="dash-grid">
              {published.map((entry) => {
                const isOwner = entry.author_username === user.username;
                return (
                  <article className="dash-card" key={entry.adventure_id}>
                    <h4 className="dash-card-title">{entry.title}</h4>
                    {entry.description && (
                      <p className="dash-card-desc">{entry.description}</p>
                    )}
                    <div className="dash-card-meta">
                      {t("templates.author", { author: entry.author_username })}
                    </div>
                    <div className="dash-card-actions">
                      <button
                        className="dash-btn dash-btn-primary"
                        type="button"
                        onClick={() => handleStartAdventure(entry.adventure_id)}
                      >
                        {t("app.start")}
                      </button>
                      {isOwner && (
                        <Link
                          className="dash-btn dash-btn-outline"
                          to={`/adventures/${entry.adventure_id}/edit`}
                        >
                          {t("app.open")}
                        </Link>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>

      {showCreateAdventure && (
        <div
          className="l-modal-overlay"
          onClick={() => setShowCreateAdventure(false)}
        >
          <div className="l-modal" onClick={(e) => e.stopPropagation()}>
            <button
              className="l-modal-close"
              onClick={() => setShowCreateAdventure(false)}
              aria-label={t("app.close")}
            >
              ×
            </button>
            <h3 className="l-modal-title">{t("templates.newAdventure")}</h3>
            <div className="l-modal-rule" />
            {createError && <div className="l-error">{createError}</div>}
            <form onSubmit={handleCreateAdventure}>
              <div className="l-form-group">
                <label className="l-label">{t("templates.title")}</label>
                <input
                  className="l-input"
                  name="title"
                  value={createForm.title}
                  onChange={handleCreateChange}
                  required
                />
              </div>
              <div className="l-form-group">
                <label className="l-label">{t("templates.description")}</label>
                <textarea
                  className="l-input"
                  name="description"
                  rows="3"
                  value={createForm.description}
                  onChange={handleCreateChange}
                />
              </div>
              <div className="dash-card-actions" style={{ marginTop: "1rem" }}>
                <button
                  className="dash-btn dash-btn-primary"
                  type="submit"
                  disabled={isCreating}
                >
                  {t("app.create")}
                </button>
                <button
                  className="dash-btn dash-btn-outline"
                  type="button"
                  onClick={() => setShowCreateAdventure(false)}
                >
                  {t("app.cancel")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default TemplatesPage;
