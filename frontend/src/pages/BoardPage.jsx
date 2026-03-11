import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { DndContext, DragOverlay, closestCorners, PointerSensor, useSensor, useSensors, useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import Modal from '../components/Modal';
import TaskCard from '../components/TaskCard';
import styles from './BoardPage.module.css';

const STATUSES = [
  { id: 'todo', label: 'To Do', color: '#64748b' },
  { id: 'in_progress', label: 'In Progress', color: '#f59e0b' },
  { id: 'in_review', label: 'In Review', color: '#8b5cf6' },
  { id: 'done', label: 'Done', color: '#22c55e' },
];

const PRIORITIES = ['low', 'medium', 'high', 'urgent'];

export default function BoardPage() {
  const { projectId } = useParams();
  const { data: project } = useApi(() => api.getProject(projectId), [projectId]);
  const { data: tasks, refetch: refetchTasks } = useApi(() => api.getTasks({ project_id: projectId }), [projectId]);
  const { data: labels } = useApi(() => api.getLabels());
  const { data: epics } = useApi(() => api.getEpics({ project_id: projectId }), [projectId]);
  const { data: sprints } = useApi(() => api.getSprints({ project_id: projectId }), [projectId]);

  const [showTaskModal, setShowTaskModal] = useState(false);
  const [editTask, setEditTask] = useState(null);
  const [activeId, setActiveId] = useState(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const handleDragStart = (event) => {
    setActiveId(event.active.id);
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setActiveId(null);

    if (!over) return;

    const taskId = active.id;
    let newStatus = over.id;

    // Check if dropped on a column
    if (STATUSES.some(s => s.id === newStatus)) {
      const task = tasks.find(t => t.id === taskId);
      if (task && task.status !== newStatus) {
        await api.updateTask(taskId, { status: newStatus });
        refetchTasks();
      }
    } else {
      // Dropped on another task - get that task's status
      const overTask = tasks.find(t => t.id === over.id);
      if (overTask) {
        newStatus = overTask.status;
        const task = tasks.find(t => t.id === taskId);
        if (task && task.status !== newStatus) {
          await api.updateTask(taskId, { status: newStatus });
          refetchTasks();
        }
      }
    }
  };

  const handleCreateTask = async (data) => {
    await api.createTask({ ...data, project_id: parseInt(projectId) });
    refetchTasks();
    setShowTaskModal(false);
  };

  const handleUpdateTask = async (data) => {
    await api.updateTask(editTask.id, data);
    refetchTasks();
    setEditTask(null);
  };

  const handleDeleteTask = async (id) => {
    if (confirm('Delete this task?')) {
      await api.deleteTask(id);
      refetchTasks();
    }
  };

  const getTasksByStatus = (status) => {
    return tasks?.filter(t => t.status === status) || [];
  };

  const activeTask = tasks?.find(t => t.id === activeId);

  const [showNotes, setShowNotes] = useState(false);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <Link to="/projects" className={styles.back}>Projects</Link>
          <h1>{project?.name || 'Board'}</h1>
        </div>
        <div className={styles.headerActions}>
          {project?.notes && (
            <button
              className={styles.notesToggle}
              onClick={() => setShowNotes(!showNotes)}
            >
              {showNotes ? 'Hide Notes' : 'Show Notes'}
            </button>
          )}
          <button className={styles.createBtn} onClick={() => setShowTaskModal(true)}>
            + New Task
          </button>
        </div>
      </header>

      {showNotes && project?.notes && (
        <div className={styles.notesPanel}>
          <h3>Project Notes</h3>
          <div className={styles.notesContent}>
            {project.notes}
          </div>
        </div>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className={styles.board}>
          {STATUSES.map((status) => (
            <DroppableColumn key={status.id} status={status}>
              <SortableContext
                id={status.id}
                items={getTasksByStatus(status.id).map(t => t.id)}
                strategy={verticalListSortingStrategy}
              >
                {getTasksByStatus(status.id).map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onClick={() => setEditTask(task)}
                    onDelete={() => handleDeleteTask(task.id)}
                  />
                ))}
                {getTasksByStatus(status.id).length === 0 && (
                  <div className={styles.emptyColumn}>Drop tasks here</div>
                )}
              </SortableContext>
            </DroppableColumn>
          ))}
        </div>

        <DragOverlay>
          {activeTask ? (
            <TaskCard task={activeTask} isDragging />
          ) : null}
        </DragOverlay>
      </DndContext>

      {(showTaskModal || editTask) && (
        <TaskModal
          task={editTask}
          labels={labels || []}
          epics={epics || []}
          sprints={sprints || []}
          onClose={() => { setShowTaskModal(false); setEditTask(null); }}
          onSubmit={editTask ? handleUpdateTask : handleCreateTask}
          onAddComment={async (content) => {
            await api.addComment(editTask.id, { content });
            const updated = await api.getTask(editTask.id);
            setEditTask(updated);
          }}
          onLogTime={async (hours, description) => {
            await api.logTime(editTask.id, { hours, description });
            refetchTasks();
            const updated = await api.getTask(editTask.id);
            setEditTask(updated);
          }}
        />
      )}
    </div>
  );
}

function DroppableColumn({ status, children }) {
  const { setNodeRef, isOver } = useDroppable({ id: status.id });

  return (
    <div className={styles.column}>
      <div className={styles.columnHeader}>
        <div className={styles.statusDot} style={{ background: status.color }} />
        <span>{status.label}</span>
      </div>
      <div
        ref={setNodeRef}
        className={`${styles.tasks} ${isOver ? styles.tasksOver : ''}`}
        data-status={status.id}
      >
        {children}
      </div>
    </div>
  );
}

function TaskModal({ task, labels, epics, sprints, onClose, onSubmit, onAddComment, onLogTime }) {
  const [form, setForm] = useState({
    title: task?.title || '',
    description: task?.description || '',
    status: task?.status || 'todo',
    priority: task?.priority || 'medium',
    due_date: task?.due_date ? task.due_date.slice(0, 16) : '',
    estimated_hours: task?.estimated_hours || '',
    epic_id: task?.epic_id || '',
    sprint_id: task?.sprint_id || '',
    label_ids: task?.labels?.map(l => l.id) || [],
  });
  const [comment, setComment] = useState('');
  const [timeHours, setTimeHours] = useState('');
  const [timeDesc, setTimeDesc] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = {
      ...form,
      due_date: form.due_date || null,
      estimated_hours: form.estimated_hours ? parseFloat(form.estimated_hours) : null,
      epic_id: form.epic_id || null,
      sprint_id: form.sprint_id || null,
    };
    onSubmit(data);
  };

  const handleAddComment = () => {
    if (comment.trim()) {
      onAddComment(comment);
      setComment('');
    }
  };

  const handleLogTime = () => {
    if (timeHours) {
      onLogTime(parseFloat(timeHours), timeDesc);
      setTimeHours('');
      setTimeDesc('');
    }
  };

  return (
    <Modal onClose={onClose} title={task ? 'Edit Task' : 'New Task'} wide={!!task}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.formGrid}>
          <div className={styles.formMain}>
            <div className={styles.field}>
              <label>Title</label>
              <input
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
                autoFocus
              />
            </div>

            <div className={styles.field}>
              <label>Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={4}
              />
            </div>

            {task && (
              <>
                <div className={styles.field}>
                  <label>Comments</label>
                  <div className={styles.comments}>
                    {task.comments?.map((c) => (
                      <div key={c.id} className={styles.comment}>
                        <p>{c.content}</p>
                        <span>{new Date(c.created_at).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                  <div className={styles.addComment}>
                    <input
                      type="text"
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      placeholder="Add a comment..."
                    />
                    <button type="button" onClick={handleAddComment}>Add</button>
                  </div>
                </div>

                <div className={styles.field}>
                  <label>Log Time</label>
                  <div className={styles.timeLog}>
                    <input
                      type="number"
                      step="0.25"
                      value={timeHours}
                      onChange={(e) => setTimeHours(e.target.value)}
                      placeholder="Hours"
                    />
                    <input
                      type="text"
                      value={timeDesc}
                      onChange={(e) => setTimeDesc(e.target.value)}
                      placeholder="Description"
                    />
                    <button type="button" onClick={handleLogTime}>Log</button>
                  </div>
                  {task.logged_hours > 0 && (
                    <span className={styles.logged}>
                      {task.logged_hours}h logged
                      {task.estimated_hours && ` / ${task.estimated_hours}h estimated`}
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          <div className={styles.formSide}>
            <div className={styles.field}>
              <label>Status</label>
              <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="in_review">In Review</option>
                <option value="done">Done</option>
              </select>
            </div>

            <div className={styles.field}>
              <label>Priority</label>
              <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div className={styles.field}>
              <label>Due Date</label>
              <input
                type="datetime-local"
                value={form.due_date}
                onChange={(e) => setForm({ ...form, due_date: e.target.value })}
              />
            </div>

            <div className={styles.field}>
              <label>Estimated Hours</label>
              <input
                type="number"
                step="0.5"
                value={form.estimated_hours}
                onChange={(e) => setForm({ ...form, estimated_hours: e.target.value })}
              />
            </div>

            {epics.length > 0 && (
              <div className={styles.field}>
                <label>Epic</label>
                <select value={form.epic_id} onChange={(e) => setForm({ ...form, epic_id: e.target.value })}>
                  <option value="">None</option>
                  {epics.map((e) => (
                    <option key={e.id} value={e.id}>{e.name}</option>
                  ))}
                </select>
              </div>
            )}

            {sprints.length > 0 && (
              <div className={styles.field}>
                <label>Sprint</label>
                <select value={form.sprint_id} onChange={(e) => setForm({ ...form, sprint_id: e.target.value })}>
                  <option value="">Backlog</option>
                  {sprints.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
            )}

            {labels.length > 0 && (
              <div className={styles.field}>
                <label>Labels</label>
                <div className={styles.labelPicker}>
                  {labels.map((l) => (
                    <label key={l.id} className={styles.labelOption}>
                      <input
                        type="checkbox"
                        checked={form.label_ids.includes(l.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setForm({ ...form, label_ids: [...form.label_ids, l.id] });
                          } else {
                            setForm({ ...form, label_ids: form.label_ids.filter(id => id !== l.id) });
                          }
                        }}
                      />
                      <span className={styles.labelColor} style={{ background: l.color }} />
                      {l.name}
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className={styles.actions}>
          <button type="button" onClick={onClose} className={styles.cancelBtn}>Cancel</button>
          <button type="submit" className={styles.submitBtn}>{task ? 'Save' : 'Create'}</button>
        </div>
      </form>
    </Modal>
  );
}
