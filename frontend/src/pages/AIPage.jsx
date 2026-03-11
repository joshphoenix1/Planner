import { useState } from 'react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import styles from './AIPage.module.css';

export default function AIPage() {
  const { data: status } = useApi(() => api.getAIStatus());
  const { data: projects } = useApi(() => api.getProjects());

  const [digest, setDigest] = useState(null);
  const [digestLoading, setDigestLoading] = useState(false);

  const [quickTask, setQuickTask] = useState('');
  const [quickTaskProject, setQuickTaskProject] = useState('');
  const [quickTaskResult, setQuickTaskResult] = useState(null);
  const [quickTaskLoading, setQuickTaskLoading] = useState(false);

  const [proposalUrl, setProposalUrl] = useState('');
  const [proposalProject, setProposalProject] = useState('');
  const [proposalResult, setProposalResult] = useState(null);
  const [proposalLoading, setProposalLoading] = useState(false);

  const handleGetDigest = async () => {
    setDigestLoading(true);
    try {
      const result = await api.getDailyDigest();
      setDigest(result);
    } catch (err) {
      setDigest({ error: err.message });
    } finally {
      setDigestLoading(false);
    }
  };

  const handleQuickTask = async (e) => {
    e.preventDefault();
    if (!quickTask.trim() || !quickTaskProject) return;

    setQuickTaskLoading(true);
    try {
      const result = await api.createTaskFromText(quickTask, parseInt(quickTaskProject));
      setQuickTaskResult(result);
      setQuickTask('');
    } catch (err) {
      setQuickTaskResult({ error: err.message });
    } finally {
      setQuickTaskLoading(false);
    }
  };

  const handleProposalImport = async (e) => {
    e.preventDefault();
    if (!proposalUrl.trim() || !proposalProject) return;

    setProposalLoading(true);
    try {
      const result = await api.createTasksFromUrl(proposalUrl, parseInt(proposalProject));
      setProposalResult(result);
      setProposalUrl('');
    } catch (err) {
      setProposalResult({ error: err.message });
    } finally {
      setProposalLoading(false);
    }
  };

  if (!status?.configured) {
    return (
      <div className={styles.page}>
        <h1>AI Assistant</h1>
        <div className={styles.setup}>
          <h2>Setup Required</h2>
          <p>Add your Anthropic API key to enable AI features:</p>
          <code>ANTHROPIC_API_KEY=sk-ant-...</code>
          <p>Add it to <code>/home/ubuntu/planner/backend/.env</code> and restart the server.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>AI Assistant</h1>
        <span className={styles.model}>Model: {status.model}</span>
      </header>

      <div className={styles.grid}>
        {/* Daily Digest */}
        <section className={styles.card}>
          <h2>Daily Digest</h2>
          <p className={styles.desc}>Get an AI-generated summary of your projects, tasks, and priorities.</p>
          <button
            onClick={handleGetDigest}
            disabled={digestLoading}
            className={styles.actionBtn}
          >
            {digestLoading ? 'Generating...' : 'Generate Digest'}
          </button>

          {digest && (
            <div className={styles.result}>
              {digest.error ? (
                <p className={styles.error}>{digest.error}</p>
              ) : (
                <>
                  <div className={styles.stats}>
                    <span>New tasks: {digest.stats?.new_tasks}</span>
                    <span>Due soon: {digest.stats?.due_soon}</span>
                    <span>In progress: {digest.stats?.in_progress}</span>
                  </div>
                  <div className={styles.digestContent}>
                    {digest.digest}
                  </div>
                </>
              )}
            </div>
          )}
        </section>

        {/* Quick Task Creation */}
        <section className={styles.card}>
          <h2>Quick Task</h2>
          <p className={styles.desc}>Describe a task naturally and AI will parse it into a structured task.</p>

          <form onSubmit={handleQuickTask} className={styles.quickForm}>
            <select
              value={quickTaskProject}
              onChange={(e) => setQuickTaskProject(e.target.value)}
              required
            >
              <option value="">Select project...</option>
              {projects?.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <textarea
              value={quickTask}
              onChange={(e) => setQuickTask(e.target.value)}
              placeholder="e.g., Fix the login bug ASAP, it's breaking production. Should take about 2 hours."
              rows={3}
            />
            <button type="submit" disabled={quickTaskLoading || !quickTask.trim()}>
              {quickTaskLoading ? 'Creating...' : 'Create Task'}
            </button>
          </form>

          {quickTaskResult && (
            <div className={styles.result}>
              {quickTaskResult.error ? (
                <p className={styles.error}>{quickTaskResult.error}</p>
              ) : (
                <div className={styles.taskResult}>
                  <strong>Created:</strong> {quickTaskResult.task?.title}
                  <div className={styles.taskMeta}>
                    Priority: {quickTaskResult.task?.priority} |
                    Est: {quickTaskResult.task?.estimated_hours || '?'}h
                    {quickTaskResult.task?.due_date && ` | Due: ${new Date(quickTaskResult.task.due_date).toLocaleDateString()}`}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Import from URL */}
        <section className={styles.card}>
          <h2>Import Tasks from URL</h2>
          <p className={styles.desc}>Paste a proposal or document URL and AI will extract all tasks.</p>

          <form onSubmit={handleProposalImport} className={styles.quickForm}>
            <select
              value={proposalProject}
              onChange={(e) => setProposalProject(e.target.value)}
              required
            >
              <option value="">Select project...</option>
              {projects?.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <input
              type="url"
              value={proposalUrl}
              onChange={(e) => setProposalUrl(e.target.value)}
              placeholder="https://docs.google.com/document/d/... or any URL"
              required
            />
            <button type="submit" disabled={proposalLoading || !proposalUrl.trim()}>
              {proposalLoading ? 'Importing...' : 'Import Tasks'}
            </button>
          </form>

          {proposalResult && (
            <div className={styles.result}>
              {proposalResult.error ? (
                <p className={styles.error}>{proposalResult.error}</p>
              ) : (
                <div className={styles.taskResult}>
                  <strong>Created {proposalResult.tasks_created} tasks:</strong>
                  <ul className={styles.taskList}>
                    {proposalResult.tasks?.map((t, i) => (
                      <li key={i}>
                        <span className={styles.taskTitle}>{t.title}</span>
                        <span className={styles.taskPriority}>{t.priority}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Features List */}
        <section className={styles.card}>
          <h2>AI Features</h2>
          <ul className={styles.featureList}>
            <li>
              <strong>Email Summarization</strong>
              <span>Click "Summarize" on any email in Gmail view</span>
            </li>
            <li>
              <strong>Sprint Planning</strong>
              <span>Go to an Epic and click "AI Suggest Tasks"</span>
            </li>
            <li>
              <strong>Smart Categorization</strong>
              <span>Auto-assign tasks to epics/sprints</span>
            </li>
            <li>
              <strong>WhatsApp Parsing</strong>
              <span>Intelligent task extraction from messages</span>
            </li>
          </ul>
        </section>

        {/* API Endpoints */}
        <section className={styles.card}>
          <h2>API Endpoints</h2>
          <div className={styles.endpoints}>
            <code>POST /api/ai/summarize-email/{'{email_id}'}</code>
            <code>POST /api/ai/parse-whatsapp</code>
            <code>POST /api/ai/plan-sprint/{'{epic_id}'}</code>
            <code>GET /api/ai/daily-digest</code>
            <code>POST /api/ai/categorize-task/{'{task_id}'}</code>
            <code>POST /api/ai/create-task-from-text</code>
          </div>
        </section>
      </div>
    </div>
  );
}
