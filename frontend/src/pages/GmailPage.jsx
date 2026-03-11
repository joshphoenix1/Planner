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
  const [editingFilter, setEditingFilter] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [search, setSearch] = useState('');
  const [sortOrder, setSortOrder] = useState('newest');

  const filteredEmails = (emails?.filter(email => {
    if (!search.trim()) return true;
    const term = search.toLowerCase();
    return (
      email.subject?.toLowerCase().includes(term) ||
      email.sender?.toLowerCase().includes(term) ||
      email.snippet?.toLowerCase().includes(term)
    );
  }) || []).sort((a, b) => {
    const dateA = new Date(a.received_at);
    const dateB = new Date(b.received_at);
    return sortOrder === 'newest' ? dateB - dateA : dateA - dateB;
  });

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
    if (editingFilter) {
      await api.updateEmailFilter(editingFilter.id, data);
    } else {
      await api.createEmailFilter(data);
    }
    refetchFilters();
    setShowFilterModal(false);
    setEditingFilter(null);
  };

  const handleEditFilter = (filter) => {
    setEditingFilter(filter);
    setShowFilterModal(true);
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

  const handleCreateProject = async (emailId) => {
    try {
      const result = await api.createProjectFromEmail(emailId);
      let msg = result.message;
      if (result.project?.github_url) {
        msg += `\n\nGitHub: ${result.project.github_url}`;
      }
      if (result.repo_path) {
        msg += `\nLocal: ${result.repo_path}`;
      }
      alert(msg);
      refetchFilters();
      refetchEmails();
      setSelectedEmail(null);
    } catch (err) {
      alert('Error creating project: ' + err.message);
    }
  };

  const handleAssignProject = async (emailId, projectId) => {
    try {
      await api.assignEmailToProject(emailId, projectId);
      refetchEmails();
    } catch (err) {
      alert('Error assigning project: ' + err.message);
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
                  <div className={styles.filterBtns}>
                    <button onClick={() => handleEditFilter(filter)} title="Edit">✎</button>
                    <button onClick={() => handleDeleteFilter(filter.id)} title="Delete">×</button>
                  </div>
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
          <div className={styles.emailListHeader}>
            <h3>Synced Emails ({filteredEmails.length}{search ? ` / ${emails?.length || 0}` : ''})</h3>
            <div className={styles.emailControls}>
              <select
                className={styles.sortSelect}
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
              </select>
              <input
                type="text"
                className={styles.searchInput}
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div className={styles.emails}>
            {filteredEmails.map((email) => (
              <div
                key={email.id}
                className={styles.emailCard}
                onClick={() => setSelectedEmail(email)}
              >
                <div className={styles.emailHeader}>
                  <span className={styles.sender}>{email.sender}</span>
                  <div className={styles.emailActions}>
                    {email.project_id ? (
                      <span className={styles.projectTag}>
                        {projects?.find(p => p.id === email.project_id)?.name}
                      </span>
                    ) : (
                      <select
                        className={styles.assignSelect}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => {
                          if (e.target.value) {
                            handleAssignProject(email.id, parseInt(e.target.value));
                            e.target.value = '';
                          }
                        }}
                        title="Assign to existing project"
                      >
                        <option value="">Assign...</option>
                        {projects?.map(p => (
                          <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                      </select>
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
            {filteredEmails.length === 0 && (
              <p className={styles.empty}>
                {search ? 'No emails match your search.' : 'No emails synced yet. Create a filter and click Sync.'}
              </p>
            )}
          </div>
        </main>
      </div>

      {showFilterModal && (
        <FilterModal
          projects={projects || []}
          filter={editingFilter}
          onClose={() => {
            setShowFilterModal(false);
            setEditingFilter(null);
          }}
          onSubmit={handleCreateFilter}
        />
      )}

      {selectedEmail && (
        <EmailModal
          email={selectedEmail}
          onClose={() => setSelectedEmail(null)}
          onCreateProject={handleCreateProject}
        />
      )}
    </div>
  );
}

function FilterModal({ projects, filter, onClose, onSubmit }) {
  const [form, setForm] = useState({
    name: filter?.name || '',
    project_id: filter?.project_id?.toString() || '',
    keywords: filter?.keywords || '',
    from_addresses: filter?.from_addresses || '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...form,
      project_id: form.project_id ? parseInt(form.project_id) : null,
    });
  };

  return (
    <Modal onClose={onClose} title={filter ? "Edit Email Filter" : "Create Email Filter"}>
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
          <button type="submit" className={styles.submitBtn}>{filter ? 'Save' : 'Create Filter'}</button>
        </div>
      </form>
    </Modal>
  );
}

function EmailModal({ email, onClose, onCreateProject }) {
  const [creating, setCreating] = useState(false);

  const handleCreateProject = async () => {
    setCreating(true);
    try {
      await onCreateProject(email.id);
    } finally {
      setCreating(false);
    }
  };

  return (
    <Modal onClose={onClose} title={email.subject || '(No Subject)'} wide>
      <div className={styles.emailDetail}>
        <div className={styles.emailMeta}>
          <strong>From:</strong> {email.sender}
        </div>
        <div className={styles.emailBody}>
          {email.body || email.snippet}
        </div>
        <div className={styles.emailActions2}>
          <button
            onClick={handleCreateProject}
            disabled={creating}
            className={styles.createProjectBtn}
          >
            {creating ? 'Creating...' : 'Create Project from Email'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
