import { useState } from 'react';
import { format } from 'date-fns';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import Modal from '../components/Modal';
import styles from './WhatsAppPage.module.css';

export default function WhatsAppPage() {
  const { data: status } = useApi(() => api.getWhatsAppStatus());
  const { data: groups, refetch: refetchGroups } = useApi(() => api.getWhatsAppGroups());
  const { data: messages, refetch: refetchMessages } = useApi(() => api.getWhatsAppMessages());
  const { data: projects } = useApi(() => api.getProjects());

  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showMessageModal, setShowMessageModal] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState(null);

  const handleCreateGroup = async (data) => {
    await api.createWhatsAppGroup(data);
    refetchGroups();
    setShowGroupModal(false);
  };

  const handleDeleteGroup = async (id) => {
    if (confirm('Remove this group mapping?')) {
      await api.deleteWhatsAppGroup(id);
      refetchGroups();
    }
  };

  const getGroupMessages = (groupId) => {
    return messages?.filter(m => m.group_mapping_id === groupId) || [];
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>WhatsApp Integration</h1>
        <div className={styles.actions}>
          <button onClick={() => setShowGroupModal(true)} className={styles.addBtn}>
            + Add Group
          </button>
          <button onClick={() => setShowMessageModal(true)} className={styles.testBtn}>
            Test Message
          </button>
        </div>
      </header>

      <div className={styles.info}>
        <h3>How it works</h3>
        <ol>
          <li>Map WhatsApp groups to your projects below</li>
          <li>Set up a webhook to receive messages (see setup below)</li>
          <li>Messages starting with <code>TASK:</code> or <code>TODO:</code> auto-create tasks</li>
          <li>Messages starting with <code>NOTE:</code> are saved as notes</li>
        </ol>

        <div className={styles.webhook}>
          <strong>Webhook URL:</strong>
          <code>http://18.191.204.13:8000/api/whatsapp/webhook</code>
        </div>
      </div>

      <div className={styles.content}>
        <section className={styles.groupsSection}>
          <h3>Mapped Groups ({groups?.length || 0})</h3>
          <div className={styles.groups}>
            {groups?.map((group) => {
              const groupMessages = getGroupMessages(group.id);
              const project = projects?.find(p => p.id === group.project_id);

              return (
                <div key={group.id} className={styles.groupCard}>
                  <div className={styles.groupHeader}>
                    <div>
                      <h4>{group.group_name}</h4>
                      <span className={styles.groupId}>ID: {group.group_id}</span>
                    </div>
                    <button onClick={() => handleDeleteGroup(group.id)} className={styles.deleteBtn}>
                      ×
                    </button>
                  </div>

                  <div className={styles.groupProject}>
                    <span className={styles.projectBadge} style={{ background: project?.color }}>
                      {project?.name || 'Unknown'}
                    </span>
                  </div>

                  {group.keywords && (
                    <div className={styles.keywords}>
                      <label>Keywords:</label> {group.keywords}
                    </div>
                  )}

                  <div className={styles.groupStats}>
                    <span>{groupMessages.length} messages</span>
                    <span className={group.auto_create_tasks ? styles.enabled : styles.disabled}>
                      {group.auto_create_tasks ? 'Auto-tasks ON' : 'Auto-tasks OFF'}
                    </span>
                  </div>

                  {groupMessages.length > 0 && (
                    <div className={styles.recentMessages}>
                      <strong>Recent:</strong>
                      {groupMessages.slice(0, 3).map((msg) => (
                        <div key={msg.id} className={styles.messagePreview}>
                          <span className={styles.msgType}>{msg.message_type}</span>
                          {msg.content?.substring(0, 50)}...
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}

            {(!groups || groups.length === 0) && (
              <p className={styles.empty}>No groups mapped yet. Add a group to get started.</p>
            )}
          </div>
        </section>

        <section className={styles.messagesSection}>
          <h3>All Messages ({messages?.length || 0})</h3>
          <div className={styles.messages}>
            {messages?.map((msg) => {
              const group = groups?.find(g => g.id === msg.group_mapping_id);
              return (
                <div key={msg.id} className={`${styles.message} ${styles[msg.message_type]}`}>
                  <div className={styles.messageHeader}>
                    <span className={styles.msgType}>{msg.message_type}</span>
                    <span className={styles.sender}>{msg.sender}</span>
                    <span className={styles.groupName}>{group?.group_name}</span>
                    {msg.received_at && (
                      <span className={styles.time}>
                        {format(new Date(msg.received_at), 'MMM d, h:mm a')}
                      </span>
                    )}
                  </div>
                  <div className={styles.messageContent}>{msg.content}</div>
                </div>
              );
            })}

            {(!messages || messages.length === 0) && (
              <p className={styles.empty}>No messages yet.</p>
            )}
          </div>
        </section>
      </div>

      {showGroupModal && (
        <GroupModal
          projects={projects || []}
          onClose={() => setShowGroupModal(false)}
          onSubmit={handleCreateGroup}
        />
      )}

      {showMessageModal && (
        <TestMessageModal
          groups={groups || []}
          onClose={() => setShowMessageModal(false)}
          onSubmit={async (data) => {
            await fetch('/api/whatsapp/messages', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data)
            });
            refetchMessages();
            setShowMessageModal(false);
          }}
        />
      )}
    </div>
  );
}

function GroupModal({ projects, onClose, onSubmit }) {
  const [form, setForm] = useState({
    group_id: '',
    group_name: '',
    project_id: projects[0]?.id || '',
    keywords: '',
    auto_create_tasks: true,
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...form,
      project_id: parseInt(form.project_id),
    });
  };

  return (
    <Modal onClose={onClose} title="Add WhatsApp Group">
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label>Group Name</label>
          <input
            type="text"
            value={form.group_name}
            onChange={(e) => setForm({ ...form, group_name: e.target.value })}
            placeholder="e.g., Project Alpha Team"
            required
          />
        </div>

        <div className={styles.field}>
          <label>WhatsApp Group ID</label>
          <input
            type="text"
            value={form.group_id}
            onChange={(e) => setForm({ ...form, group_id: e.target.value })}
            placeholder="e.g., 120363XXX@g.us"
            required
          />
          <small>Get this from your WhatsApp Business API or webhook logs</small>
        </div>

        <div className={styles.field}>
          <label>Project</label>
          <select
            value={form.project_id}
            onChange={(e) => setForm({ ...form, project_id: e.target.value })}
            required
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label>Keywords (optional, comma-separated)</label>
          <input
            type="text"
            value={form.keywords}
            onChange={(e) => setForm({ ...form, keywords: e.target.value })}
            placeholder="Filter messages containing these keywords"
          />
        </div>

        <div className={styles.checkbox}>
          <label>
            <input
              type="checkbox"
              checked={form.auto_create_tasks}
              onChange={(e) => setForm({ ...form, auto_create_tasks: e.target.checked })}
            />
            Auto-create tasks from TASK: messages
          </label>
        </div>

        <div className={styles.modalActions}>
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className={styles.submitBtn}>Add Group</button>
        </div>
      </form>
    </Modal>
  );
}

function TestMessageModal({ groups, onClose, onSubmit }) {
  const [form, setForm] = useState({
    group_mapping_id: groups[0]?.id || '',
    sender: 'Test User',
    content: '',
    message_type: 'text',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...form,
      group_mapping_id: parseInt(form.group_mapping_id),
    });
  };

  return (
    <Modal onClose={onClose} title="Test Message">
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label>Group</label>
          <select
            value={form.group_mapping_id}
            onChange={(e) => setForm({ ...form, group_mapping_id: e.target.value })}
            required
          >
            {groups.map((g) => (
              <option key={g.id} value={g.id}>{g.group_name}</option>
            ))}
          </select>
        </div>

        <div className={styles.field}>
          <label>Sender</label>
          <input
            type="text"
            value={form.sender}
            onChange={(e) => setForm({ ...form, sender: e.target.value })}
          />
        </div>

        <div className={styles.field}>
          <label>Message</label>
          <textarea
            value={form.content}
            onChange={(e) => setForm({ ...form, content: e.target.value })}
            rows={3}
            placeholder="Try: TASK: Review the proposal"
            required
          />
        </div>

        <div className={styles.modalActions}>
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className={styles.submitBtn}>Send Test</button>
        </div>
      </form>
    </Modal>
  );
}
