import { useState, useRef, useCallback } from "react";
import {
  Camera, MapPin, Upload, Loader2, CheckCircle2, Copy,
  Eye, Zap, AlertOctagon, Link2, Navigation,
} from "lucide-react";
import { CATEGORIES } from "../constants";
import { reportIssue } from "../api";
import "./ReportIssue.css";

const SEVERITY_STYLE = {
  Low: { color: "var(--sev-low)", label: "Low" },
  Medium: { color: "var(--sev-medium)", label: "Medium" },
  High: { color: "var(--sev-high)", label: "High" },
  Critical: { color: "var(--sev-critical)", label: "Critical" },
};

export default function ReportIssue() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [category, setCategory] = useState(CATEGORIES[0].value);
  const [coords, setCoords] = useState(null);
  const [gpsStatus, setGpsStatus] = useState("idle"); // idle | locating | done | error
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFile = useCallback((f) => {
    if (!f || !f.type.startsWith("image/")) return;
    setFile(f);
    setResult(null);
    setError(null);
    const url = URL.createObjectURL(f);
    setPreviewUrl(url);
  }, []);

  function captureGPS() {
    if (!navigator.geolocation) {
      setGpsStatus("error");
      return;
    }
    setGpsStatus("locating");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        setGpsStatus("done");
      },
      () => {
        // Fall back to a representative Delhi-NCR point for demo purposes
        // when location permission is denied / unavailable.
        setCoords({ lat: 28.6139 + (Math.random() - 0.5) * 0.15, lon: 77.209 + (Math.random() - 0.5) * 0.15 });
        setGpsStatus("done");
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }

  async function handleSubmit() {
    if (!coords) {
      setError("Capture a location before submitting.");
      return;
    }
    if (category === "Road Damage" && !file) {
      setError("Pothole/road damage reports need a photo for AI detection.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await reportIssue({
        latitude: coords.lat,
        longitude: coords.lon,
        category,
        file,
      });
      setResult(res);
    } catch (e) {
      setError(e.message || "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  function resetForm() {
    setFile(null);
    setPreviewUrl(null);
    setCoords(null);
    setGpsStatus("idle");
    setResult(null);
    setError(null);
  }

  const complaint = result?.complaint;
  const box = complaint?.bounding_box;
  const isDuplicate = result?.status === "duplicate";

  return (
    <div className="report-page">
      <div className="report-page__header">
        <h1>Report an Issue</h1>
        <p>AI-assisted civic infrastructure reporting</p>
      </div>

      <div className="report-grid">
        {/* LEFT: submission form */}
        <div className="panel">
          <div className="panel__head">
            <Camera size={16} />
            <span>Report an Issue</span>
          </div>
          <p className="panel__subtitle">Photo, GPS location, and issue category</p>

          <div className="field-label">Photo / Video Upload</div>
          <div
            className={`dropzone ${dragOver ? "dropzone--over" : ""}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFile(e.dataTransfer.files?.[0]);
            }}
          >
            {previewUrl ? (
              <img src={previewUrl} alt="Upload preview" className="dropzone__preview" />
            ) : (
              <>
                <Upload size={26} strokeWidth={1.6} />
                <div>
                  Drop image or <span className="link-text">click to upload</span>
                </div>
                <div className="dropzone__hint">Supports JPG, PNG — Max 10MB</div>
              </>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="visually-hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </div>

          <div className="field-label">Location (GPS)</div>
          <div className="gps-row">
            <div className="gps-value mono">
              {coords ? `${coords.lat.toFixed(5)}, ${coords.lon.toFixed(5)}` : "Not captured"}
            </div>
            <button className="btn btn--brand" onClick={captureGPS} disabled={gpsStatus === "locating"}>
              {gpsStatus === "locating" ? <Loader2 size={15} className="spin" /> : <MapPin size={15} />}
              Capture GPS
            </button>
          </div>
          {gpsStatus === "error" && (
            <div className="hint-error">Geolocation isn't available in this browser.</div>
          )}

          <div className="field-label">Issue Category</div>
          <div className="category-grid">
            {CATEGORIES.map((c) => (
              <button
                key={c.value}
                className={`category-chip ${category === c.value ? "category-chip--active" : ""}`}
                onClick={() => setCategory(c.value)}
              >
                {c.label}
              </button>
            ))}
          </div>

          {error && <div className="hint-error">{error}</div>}

          <button className="btn btn--submit" onClick={handleSubmit} disabled={submitting}>
            {submitting ? (
              <>
                <Loader2 size={16} className="spin" /> Analyzing…
              </>
            ) : (
              <>
                <Navigation size={16} /> Submit Report
              </>
            )}
          </button>

          {result && (
            <button className="btn btn--ghost" onClick={resetForm}>
              Report another issue
            </button>
          )}
        </div>

        {/* RIGHT: AI vision analysis */}
        <div className="panel">
          <div className="panel__head">
            <Eye size={16} />
            <span>AI Vision Analysis</span>
            {result && (
              <span className="panel__status-pill">
                <CheckCircle2 size={12} /> COMPLETE
              </span>
            )}
          </div>
          <p className="panel__subtitle">
            {category === "Road Damage" ? "YOLOv8 Pothole Detection" : "Category-based severity scoring"}
          </p>

          {!result && !submitting && (
            <div className="vision-empty">
              <Zap size={28} strokeWidth={1.4} />
              <p>Submit a report to see AI detection results here.</p>
            </div>
          )}

          {submitting && (
            <div className="vision-empty">
              <Loader2 size={28} className="spin" />
              <p>Running detection pipeline…</p>
            </div>
          )}

          {result && isDuplicate && (
            <div className="duplicate-banner">
              <Link2 size={16} />
              <div>
                <strong>Duplicate Detected — Report Merged</strong>
                <div className="duplicate-banner__sub">{result.message}</div>
                <div className="duplicate-banner__sub">
                  {result.distance_m}m from existing report · now flagged by {result.report_count} citizens
                </div>
              </div>
            </div>
          )}

          {result && complaint && (
            <>
              {previewUrl && category === "Road Damage" && (
                <div className="vision-image-wrap">
                  <img src={previewUrl} alt="Analyzed" className="vision-image" />
                  {box && complaint.defect_type && (
                    <div
                      className="vision-box"
                      style={{
                        left: `${(box.x1 / (complaint.image_width || 1)) * 100}%`,
                        top: `${(box.y1 / (complaint.image_height || 1)) * 100}%`,
                        width: `${((box.x2 - box.x1) / (complaint.image_width || 1)) * 100}%`,
                        height: `${((box.y2 - box.y1) / (complaint.image_height || 1)) * 100}%`,
                      }}
                    >
                      <span className="vision-box__label">
                        {complaint.defect_type}{" "}
                        {complaint.ai_confidence !== "" && complaint.ai_confidence != null
                          ? `${Math.round(complaint.ai_confidence * 100)}%`
                          : ""}
                      </span>
                    </div>
                  )}
                </div>
              )}

              <div className="vision-stats">
                {complaint.ai_confidence !== "" && complaint.ai_confidence != null && (
                  <div className="vision-stat">
                    <div className="vision-stat__label">
                      <Zap size={13} /> Detection Confidence
                    </div>
                    <div className="vision-stat__value">
                      {Math.round(complaint.ai_confidence * 100)}%
                    </div>
                    <div className="confidence-bar">
                      <div
                        className="confidence-bar__fill"
                        style={{ width: `${complaint.ai_confidence * 100}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="vision-meta-grid">
                  <MetaRow label="Complaint ID" value={complaint.complaint_id} mono />
                  <MetaRow
                    label="Location"
                    value={`${Number(complaint.latitude).toFixed(4)}, ${Number(complaint.longitude).toFixed(4)}`}
                    mono
                  />
                  <MetaRow label="Type" value={complaint.complaint_category} />
                  <MetaRow label="Defect" value={complaint.defect_type} />
                  <MetaRow
                    label="AI Severity"
                    value={
                      <span
                        className="severity-badge"
                        style={{
                          color: SEVERITY_STYLE[complaint.severity]?.color,
                          borderColor: SEVERITY_STYLE[complaint.severity]?.color,
                        }}
                      >
                        <AlertOctagon size={12} /> {complaint.severity} ({complaint.severity_score})
                      </span>
                    }
                  />
                  <MetaRow label="Road Authority" value={complaint.road_type} />
                  <MetaRow label="Road" value={complaint.road_name} />
                  <MetaRow label="Detector" value={complaint.detector} mono muted />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function MetaRow({ label, value, mono, muted }) {
  return (
    <div className="meta-row">
      <span className="meta-row__label">{label}</span>
      <span className={`meta-row__value ${mono ? "mono" : ""} ${muted ? "meta-row__value--muted" : ""}`}>
        {value}
      </span>
    </div>
  );
}
