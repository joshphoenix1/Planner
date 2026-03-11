import { useState } from 'react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import styles from './SettingsPage.module.css';

export default function SettingsPage() {
  const { data: githubStatus, refetch: refetchGithub } = useApi(() => api.getGitHubStatus());
  const { data: gmailStatus, refetch: refetchGmail } = useApi(() => api.getGmailStatus());
  const { data: aiStatus, refetch: refetchAI } = useApi(() => api.getAIStatus());
  const { data: whatsappStatus, refetch: refetchWhatsApp } = useApi(() => api.getWhatsAppStatus());

  const [testing, setTesting] = useState(null);

  const testConnection = async (service, refetch) => {
    setTesting(service);
    await refetch();
    setTesting(null);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Settings</h1>
      </header>

      <div className={styles.cards}>
        {/* GitHub */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.service}>
              <svg viewBox="0 0 24 24" fill="currentColor" className={styles.icon}>
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
              </svg>
              <h2>GitHub</h2>
            </div>
            <span className={`${styles.status} ${githubStatus?.configured ? styles.connected : styles.disconnected}`}>
              {githubStatus?.configured ? 'Connected' : 'Not configured'}
            </span>
          </div>
          <div className={styles.cardBody}>
            <p>Import repositories as projects.</p>
            <div className={styles.config}>
              <code>GITHUB_TOKEN</code>
              <span className={githubStatus?.configured ? styles.set : styles.notSet}>
                {githubStatus?.configured ? 'Set' : 'Not set'}
              </span>
            </div>
          </div>
          <div className={styles.cardActions}>
            <button
              onClick={() => testConnection('github', refetchGithub)}
              disabled={testing === 'github'}
            >
              {testing === 'github' ? 'Testing...' : 'Test Connection'}
            </button>
            <a href="/github">Manage</a>
          </div>
        </div>

        {/* Gmail */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.service}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.icon}>
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                <polyline points="22,6 12,13 2,6" />
              </svg>
              <h2>Gmail</h2>
            </div>
            <span className={`${styles.status} ${gmailStatus?.authenticated ? styles.connected : styles.disconnected}`}>
              {gmailStatus?.authenticated ? 'Connected' : gmailStatus?.configured ? 'Auth failed' : 'Not configured'}
            </span>
          </div>
          <div className={styles.cardBody}>
            {gmailStatus?.email && <p className={styles.account}>{gmailStatus.email}</p>}
            <p>Sync emails to projects via filters.</p>
            <div className={styles.config}>
              <code>GMAIL_EMAIL</code>
              <span className={gmailStatus?.configured ? styles.set : styles.notSet}>
                {gmailStatus?.configured ? 'Set' : 'Not set'}
              </span>
            </div>
            <div className={styles.config}>
              <code>GMAIL_APP_PASSWORD</code>
              <span className={gmailStatus?.configured ? styles.set : styles.notSet}>
                {gmailStatus?.configured ? 'Set' : 'Not set'}
              </span>
            </div>
          </div>
          <div className={styles.cardActions}>
            <button
              onClick={() => testConnection('gmail', refetchGmail)}
              disabled={testing === 'gmail'}
            >
              {testing === 'gmail' ? 'Testing...' : 'Test Connection'}
            </button>
            <a href="/gmail">Manage Filters</a>
          </div>
        </div>

        {/* WhatsApp */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.service}>
              <svg viewBox="0 0 24 24" fill="currentColor" className={styles.icon}>
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
              </svg>
              <h2>WhatsApp</h2>
            </div>
            <span className={`${styles.status} ${whatsappStatus?.configured ? styles.connected : styles.disconnected}`}>
              {whatsappStatus?.configured ? 'Connected' : 'Not configured'}
            </span>
          </div>
          <div className={styles.cardBody}>
            <p>Receive messages via webhook, auto-create tasks.</p>
            <div className={styles.config}>
              <code>WHATSAPP_TOKEN</code>
              <span className={whatsappStatus?.configured ? styles.set : styles.notSet}>
                {whatsappStatus?.configured ? 'Set' : 'Not set'}
              </span>
            </div>
            <div className={styles.webhook}>
              <label>Webhook URL:</label>
              <code>http://18.191.204.13:8000/api/whatsapp/webhook</code>
            </div>
          </div>
          <div className={styles.cardActions}>
            <button
              onClick={() => testConnection('whatsapp', refetchWhatsApp)}
              disabled={testing === 'whatsapp'}
            >
              {testing === 'whatsapp' ? 'Testing...' : 'Test Connection'}
            </button>
            <a href="/whatsapp">Manage Groups</a>
          </div>
        </div>

        {/* AI / Claude */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div className={styles.service}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={styles.icon}>
                <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z" />
                <circle cx="7.5" cy="14.5" r="1.5" fill="currentColor" />
                <circle cx="16.5" cy="14.5" r="1.5" fill="currentColor" />
              </svg>
              <h2>AI Assistant</h2>
            </div>
            <span className={`${styles.status} ${aiStatus?.configured ? styles.connected : styles.disconnected}`}>
              {aiStatus?.configured ? 'Connected' : 'Not configured'}
            </span>
          </div>
          <div className={styles.cardBody}>
            <p>Claude-powered features: summaries, task parsing, planning.</p>
            {aiStatus?.model && <p className={styles.model}>Model: {aiStatus.model}</p>}
            <div className={styles.config}>
              <code>ANTHROPIC_API_KEY</code>
              <span className={aiStatus?.configured ? styles.set : styles.notSet}>
                {aiStatus?.configured ? 'Set' : 'Not set'}
              </span>
            </div>
          </div>
          <div className={styles.cardActions}>
            <button
              onClick={() => testConnection('ai', refetchAI)}
              disabled={testing === 'ai'}
            >
              {testing === 'ai' ? 'Testing...' : 'Test Connection'}
            </button>
            <a href="/ai">Use AI</a>
          </div>
        </div>
      </div>

      <div className={styles.envInfo}>
        <h3>Environment Configuration</h3>
        <p>All settings are configured via environment variables in:</p>
        <code>/home/ubuntu/planner/backend/.env</code>
        <p>After editing, restart the backend:</p>
        <code>pkill -f uvicorn && cd /home/ubuntu/planner/backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 &</code>
      </div>
    </div>
  );
}
