export async function fetchDesertMetrics() {
  const res = await fetch("http://localhost:8000/metrics/desert-index");
  return res.json();
}
