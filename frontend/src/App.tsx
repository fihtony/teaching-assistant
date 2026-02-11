/**
 * Main App component with React Router setup
 */

import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/layout";
import { Dashboard, GradingPage, HistoryPage, TemplatesPage, SettingsPage, StudentsPage } from "@/pages";
import { EssayGradingPage } from "@/pages/EssayGradingPage";

function App() {
  useEffect(() => {
    // Log frontend startup time
    const startTime = new Date().toISOString();
    console.log(`[Frontend] Started at ${startTime}`);
    sessionStorage.setItem("frontend_startup_time", startTime);
  }, []);

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/grade/:id" element={<GradingPage />} />
        <Route path="/essay-grading" element={<EssayGradingPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
