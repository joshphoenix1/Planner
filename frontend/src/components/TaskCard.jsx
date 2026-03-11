import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { isPast, isToday, parseISO } from 'date-fns';
import { formatInTimeZone, toZonedTime } from 'date-fns-tz';
import styles from './TaskCard.module.css';

const NZT = 'Pacific/Auckland';

function formatNZT(dateString, formatStr) {
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return formatInTimeZone(date, NZT, formatStr);
  } catch {
    return '';
  }
}

function parseNZT(dateString) {
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return toZonedTime(date, NZT);
  } catch {
    return null;
  }
}

const PRIORITY_COLORS = {
  low: '#64748b',
  medium: '#f59e0b',
  high: '#ef4444',
  urgent: '#dc2626',
};

export default function TaskCard({ task, onClick, onDelete, isDragging }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const dueDate = task.due_date ? parseNZT(task.due_date) : null;
  const isOverdue = dueDate && isPast(dueDate) && task.status !== 'done';
  const isDueToday = dueDate && isToday(dueDate);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={styles.card}
      onClick={onClick}
      {...attributes}
      {...listeners}
    >
      <div className={styles.header}>
        <span className={styles.priority} style={{ background: PRIORITY_COLORS[task.priority] }}>
          {task.priority}
        </span>
        {onDelete && (
          <button
            className={styles.delete}
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <h4 className={styles.title}>{task.title}</h4>

      {task.labels?.length > 0 && (
        <div className={styles.labels}>
          {task.labels.map((label) => (
            <span key={label.id} className={styles.label} style={{ background: label.color }}>
              {label.name}
            </span>
          ))}
        </div>
      )}

      <div className={styles.footer}>
        {dueDate && (
          <span className={`${styles.due} ${isOverdue ? styles.overdue : ''} ${isDueToday ? styles.today : ''}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            {formatNZT(task.due_date, 'MMM d')}
          </span>
        )}

        {task.logged_hours > 0 && (
          <span className={styles.time}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            {task.logged_hours}h
          </span>
        )}

        {task.comments?.length > 0 && (
          <span className={styles.comments}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
            {task.comments.length}
          </span>
        )}
      </div>
    </div>
  );
}
