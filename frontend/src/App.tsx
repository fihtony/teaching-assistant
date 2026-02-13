/**
 * Main App component with React Router setup
 */

import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/layout";
import {
  Dashboard,
  GradingResultPage,
  HistoryPage,
  TemplatesPage,
  SettingsPage,
  StudentsPage,
  GradingPage,
  BuildInstructionPage,
} from "@/pages";

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
        <Route path="/grading" element={<GradingPage />} />
        <Route path="/grade/:id" element={<GradingResultPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/templates" element={<TemplatesPage />} />
        <Route path="/build-instruction" element={<BuildInstructionPage />} />
        <Route path="/students" element={<StudentsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
