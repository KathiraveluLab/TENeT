export async function fetchDesertMetrics() {
  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/metrics/desert-index`);
  return res.json();
}
