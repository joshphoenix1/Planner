import { useState } from 'react';
import { api } from '../api/client';
import { useApi } from '../hooks/useApi';
import styles from './GitHubPage.module.css';

export default function GitHubPage() {
  const { data: status } = useApi(() => api.getGitHubStatus());
  const { data: repos, loading, error } = useApi(() =>
    status?.configured ? api.getGitHubRepos() : Promise.resolve([])
  , [status?.configured]);
  const { data: projects, refetch: refetchProjects } = useApi(() => api.getProjects());

  const [importing, setImporting] = useState(null);

  const handleImport = async (repo) => {
    setImporting(repo.full_name);
    try {
      await api.createProject({
        name: repo.name,
        description: repo.description || '',
        github_url: repo.html_url,
        github_repo: repo.full_name,
      });
      refetchProjects();
    } finally {
      setImporting(null);
    }
  };

  const isImported = (fullName) => {
    return projects?.some(p => p.github_repo === fullName);
  };

  if (!status?.configured) {
    return (
      <div className={styles.page}>
        <h1>GitHub Integration</h1>
        <div className={styles.setup}>
          <h2>Setup Required</h2>
          <p>To import repositories from GitHub, set your personal access token:</p>
          <code>export GITHUB_TOKEN=your_token_here</code>
          <p>Then restart the backend server.</p>
          <a
            href="https://github.com/settings/tokens/new?scopes=repo&description=Planner"
            target="_blank"
            rel="noopener"
            className={styles.link}
          >
            Create a GitHub token
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>GitHub Repositories</h1>
        <span className={styles.connected}>Connected</span>
      </header>

      {loading && <p className={styles.loading}>Loading repositories...</p>}
      {error && <p className={styles.error}>Error: {error}</p>}

      <div className={styles.grid}>
        {repos?.map((repo) => (
          <div key={repo.full_name} className={styles.card}>
            <div className={styles.cardHeader}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 22v-4a4.8 4.8 0 00-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 004 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
                <path d="M9 18c-4.51 2-5-2-7-2" />
              </svg>
              <div className={styles.repoInfo}>
                <h3>{repo.name}</h3>
                <span className={styles.fullName}>{repo.full_name}</span>
              </div>
            </div>

            {repo.description && <p className={styles.desc}>{repo.description}</p>}

            <div className={styles.actions}>
              <a href={repo.html_url} target="_blank" rel="noopener" className={styles.viewBtn}>
                View on GitHub
              </a>
              {isImported(repo.full_name) ? (
                <span className={styles.imported}>Imported</span>
              ) : (
                <button
                  onClick={() => handleImport(repo)}
                  className={styles.importBtn}
                  disabled={importing === repo.full_name}
                >
                  {importing === repo.full_name ? 'Importing...' : 'Import as Project'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
