import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import styles from './HealthDashboard.module.css';

export default function HealthDashboard() {
  const { data, loading, error } = useApi(() => api.getDashboard(), { refreshInterval: 30000 });

  if (loading && !data) return null;
  if (error) return null;

  const integrations = data?.integrations || {};

  return (
    <div className={styles.dashboard}>
      <div className={styles.stats}>
        <StatCard
          label="Tasks"
          value={data?.tasks?.total || 0}
          sub={`${data?.tasks?.in_progress || 0} in progress`}
          color="blue"
        />
        <StatCard
          label="Overdue"
          value={data?.tasks?.overdue || 0}
          sub="past due date"
          color={data?.tasks?.overdue > 0 ? "red" : "green"}
        />
        <StatCard
          label="Due This Week"
          value={data?.tasks?.due_this_week || 0}
          sub="upcoming"
          color={data?.tasks?.due_this_week > 5 ? "yellow" : "blue"}
        />
        <StatCard
          label="Projects"
          value={data?.projects || 0}
          sub={`${data?.epics || 0} epics`}
          color="purple"
        />
        <StatCard
          label="Active Sprints"
          value={data?.sprints?.active || 0}
          sub="running"
          color="blue"
        />
        <StatCard
          label="Emails"
          value={data?.emails?.total || 0}
          sub={`${data?.emails?.today || 0} today`}
          color="blue"
        />
        <StatCard
          label="Calendar"
          value={data?.calendar?.upcoming || 0}
          sub="upcoming events"
          color="blue"
        />
        <StatCard
          label="Errors"
          value={data?.errors?.new || 0}
          sub={`${data?.errors?.total || 0} total`}
          color={data?.errors?.new > 0 ? "red" : "green"}
        />
      </div>

      <div className={styles.integrations}>
        <IntegrationStatus
          name="Gmail"
          configured={integrations.gmail?.configured}
          connected={integrations.gmail?.connected}
        />
        <IntegrationStatus
          name="GitHub"
          configured={integrations.github?.configured}
          connected={integrations.github?.configured}
        />
        <IntegrationStatus
          name="AI"
          configured={integrations.ai?.configured}
          connected={integrations.ai?.configured}
        />
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, color }) {
  return (
    <div className={`${styles.stat} ${styles[color]}`}>
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
      <div className={styles.statSub}>{sub}</div>
    </div>
  );
}

function IntegrationStatus({ name, configured, connected }) {
  const status = !configured ? 'off' : connected ? 'on' : 'warning';
  const label = !configured ? 'Not configured' : connected ? 'Connected' : 'Configured';

  return (
    <div className={styles.integration}>
      <span className={`${styles.dot} ${styles[status]}`} />
      <span className={styles.integrationName}>{name}</span>
      <span className={styles.integrationStatus}>{label}</span>
    </div>
  );
}
