import { useState, useEffect } from "react";
import { AlertTriangle, X, CloudRain } from "lucide-react";
import "./AlertBanner.css";

/**
 * Shows a dismissible hazard banner. Content is derived from the live
 * risk-zone data (a real "N critical zones" count) rather than a
 * hardcoded weather feed — CIVIC-TWIN doesn't have an IMD/OpenWeather
 * integration wired up, so we surface the signal we actually have.
 */
export default function AlertBanner({ zones }) {
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setDismissed(false);
  }, [zones?.length]);

  if (dismissed) return null;

  const criticalZones = (zones || []).filter((z) => z.risk_level === "Critical");
  if (criticalZones.length === 0) return null;

  const waterlogging = criticalZones.filter((z) => z.dominant_category === "Drainage / Waterlogging");
  const severity = criticalZones.length >= 5 ? "HIGH" : "MEDIUM";

  return (
    <div className="alertbanner" data-severity={severity}>
      <div className="alertbanner__icon">
        {waterlogging.length > 0 ? <CloudRain size={15} /> : <AlertTriangle size={15} />}
      </div>
      <div className="alertbanner__text">
        <strong>Risk Alert —</strong>{" "}
        {criticalZones.length} zone{criticalZones.length !== 1 ? "s" : ""} at Critical risk level
        {waterlogging.length > 0 && `, ${waterlogging.length} flagged for drainage/waterlogging`}.
        Highest: {criticalZones[0].dominant_category} near ({criticalZones[0].latitude.toFixed(3)},{" "}
        {criticalZones[0].longitude.toFixed(3)}).
      </div>
      <span className="alertbanner__badge">{severity}</span>
      <button className="alertbanner__close" onClick={() => setDismissed(true)} aria-label="Dismiss alert">
        <X size={15} />
      </button>
    </div>
  );
}
