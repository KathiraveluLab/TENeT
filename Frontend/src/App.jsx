import React from "react";
import "leaflet/dist/leaflet.css";
import Home from "./pages/Home.jsx";
import Map from "./pages/Map.jsx"
import { Routes, Route } from "react-router-dom";
function App() {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/map" element={<Map />} />
      </Routes>
    </div>
  );
  
}

export default App;
