import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { format } from 'date-fns';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import Modal from '../components/Modal';
import styles from './SprintsPage.module.css';

export default function SprintsPage() {
  const { projectId } = useParams();
  const { data: project } = useApi(() => api.getProject(projectId), [projectId]);
  const { data: sprints, refetch } = useApi(() => api.getSprints({ project_id: projectId }), [projectId]);
  const { data: tasks } = useApi(() => api.getTasks({ project_id: projectId }), [projectId]);

  const [showModal, setShowModal] = useState(false);
  const [editSprint, setEditSprint] = useState(null);

  const handleCreate = async (data) => {
    await api.createSprint({ ...data, project_id: parseInt(projectId) });
    refetch();
    setShowModal(false);
  };

  const handleUpdate = async (data) => {
    await api.updateSprint(editSprint.id, data);
    refetch();
    setEditSprint(null);
  };

  const handleDelete = async (id) => {
    if (confirm('Delete this sprint?')) {
      await api.deleteSprint(id);
      refetch();
    }
  };

  const handleStart = async (id) => {
    await api.startSprint(id);
    refetch();
  };

  const handleComplete = async (id) => {
    await api.completeSprint(id);
    refetch();
  };

  const getSprintTasks = (sprintId) => {
    return tasks?.filter(t => t.sprint_id === sprintId) || [];
  };

  const getProgress = (sprintId) => {
    const sprintTasks = getSprintTasks(sprintId);
    if (sprintTasks.length === 0) return 0;
    const done = sprintTasks.filter(t => t.status === 'done').length;
    return Math.round((done / sprintTasks.length) * 100);
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <Link to="/projects" className={styles.back}>Projects</Link>
          <h1>Sprints - {project?.name}</h1>
        </div>
        <button className={styles.createBtn} onClick={() => setShowModal(true)}>
          + New Sprint
        </button>
      </header>

      <div className={styles.list}>
        {sprints?.map((sprint) => {
          const progress = getProgress(sprint.id);
          const sprintTasks = getSprintTasks(sprint.id);

          return (
            <div key={sprint.id} className={styles.card}>
              <div className={styles.cardHeader}>
                <div>
                  <span className={`${styles.status} ${styles[sprint.status]}`}>
                    {sprint.status}
                  </span>
                  <h3>{sprint.name}</h3>
                </div>
                <div className={styles.actions}>
                  {sprint.status === 'planned' && (
                    <button onClick={() => handleStart(sprint.id)} className={styles.startBtn}>
                      Start Sprint
                    </button>
                  )}
                  {sprint.status === 'active' && (
                    <button onClick={() => handleComplete(sprint.id)} className={styles.completeBtn}>
                      Complete
                    </button>
                  )}
                  <button onClick={() => setEditSprint(sprint)}>Edit</button>
                  <button onClick={() => handleDelete(sprint.id)}>Delete</button>
                </div>
              </div>

              {sprint.goal && <p className={styles.goal}>{sprint.goal}</p>}

              <div className={styles.dates}>
                {sprint.start_date && (
                  <span>Start: {format(new Date(sprint.start_date), 'MMM d, yyyy')}</span>
                )}
                {sprint.end_date && (
                  <span>End: {format(new Date(sprint.end_date), 'MMM d, yyyy')}</span>
                )}
              </div>

              <div className={styles.progress}>
                <div className={styles.progressBar}>
                  <div className={styles.progressFill} style={{ width: `${progress}%` }} />
                </div>
                <span>{progress}% complete ({sprintTasks.filter(t => t.status === 'done').length}/{sprintTasks.length} tasks)</span>
              </div>
            </div>
          );
        })}

        {sprints?.length === 0 && (
          <div className={styles.empty}>
            <p>No sprints yet. Create one to start organizing your work.</p>
          </div>
        )}
      </div>

      {(showModal || editSprint) && (
        <SprintModal
          sprint={editSprint}
          onClose={() => { setShowModal(false); setEditSprint(null); }}
          onSubmit={editSprint ? handleUpdate : handleCreate}
        />
      )}
    </div>
  );
}

function SprintModal({ sprint, onClose, onSubmit }) {
  const [form, setForm] = useState({
    name: sprint?.name || '',
    goal: sprint?.goal || '',
    start_date: sprint?.start_date ? sprint.start_date.slice(0, 10) : '',
    end_date: sprint?.end_date ? sprint.end_date.slice(0, 10) : '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...form,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
    });
  };

  return (
    <Modal onClose={onClose} title={sprint ? 'Edit Sprint' : 'New Sprint'}>
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
          <label>Goal</label>
          <textarea
            value={form.goal}
            onChange={(e) => setForm({ ...form, goal: e.target.value })}
            rows={3}
            placeholder="What do you want to achieve this sprint?"
          />
        </div>

        <div className={styles.row}>
          <div className={styles.field}>
            <label>Start Date</label>
            <input
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            />
          </div>
          <div className={styles.field}>
            <label>End Date</label>
            <input
              type="date"
              value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            />
          </div>
        </div>

        <div className={styles.modalActions}>
          <button type="button" onClick={onClose}>Cancel</button>
          <button type="submit" className={styles.submitBtn}>{sprint ? 'Save' : 'Create'}</button>
        </div>
      </form>
    </Modal>
  );
}
