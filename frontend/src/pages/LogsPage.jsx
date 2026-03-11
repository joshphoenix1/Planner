import { useState } from 'react';
import { parseISO } from 'date-fns';
import { formatInTimeZone } from 'date-fns-tz';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import styles from './LogsPage.module.css';

const NZT = 'Pacific/Auckland';

function formatNZT(dateString, formatStr = 'MMM d, yyyy h:mm a') {
  try {
    const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
    return formatInTimeZone(date, NZT, formatStr) + ' NZT';
  } catch {
    return dateString;
  }
}

export default function LogsPage() {
  const { data: logs, refetch } = useApi(() => api.getLogs());
  const [filter, setFilter] = useState('all');
  const [analyzing, setAnalyzing] = useState(null);

  const filteredLogs = logs?.filter(log => {
    if (filter === 'all') return true;
    return log.status === filter;
  }) || [];

  const handleAnalyze = async (id) => {
    setAnalyzing(id);
    try {
      await api.analyzeError(id);
      refetch();
    } finally {
      setAnalyzing(null);
    }
  };

  const handleStatusChange = async (id, status) => {
    await api.updateErrorStatus(id, status);
    refetch();
  };

  const handleDelete = async (id) => {
    if (confirm('Delete this error log?')) {
      await api.deleteError(id);
      refetch();
    }
  };

  const handleClearAll = async () => {
    if (confirm('Clear all error logs?')) {
      await api.clearAllErrors();
      refetch();
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'new': return '#ef4444';
      case 'reviewing': return '#f59e0b';
      case 'fixed': return '#22c55e';
      case 'ignored': return '#6b7280';
      default: return '#6b7280';
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1>Error Logs</h1>
          <span className={styles.count}>{logs?.length || 0} errors</span>
        </div>
        <div className={styles.actions}>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className={styles.filter}>
            <option value="all">All</option>
            <option value="new">New</option>
            <option value="reviewing">Reviewing</option>
            <option value="fixed">Fixed</option>
            <option value="ignored">Ignored</option>
          </select>
          <button onClick={handleClearAll} className={styles.clearBtn}>Clear All</button>
        </div>
      </header>

      <div className={styles.logs}>
        {filteredLogs.map((log) => (
          <div key={log.id} className={styles.logCard}>
            <div className={styles.logHeader}>
              <div className={styles.logInfo}>
                <span className={styles.source}>{log.source}</span>
                <span className={styles.errorType}>{log.error_type}</span>
                <span
                  className={styles.status}
                  style={{ background: getStatusColor(log.status) }}
                >
                  {log.status}
                </span>
              </div>
              <div className={styles.logActions}>
                <button
                  onClick={() => handleAnalyze(log.id)}
                  disabled={analyzing === log.id}
                  className={styles.analyzeBtn}
                >
                  {analyzing === log.id ? 'Analyzing...' : 'AI Analyze'}
                </button>
                <select
                  value={log.status}
                  onChange={(e) => handleStatusChange(log.id, e.target.value)}
                  className={styles.statusSelect}
                >
                  <option value="new">New</option>
                  <option value="reviewing">Reviewing</option>
                  <option value="fixed">Fixed</option>
                  <option value="ignored">Ignored</option>
                </select>
                <button onClick={() => handleDelete(log.id)} className={styles.deleteBtn}>×</button>
              </div>
            </div>

            <div className={styles.message}>{log.message}</div>

            {log.stack_trace && (
              <details className={styles.stackTrace}>
                <summary>Stack Trace</summary>
                <pre>{log.stack_trace}</pre>
              </details>
            )}

            {log.ai_suggestion && (
              <div className={styles.aiSuggestion}>
                <div className={styles.aiLabel}>AI Suggestion:</div>
                <div className={styles.aiContent}>{log.ai_suggestion}</div>
              </div>
            )}

            <div className={styles.timestamp}>
              {formatNZT(log.created_at)}
            </div>
          </div>
        ))}

        {filteredLogs.length === 0 && (
          <div className={styles.empty}>No errors logged</div>
        )}
      </div>
    </div>
  );
}
