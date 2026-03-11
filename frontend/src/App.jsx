import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProjectsPage from './pages/ProjectsPage';
import BoardPage from './pages/BoardPage';
import SprintsPage from './pages/SprintsPage';
import EpicsPage from './pages/EpicsPage';
import GitHubPage from './pages/GitHubPage';
import GmailPage from './pages/GmailPage';
import CalendarPage from './pages/CalendarPage';
import WhatsAppPage from './pages/WhatsAppPage';
import AIPage from './pages/AIPage';
import SettingsPage from './pages/SettingsPage';
import LogsPage from './pages/LogsPage';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/projects" replace />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:projectId/board" element={<BoardPage />} />
        <Route path="projects/:projectId/sprints" element={<SprintsPage />} />
        <Route path="projects/:projectId/epics" element={<EpicsPage />} />
        <Route path="github" element={<GitHubPage />} />
        <Route path="gmail" element={<GmailPage />} />
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="whatsapp" element={<WhatsAppPage />} />
        <Route path="ai" element={<AIPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="logs" element={<LogsPage />} />
      </Route>
    </Routes>
  );
}
