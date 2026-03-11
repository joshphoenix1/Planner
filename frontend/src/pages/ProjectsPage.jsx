import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import Modal from '../components/Modal';
import styles from './ProjectsPage.module.css';

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#22c55e', '#06b6d4', '#ef4444'];

export default function ProjectsPage() {
  const { data: projects, loading, refetch } = useApi(() => api.getProjects());
  const [showModal, setShowModal] = useState(false);
  const [editProject, setEditProject] = useState(null);

  const handleCreate = async (data) => {
    await api.createProject(data);
    refetch();
    setShowModal(false);
  };

  const handleUpdate = async (data) => {
    await api.updateProject(editProject.id, data);
    refetch();
    setEditProject(null);
  };

  const handleDelete = async (id) => {
    if (confirm('Delete this project and all its tasks?')) {
      await api.deleteProject(id);
      refetch();
    }
  };

  if (loading) return <div className={styles.loading}>Loading...</div>;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Projects</h1>
        <button className={styles.createBtn} onClick={() => setShowModal(true)}>
          + New Project
        </button>
      </header>

      <div className={styles.grid}>
        {projects?.map((project) => (
          <div key={project.id} className={styles.card}>
            <div className={styles.cardHeader}>
              <div className={styles.cardColor} style={{ background: project.color }} />
              <div className={styles.cardInfo}>
                <h3>{project.name}</h3>
                {project.github_repo && (
                  <a href={project.github_url} target="_blank" rel="noopener" className={styles.repo}>
                    {project.github_repo}
                  </a>
                )}
              </div>
              <div className={styles.cardActions}>
                <button onClick={() => setEditProject(project)} title="Edit">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </button>
                <button onClick={() => handleDelete(project.id)} title="Delete">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                  </svg>
                </button>
              </div>
            </div>

            {project.description && <p className={styles.desc}>{project.description}</p>}

            <div className={styles.stats}>
              <div>
                <span className={styles.statValue}>{project.task_count}</span>
                <span className={styles.statLabel}>Tasks</span>
              </div>
              <div>
                <span className={styles.statValue}>{project.completed_count}</span>
                <span className={styles.statLabel}>Done</span>
              </div>
              <div>
                <span className={styles.statValue}>{project.epic_count}</span>
                <span className={styles.statLabel}>Epics</span>
              </div>
              <div>
                <span className={styles.statValue}>{project.sprint_count}</span>
                <span className={styles.statLabel}>Sprints</span>
              </div>
            </div>

            <Link to={`/projects/${project.id}/board`} className={styles.openBtn}>
              Open Board
            </Link>
          </div>
        ))}

        {projects?.length === 0 && (
          <div className={styles.empty}>
            <p>No projects yet. Create one or import from GitHub.</p>
          </div>
        )}
      </div>

      {(showModal || editProject) && (
        <ProjectModal
          project={editProject}
          onClose={() => { setShowModal(false); setEditProject(null); }}
          onSubmit={editProject ? handleUpdate : handleCreate}
          colors={COLORS}
        />
      )}
    </div>
  );
}

function ProjectModal({ project, onClose, onSubmit, colors }) {
  const [form, setForm] = useState({
    name: project?.name || '',
    description: project?.description || '',
    github_url: project?.github_url || '',
    github_repo: project?.github_repo || '',
    color: project?.color || colors[0],
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <Modal onClose={onClose} title={project ? 'Edit Project' : 'New Project'}>
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
          <label>GitHub Repository (owner/repo)</label>
          <input
            type="text"
            value={form.github_repo}
            onChange={(e) => setForm({
              ...form,
              github_repo: e.target.value,
              github_url: e.target.value ? `https://github.com/${e.target.value}` : ''
            })}
            placeholder="e.g., username/my-project"
          />
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

        <div className={styles.actions}>
          <button type="button" onClick={onClose} className={styles.cancelBtn}>
            Cancel
          </button>
          <button type="submit" className={styles.submitBtn}>
            {project ? 'Save' : 'Create'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
