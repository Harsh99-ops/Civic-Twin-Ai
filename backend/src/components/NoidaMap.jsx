import { useEffect, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  useMap
} from "react-leaflet";

import L from "leaflet";
import Papa from "papaparse";

import "leaflet/dist/leaflet.css";

// Fix Leaflet's default marker icon paths when using Vite
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Noida center
const NOIDA_CENTER = [28.5744, 77.3560];

function MapController() {
  const map = useMap();

  useEffect(() => {
    map.setView(NOIDA_CENTER, 12);
  }, [map]);

  return null;
}

export default function NoidaMap() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/noida_complaints_300.csv")
      .then((response) => response.text())
      .then((csvText) => {
        Papa.parse(csvText, {
          header: true,
          skipEmptyLines: true,
          complete: (result) => {
            const validComplaints = result.data.filter(
              (item) =>
                item.latitude &&
                item.longitude &&
                !isNaN(Number(item.latitude)) &&
                !isNaN(Number(item.longitude))
            );

            setComplaints(validComplaints);
            setLoading(false);
          },
        });
      })
      .catch((error) => {
        console.error("Error loading CSV:", error);
        setLoading(false);
      });
  }, []);

  return (
    <div className="map-wrapper">
      <div className="map-header">
        <div>
          <h1>CivicTwin AI</h1>
          <p>Noida Infrastructure Intelligence — Phase 1</p>
        </div>

        <div className="complaint-count">
          {loading ? "Loading..." : `${complaints.length} complaints`}
        </div>
      </div>

      <MapContainer
        center={NOIDA_CENTER}
        zoom={12}
        scrollWheelZoom={true}
        className="noida-map"
      >
        <MapController />

        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {complaints.map((complaint) => {
          const latitude = Number(complaint.latitude);
          const longitude = Number(complaint.longitude);

          return (
            <Marker
              key={complaint.complaint_id}
              position={[latitude, longitude]}
            >
              <Popup>
                <div className="popup">
                  <h3>{complaint.complaint_id}</h3>

                  <p>
                    <strong>Category:</strong>{" "}
                    {complaint.complaint_category}
                  </p>

                  <p>
                    <strong>Latitude:</strong> {latitude}
                  </p>

                  <p>
                    <strong>Longitude:</strong> {longitude}
                  </p>

                  <p>
                    <strong>Date:</strong> {complaint.date_time}
                  </p>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}