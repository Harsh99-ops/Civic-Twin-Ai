import { useState, useEffect, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import TopNav from "./components/TopNav";
import AlertBanner from "./components/AlertBanner";
import ChatWidget from "./components/ChatWidget";
import ReportIssue from "./pages/ReportIssue";
import GisMap from "./pages/GisMap";
import Dashboard from "./pages/Dashboard";
import { getHealth, getRiskZones } from "./api";

function App() {
  const [role, setRole] = useState("citizen");
  const [backendUp, setBackendUp] = useState(true);
  const [zones, setZones] = useState([]);

  const checkHealth = useCallback(() => {
    getHealth()
      .then(() => setBackendUp(true))
      .catch(() => setBackendUp(false));
  }, []);

  useEffect(() => {
    checkHealth();
    getRiskZones(20).then((d) => setZones(d.zones)).catch(() => setZones([]));
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return (
    <BrowserRouter>
      <TopNav role={role} onRoleChange={setRole} backendUp={backendUp} />
      <AlertBanner zones={zones} />
      <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Routes>
          <Route path="/" element={<Navigate to="/report" replace />} />
          <Route path="/report" element={<ReportIssue />} />
          <Route path="/map" element={<GisMap />} />
          <Route
            path="/dashboard"
            element={role === "admin" ? <Dashboard /> : <Navigate to="/report" replace />}
          />
          <Route path="*" element={<Navigate to="/report" replace />} />
        </Routes>
      </main>
      <ChatWidget />
    </BrowserRouter>
  );
}

export default App;
