import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { api } from "./api";
import JobsPage from "./pages/JobsPage";
import JobDetailPage from "./pages/JobDetailPage";
import ApplicationPage from "./pages/ApplicationPage";

export default function App() {
  const [provider, setProvider] = useState<string | null>(null);
  const [apiDown, setApiDown] = useState(false);

  useEffect(() => {
    api.health().then((h) => setProvider(h.ai_provider)).catch(() => setApiDown(true));
  }, []);

  return (
    <>
      <header className="topbar">
        <Link to="/" className="brand">
          <img src="/favicon.svg" alt="" width={26} height={26} />
          AI Recruitment Assistant
        </Link>
        <span className="topbar-meta">
          {apiDown ? (
            <span className="pill pill-failed">API unreachable</span>
          ) : provider ? (
            <span className="pill pill-neutral" title="Model used for CV analysis">AI: {provider}</span>
          ) : null}
        </span>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<JobsPage />} />
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
          <Route path="/applications/:appId" element={<ApplicationPage />} />
          <Route path="*" element={<p>Page not found. <Link to="/">Back to vacancies</Link></p>} />
        </Routes>
      </main>
      <footer className="footer">
        AI scores are advisory. Every hiring decision is made and recorded by a recruiter.
      </footer>
    </>
  );
}
