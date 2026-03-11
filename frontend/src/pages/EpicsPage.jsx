import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import Modal from '../components/Modal';
import styles from './EpicsPage.module.css';

const COLORS = ['#8b5cf6', '#6366f1', '#ec4899', '#f59e0b', '#22c55e', '#06b6d4', '#ef4444'];

export default function EpicsPage() {
  const { projectId } = useParams();
  const { data: project } = useApi(() => api.getProject(projectId), [projectId]);
  const { data: epics, refetch } = useApi(() => api.getEpics({ project_id: projectId }), [projectId]);
  const { data: tasks } = useApi(() => api.getTasks({ project_id: projectId }), [projectId]);

  const [showModal, setShowModal] = useState(false);
  const [editEpic, setEditEpic] = useState(null);

  const handleCreate = async (data) => {
    await api.createEpic({ ...data, project_id: parseInt(projectId) });
    refetch();
    setShowModal(false);
  };

  const handleUpdate = async (data) => {
    await api.updateEpic(editEpic.id, data);
    refetch();
    setEditEpic(null);
  };

  const handleDelete = async (id) => {
    if (confirm('Delete this epic? Tasks will be unassigned.')) {
      await api.deleteEpic(id);
      refetch();
    }
  };

  const getEpicTasks = (epicId) => {
    return tasks?.filter(t => t.epic_id === epicId) || [];
  };

  const getProgress = (epicId) => {
    const epicTasks = getEpicTasks(epicId);
    if (epicTasks.length === 0) return 0;
    const done = epicTasks.filter(t => t.status === 'done').length;
    return Math.round((done / epicTasks.length) * 100);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <Link to="/projects" className={styles.back}>Projects</Link>
          <h1>Epics - {project?.name}</h1>
        </div>
        <button className={styles.createBtn} onClick={() => setShowModal(true)}>
          + New Epic
        </button>
      </header>

      <div className={styles.grid}>
        {epics?.map((epic) => {
          const progress = getProgress(epic.id);
          const epicTasks = getEpicTasks(epic.id);

          return (
            <div key={epic.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <div className={styles.colorBar} style={{ background: epic.color }} />
                <div className={styles.cardInfo}>
                  <span className={`${styles.status} ${styles[epic.status]}`}>
                    {epic.status.replace('_', ' ')}
                  </span>
                  <h3>{epic.name}</h3>
                </div>
                <div className={styles.actions}>
                  <button onClick={() => setEditEpic(epic)}>Edit</button>
                  <button onClick={() => handleDelete(epic.id)}>Delete</button>
                </div>
              </div>

              {epic.description && <p className={styles.desc}>{epic.description}</p>}

              <div className={styles.progress}>
                <div className={styles.progressBar}>
                  <div className={styles.progressFill} style={{ width: `${progress}%`, background: epic.color }} />
                </div>
                <span>{progress}% ({epicTasks.filter(t => t.status === 'done').length}/{epicTasks.length} tasks)</span>
              </div>
            </div>
          );
        })}

        {epics?.length === 0 && (
          <div className={styles.empty}>
            <p>No epics yet. Create epics to group related tasks.</p>
          </div>
        )}
      </div>

      {(showModal || editEpic) && (
        <EpicModal
          epic={editEpic}
          colors={COLORS}
          onClose={() => { setShowModal(false); setEditEpic(null); }}
          onSubmit={editEpic ? handleUpdate : handleCreate}
        />
      )}
    </div>
  );
}

function EpicModal({ epic, colors, onClose, onSubmit }) {
  const [form, setForm] = useState({
    name: epic?.name || '',
    description: epic?.description || '',
    color: epic?.color || colors[0],
    status: epic?.status || 'open',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <Modal onClose={onClose} title={epic ? 'Edit Epic' : 'New Epic'}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label>Name</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
            autoFocus
          />
        </div>

        <div className={styles.field}>
          <label>Description</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={3}
          />
        </div>

        <div className={styles.field}>
          <label>Status</label>
          <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
          </select>
        </div>

        <div className={styles.field}>
          <label>Color</label>
          <div className={styles.colors}>
            {colors.map((c) => (
              <button
                key={c}
                type="button"
                className={`${styles.colorBtn} ${form.color === c ? styles.selected : ''}`}
                style={{ background: c }}
                onClick={() => setForm({ ...form, color: c })}
              />
            ))}
          </div>
        </div>

        <div className={styles.modalActions}>
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className={styles.submitBtn}>{epic ? 'Save' : 'Create'}</button>
        </div>
      </form>
    </Modal>
  );
}
