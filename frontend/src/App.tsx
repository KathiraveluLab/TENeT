import { useEffect, useState } from "react";
import DesertMap from "./components/DesertMap";
import type { Region } from "./components/DesertMap"
type Mode = "physical" | "telehealth";

function App() {
  const [data, setData] = useState<Region[]>([]);

  const [mode, setMode] = useState<Mode>("physical");

  useEffect(() => {
  fetch("http://localhost:8000/metrics/desert-index")
    .then((res) => {
      return res.json();
    })
    .then((json) => {
      console.log("data received:", json);
      setData(json);
    })
    .catch((err) => {
      console.error("Failed to load metrics", err);
    });
}, []);

  return (
    <div style={{ height: "100vh", width: "100vw" }}>
      {/* Header */}
      <div style={{ padding: 10, background: "#111", color: "#fff" }}>
        <button onClick={() => setMode("physical")}>Physical</button>
        <button onClick={() => setMode("telehealth")}>Telehealth</button>
      </div>

      {/* Map ALWAYS renders */}
      <div style={{ height: "calc(100vh - 50px)" }}>
        <DesertMap data={data} mode={mode} />
      </div>

      {/* Optional overlay */}
      {!data && (
        <div
          style={{
            position: "absolute",
            top: 70,
            left: 20,
            background: "#000",
            color: "#fff",
            padding: 8,
          }}
        >
          Loading data…
        </div>
      )}
    </div>
  );
}

export default App;
