export const CATEGORIES = [
  { value: "Road Damage", label: "Pothole / Road Damage", icon: "road" },
  { value: "Drainage / Waterlogging", label: "Waterlogging", icon: "droplet" },
  { value: "Streetlight / Electrical", label: "Streetlight", icon: "lightbulb" },
  { value: "Waste Management", label: "Waste / Garbage", icon: "trash" },
];

export const SEVERITY_COLOR = {
  Low: "var(--sev-low)",
  Medium: "var(--sev-medium)",
  High: "var(--sev-high)",
  Critical: "var(--sev-critical)",
};

export const ROAD_COLOR = {
  NHAI: "var(--road-nhai)",
  "State/Municipal": "var(--road-state)",
};

export function formatINR(n) {
  const num = Number(n) || 0;
  return "₹" + num.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function formatPercent(n) {
  return `${Number(n).toFixed(1)}%`;
}

export function categoryLabel(value) {
  return CATEGORIES.find((c) => c.value === value)?.label || value;
}

export const DELHI_NCR_CENTER = [28.6139, 77.209];
