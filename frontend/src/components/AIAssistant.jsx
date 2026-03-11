import { useState } from 'react';
import { api } from '../api/client';
import styles from './AIAssistant.module.css';

export default function AIAssistant() {
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [collapsed, setCollapsed] = useState(false);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRecommendations();
      setRecommendations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.assistant}>
      <div className={styles.header}>
        <div className={styles.title}>
          <span className={styles.icon}>🤖</span>
          <h3>AI Assistant</h3>
        </div>
        <div className={styles.actions}>
          <button
            className={styles.refreshBtn}
            onClick={fetchRecommendations}
            disabled={loading}
          >
            {loading ? 'Analyzing...' : recommendations ? 'Refresh' : 'Get Recommendations'}
          </button>
          {recommendations && (
            <button
              className={styles.collapseBtn}
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? '▼' : '▲'}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className={styles.error}>Error: {error}</div>
      )}

      {recommendations && !collapsed && (
        <div className={styles.content}>
          <div className={styles.meta}>
            Analyzed {recommendations.context?.emails_analyzed || 0} emails, {' '}
            {recommendations.context?.tasks_analyzed || 0} tasks, {' '}
            {recommendations.context?.events_analyzed || 0} events
          </div>
          <div className={styles.recommendations}>
            {recommendations.recommendations || 'No recommendations available.'}
          </div>
        </div>
      )}

      {!recommendations && !loading && (
        <div className={styles.placeholder}>
          Click "Get Recommendations" to analyze your emails, tasks, and calendar for AI-powered priorities.
        </div>
      )}
    </div>
  );
}
