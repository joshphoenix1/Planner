import { useState } from 'react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import Modal from '../components/Modal';
import styles from './GmailPage.module.css';

export default function GmailPage() {
  const { data: status, refetch: refetchStatus } = useApi(() => api.getGmailStatus());
  const { data: filters, refetch: refetchFilters } = useApi(() => api.getEmailFilters());
  const { data: emails, refetch: refetchEmails } = useApi(() => api.getEmails());
  const { data: projects } = useApi(() => api.getProjects());

  const [showFilterModal, setShowFilterModal] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.syncEmails();
      refetchEmails();
    } finally {
      setSyncing(false);
    }
  };

  const handleCreateFilter = async (data) => {
    await api.createEmailFilter(data);
    refetchFilters();
    setShowFilterModal(false);
  };

  const handleDeleteFilter = async (id) => {
    if (confirm('Delete this filter?')) {
      await api.deleteEmailFilter(id);
      refetchFilters();
    }
  };

  const handleDeleteEmail = async (e, emailId, blockSender = false) => {
    e.stopPropagation();
    const msg = blockSender
      ? 'Delete this email and block the sender from future syncs?'
      : 'Delete this email?';
    if (confirm(msg)) {
      const result = await api.deleteEmail(emailId, blockSender);
      if (result.blocked) {
        refetchFilters();
      }
      refetchEmails();
    }
  };

  if (!status?.configured) {
    return (
      <div className={styles.page}>
        <h1>Gmail Integration</h1>
        <div className={styles.setup}>
          <h2>Setup Required</h2>
          <p>Add your Gmail credentials to the .env file:</p>
          <pre>
GMAIL_EMAIL=your.email@gmail.com{'\n'}
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
          </pre>
          <h3>Get an App Password:</h3>
          <ol>
            <li>Enable 2FA at <a href="https://myaccount.google.com/security" target="_blank">Google Security</a></li>
            <li>Create App Password at <a href="https://myaccount.google.com/apppasswords" target="_blank">App Passwords</a></li>
            <li>Select "Mail" → "Other" → name it "Planner"</li>
            <li>Copy the 16-character password to .env</li>
          </ol>
          <p>Then restart the backend.</p>
        </div>
      </div>
    );
  }

  if (!status?.authenticated) {
    return (
      <div className={styles.page}>
        <h1>Gmail Integration</h1>
        <div className={styles.setup}>
          <h2>Connection Failed</h2>
          <p>Could not connect to Gmail: {status?.error}</p>
          <p>Check your GMAIL_EMAIL and GMAIL_APP_PASSWORD in .env</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Gmail</h1>
          <span className={styles.connected}>{status.email}</span>
        </div>
        <div className={styles.actions}>
          <button onClick={() => setShowFilterModal(true)} className={styles.filterBtn}>
            + Add Filter
          </button>
          <button onClick={handleSync} disabled={syncing} className={styles.syncBtn}>
            {syncing ? 'Syncing...' : 'Sync Emails'}
          </button>
        </div>
      </header>

      <div className={styles.content}>
        <aside className={styles.sidebar}>
          <h3>Email Filters</h3>
          <div className={styles.filters}>
            {filters?.map((filter) => (
              <div key={filter.id} className={styles.filterCard}>
                <div className={styles.filterHeader}>
                  <span className={styles.filterName}>{filter.name}</span>
                  <button onClick={() => handleDeleteFilter(filter.id)}>×</button>
                </div>
                {filter.keywords && (
                  <div className={styles.filterDetail}>
                    <label>Keywords:</label>
                    <span>{filter.keywords}</span>
                  </div>
                )}
                {filter.from_addresses && (
                  <div className={styles.filterDetail}>
                    <label>From:</label>
                    <span>{filter.from_addresses}</span>
                  </div>
                )}
                <div className={styles.filterProject}>
                  {filter.project_id
                    ? projects?.find(p => p.id === filter.project_id)?.name || 'Unknown project'
                    : 'All Projects (AI assigns)'}
                </div>
                {filter.blocked_addresses && (
                  <div className={styles.blockedAddresses}>
                    <label>Blocked:</label>
                    <span>{filter.blocked_addresses}</span>
                  </div>
                )}
              </div>
            ))}
            {(!filters || filters.length === 0) && (
              <p className={styles.empty}>No filters yet. Create one to start syncing emails.</p>
            )}
          </div>
        </aside>

        <main className={styles.emailList}>
          <h3>Synced Emails ({emails?.length || 0})</h3>
          <div className={styles.emails}>
            {emails?.map((email) => (
              <div
                key={email.id}
                className={styles.emailCard}
                onClick={() => setSelectedEmail(email)}
              >
                <div className={styles.emailHeader}>
                  <span className={styles.sender}>{email.sender}</span>
                  <div className={styles.emailActions}>
                    {email.project_id && (
                      <span className={styles.projectTag}>
                        {projects?.find(p => p.id === email.project_id)?.name}
                      </span>
                    )}
                    <button
                      className={styles.blockBtn}
                      onClick={(e) => handleDeleteEmail(e, email.id, true)}
                      title="Delete and block sender"
                    >
                      Block
                    </button>
                    <button
                      className={styles.deleteBtn}
                      onClick={(e) => handleDeleteEmail(e, email.id, false)}
                      title="Delete email"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className={styles.subject}>{email.subject}</div>
                <div className={styles.snippet}>{email.snippet}</div>
              </div>
            ))}
            {(!emails || emails.length === 0) && (
              <p className={styles.empty}>No emails synced yet. Create a filter and click Sync.</p>
            )}
          </div>
        </main>
      </div>

      {showFilterModal && (
        <FilterModal
          projects={projects || []}
          onClose={() => setShowFilterModal(false)}
          onSubmit={handleCreateFilter}
        />
      )}

      {selectedEmail && (
        <EmailModal
          email={selectedEmail}
          onClose={() => setSelectedEmail(null)}
        />
      )}
    </div>
  );
}

function FilterModal({ projects, onClose, onSubmit }) {
  const [form, setForm] = useState({
    name: '',
    project_id: '',  // empty = all projects
    keywords: '',
    from_addresses: '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...form,
      project_id: form.project_id ? parseInt(form.project_id) : null,
    });
  };

  return (
    <Modal onClose={onClose} title="Create Email Filter">
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label>Filter Name</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g., Client Emails"
            required
          />
        </div>

        <div className={styles.field}>
          <label>Project</label>
          <select
            value={form.project_id}
            onChange={(e) => setForm({ ...form, project_id: e.target.value })}
          >
            <option value="">All Projects (AI assigns)</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <small>AI will analyze email content and assign to the right project</small>
        </div>

        <div className={styles.field}>
          <label>Keywords (comma-separated)</label>
          <input
            type="text"
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
            placeholder="e.g., invoice, proposal, project-name"
          />
        </div>

        <div className={styles.field}>
          <label>From Addresses (comma-separated)</label>
          <input
            type="text"
            value={form.from_addresses}
            onChange={(e) => setForm({ ...form, from_addresses: e.target.value })}
            placeholder="e.g., client@example.com, boss@company.com"
          />
        </div>

        <div className={styles.modalActions}>
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className={styles.submitBtn}>Create Filter</button>
        </div>
      </form>
    </Modal>
  );
}

function EmailModal({ email, onClose }) {
  return (
    <Modal onClose={onClose} title={email.subject || '(No Subject)'} wide>
      <div className={styles.emailDetail}>
        <div className={styles.emailMeta}>
          <strong>From:</strong> {email.sender}
        </div>
        <div className={styles.emailBody}>
          {email.body || email.snippet}
        </div>
      </div>
    </Modal>
  );
}
