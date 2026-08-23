import { useEffect, useState, useMemo, useCallback } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { Map as MapIcon, Eye, EyeOff, RefreshCw, Loader2 } from "lucide-react";
import "leaflet/dist/leaflet.css";
import { getComplaints } from "../api";
import { SEVERITY_COLOR, ROAD_COLOR, DELHI_NCR_CENTER, categoryLabel } from "../constants";
import "./GisMap.css";

function MapController({ center }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 11);
  }, [map, center]);
  return null;
}

const CATEGORY_FILTERS = [
  { value: "", label: "All categories" },
  { value: "Road Damage", label: "Pothole / Road Damage" },
  { value: "Drainage / Waterlogging", label: "Waterlogging" },
  { value: "Streetlight / Electrical", label: "Streetlight" },
  { value: "Waste Management", label: "Waste" },
];

const ROAD_FILTERS = [
  { value: "", label: "All roads" },
  { value: "NHAI", label: "NHAI (National Highway)" },
  { value: "State/Municipal", label: "State / Municipal" },
];

export default function GisMap() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState("");
  const [roadType, setRoadType] = useState("");
  const [showMarkers, setShowMarkers] = useState(true);
  const [showRoadTint, setShowRoadTint] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const params = {};
    if (category) params.category = category;
    if (roadType) params.road_type = roadType;
    getComplaints(params)
      .then((d) => setComplaints(d.complaints))
      .catch(() => setComplaints([]))
      .finally(() => setLoading(false));
  }, [category, roadType]);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const c = { Low: 0, Medium: 0, High: 0, Critical: 0 };
    complaints.forEach((x) => {
      if (c[x.severity] !== undefined) c[x.severity]++;
    });
    return c;
  }, [complaints]);

  return (
    <div className="gismap-page">
      <div className="gismap-page__header">
        <div>
          <h1>GIS Map</h1>
          <p>Interactive infrastructure defect map with severity and road-authority overlays</p>
        </div>
        <button className="btn btn--ghost btn--sm" onClick={load}>
          {loading ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}
          Refresh
        </button>
      </div>

      <div className="gismap-toolbar">
        <div className="gismap-toolbar__group">
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORY_FILTERS.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <select value={roadType} onChange={(e) => setRoadType(e.target.value)}>
            {ROAD_FILTERS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="gismap-toolbar__group">
          <button
            className={`toggle-chip ${showMarkers ? "toggle-chip--on" : ""}`}
            onClick={() => setShowMarkers((v) => !v)}
          >
            {showMarkers ? <Eye size={13} /> : <EyeOff size={13} />} Defect Markers
          </button>
          <button
            className={`toggle-chip ${showRoadTint ? "toggle-chip--on" : ""}`}
            onClick={() => setShowRoadTint((v) => !v)}
          >
            {showRoadTint ? <Eye size={13} /> : <EyeOff size={13} />} Road Authority Tint
          </button>
        </div>
      </div>

      <div className="gismap-panel">
        <div className="gismap-panel__head">
          <MapIcon size={16} />
          <span>GIS Digital Twin Map</span>
          <span className="gismap-panel__count">{loading ? "Loading…" : `${complaints.length} complaints`}</span>
        </div>

        <div className="gismap-map-wrap">
          <MapContainer center={DELHI_NCR_CENTER} zoom={11} scrollWheelZoom className="gismap-leaflet">
            <MapController center={DELHI_NCR_CENTER} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              className="dark-tiles"
            />

            {showMarkers &&
              complaints.map((c) => {
                const lat = Number(c.latitude);
                const lon = Number(c.longitude);
                if (Number.isNaN(lat) || Number.isNaN(lon)) return null;
                const color = SEVERITY_COLOR[c.severity] || "#8b96a8";
                const radius = c.severity === "Critical" ? 9 : c.severity === "High" ? 7.5 : c.severity === "Medium" ? 6 : 5;
                return (
                  <CircleMarker
                    key={c.complaint_id}
                    center={[lat, lon]}
                    radius={radius}
                    pathOptions={{
                      color: showRoadTint ? ROAD_COLOR[c.road_type] || color : color,
                      fillColor: color,
                      fillOpacity: 0.75,
                      weight: showRoadTint ? 2.5 : 1.5,
                    }}
                  >
                    <Popup>
                      <div className="map-popup">
                        <div className="map-popup__id">{c.complaint_id}</div>
                        <div className="map-popup__row">
                          <span>Category</span>
                          <b>{categoryLabel(c.complaint_category)}</b>
                        </div>
                        <div className="map-popup__row">
                          <span>Defect</span>
                          <b>{c.defect_type}</b>
                        </div>
                        <div className="map-popup__row">
                          <span>Severity</span>
                          <b style={{ color: SEVERITY_COLOR[c.severity] }}>
                            {c.severity} ({c.severity_score})
                          </b>
                        </div>
                        {c.ai_confidence && (
                          <div className="map-popup__row">
                            <span>AI Confidence</span>
                            <b>{Math.round(Number(c.ai_confidence) * 100)}%</b>
                          </div>
                        )}
                        <div className="map-popup__row">
                          <span>Reported by</span>
                          <b>{c.report_count} citizen{Number(c.report_count) !== 1 ? "s" : ""}</b>
                        </div>
                        <div className="map-popup__row">
                          <span>Road authority</span>
                          <b>{c.road_type}</b>
                        </div>
                        <div className="map-popup__road">{c.road_name}</div>
                        <div className="map-popup__date">{c.date_time}</div>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
          </MapContainer>

          <div className="gismap-legend">
            <div className="gismap-legend__title">Severity</div>
            {Object.entries(SEVERITY_COLOR).map(([label, color]) => (
              <div className="gismap-legend__item" key={label}>
                <span className="gismap-legend__dot" style={{ background: color }} />
                {label} <span className="gismap-legend__count">({counts[label]})</span>
              </div>
            ))}
            {showRoadTint && (
              <>
                <div className="gismap-legend__title" style={{ marginTop: 10 }}>
                  Road Authority (ring)
                </div>
                {Object.entries(ROAD_COLOR).map(([label, color]) => (
                  <div className="gismap-legend__item" key={label}>
                    <span className="gismap-legend__ring" style={{ borderColor: color }} />
                    {label}
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
