import { useEffect, useState } from "react";
import DesertMap from "./components/DesertMap";
type Mode = "physical" | "telehealth";
import type { FeatureCollection, Geometry } from "geojson";

type BroadbandInfo = {
  advertised: number;
  actual: number;
  gap: number;
  state: "adequately_served" | "true_desert" | "advertised_but_unreliable" | "partially_served";
  color: "green" | "red" | "orange" | "yellow";
};


type DesertProps = {
  community: {
    name: string;
    geoid: string;
    type: "place" | "native_village";
  };
  physical_desert: number;
  telehealth_desert: number;
  physical_count: number;
  telehealth_count: number;
  broadband: BroadbandInfo;
};

type DesertGeoJSON = FeatureCollection<Geometry, DesertProps>;
function App() {
  const [data, setData] = useState<DesertGeoJSON | null>(null);
  const [mode, setMode] = useState<Mode>("physical");

  useEffect(() => {
    fetch("http://localhost:8000/metrics/desert-index")
      .then(res => res.json())
      .then(json => setData(json))
      .catch(console.error);
  }, []);

  return (
    <div style={{ height: "100vh", width: "100vw" }}>
      <div style={{ padding: 10, background: "#111", color: "#fff" }}>
        <button onClick={() => setMode("physical")}>Physical</button>
        <button onClick={() => setMode("telehealth")}>Telehealth</button>
      </div>

      <div style={{ height: "calc(100vh - 50px)" }}>
        {data ? <DesertMap data={data} mode={mode} /> : "Loading…"}
      </div>
    </div>
  );
}


export default App;
