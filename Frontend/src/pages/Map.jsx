import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer , Marker, Popup, Circle, Rectangle} from "react-leaflet";
import { Link } from "react-router-dom";
import Healthicon from "../assets/hospital.png"
import L from "leaflet";
function Map() {
  const [selected, setSelected] = useState("map");
  const [internetData, setInternetData] = useState([0,0,0,0]);
  const [healthData, setHealthData] = useState([]);
  const [MapRadius, setMapRadius] = useState(10);
  useEffect(() => {
    fetch("http://localhost:5000/api/tenet/")
      .then((res) => res.json())
      .then((data) => {
        console.log(data)
        setInternetData(data.internet);
        setHealthData(data.health);
      })
      .catch((err) => console.error(err));
  }, []);
    const healthIcon = L.icon({
    iconUrl: Healthicon,
    iconSize: [25, 25],
    iconAnchor: [12, 41],
    popupAnchor: [0, -35]
  });
  return (
    <div className="h-screen bg-white text-balck font-['Manrope',sans-serif]">
            <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Manrope:wght@200;300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

        .material-symbols-outlined {
          font-family: 'Material Symbols Outlined';
        }

        .hero-gradient { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }

        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(28px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .anim-1 { animation: fadeInUp .6s ease both; }
        .anim-2 { animation: fadeInUp .8s ease both; }
        .anim-3 { animation: fadeInUp .9s .15s ease both; }
        .anim-4 { animation: fadeInUp 1s .3s ease both; }

        .bento-icon-bg {
          position: absolute;
          right: 0;
          bottom: 0;
          opacity: .05;
          font-size: 180px;
        }
      `}</style>
      {/* ── NAVBAR ── */}
      <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-8 h-20 bg-white border-b border-red-100 shadow">
        <div className="text-2xl font-bold text-red-600 font-['Space_Grotesk']">
           <Link to="/" onClick={() => setSelected("home")}>
            TENeT
          </Link>
        </div>

        <div className="hidden md:flex gap-10">
          <Link to="/map">
            <span
              onClick={() => setSelected("map")}
              className={`cursor-pointer hover:text-red-500 ${
                selected === "map" ? "text-red-600 border-b-2 border-red-600" : "text-gray-700"
              }`}
            >
              Map
            </span>
          </Link>

          <Link to="/">
            <span
              onClick={() => setSelected("about")}
              className={`cursor-pointer hover:text-red-500 ${
                selected === "about" ? "text-red-600 border-b-2 border-red-600" : "text-gray-700"
              }`}
            >
              About
            </span>
          </Link>

          <Link to="/">
            <span
              onClick={() => setSelected("contribute")}
              className={`cursor-pointer hover:text-red-500 ${
                selected === "contribute" ? "text-red-600 border-b-2 border-red-600" : "text-gray-700"
              }`}
            >
              Contribution
            </span>
          </Link>

          <Link to="/">
            <span
              onClick={() => setSelected("contact")}
              className={`cursor-pointer hover:text-red-500 ${
                selected === "contact" ? "text-red-600 border-b-2 border-red-600" : "text-gray-700"
              }`}
            >
              Contact
            </span>
          </Link>
        </div>

        <button className="hero-gradient px-6 py-2.5 rounded-xl text-white font-bold shadow">
          Login
        </button>
      </nav>

      {/* ── MAP SECTION ── */}
      <div className="pt-24 px-8 md:px-24">
        <div className="flex flex-col justify-center items-center md:flex-row gap-8">
          {/* ── Left Filter Panel ── */}
          <div className="md:w-1/4 h-[50vh] bg-white/80 backdrop-blur-md p-8 rounded-xl flex flex-col gap-6 shadow-lg z-20">
            <h3 className="text-2xl font-bold text-black mb-4">Filter Map</h3>

            <div className="flex flex-col gap-2">
              <label className="text-black font-semibold">Region</label>
              <select className="p-2 rounded bg-white text-black">
                <option>All Alaska</option>
                <option>North</option>
                <option>South</option>
                <option>East</option>
                <option>West</option>
              </select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-black font-semibold">Connectivity</label>
              <select className="p-2 rounded bg-white text-black">
                <option>All</option>
                <option>High</option>
                <option>Medium</option>
                <option>Low</option>
              </select>
            </div>
             <div className="flex flex-col gap-2">
            <label className="text-black font-semibold"> Radius: {MapRadius} Km </label>
            <input
              type="range"
              min="1"
              max="100"
              value={MapRadius}
              onChange={(e) => setMapRadius(Number(e.target.value))}
              className="w-64 slider"
            />
          </div>
            <button className="mt-4 bg-red-600 hover:bg-red-500 text-white font-bold py-2 px-4 rounded transition">
              Apply Filters
            </button>
          </div>

          {/* ── Right Map ── */}
          <div className="md:w-3/4 relative">
            <MapContainer
              center={[64.2, -149.5]}
              zoom={4}
              scrollWheelZoom={false}
              className="w-full h-[80vh] rounded-xl shadow-2xl"
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution="&copy; OpenStreetMap contributors"
              />
              {/* {internetData.map((point, idx) => (
                <Marker
                  key={`internet-${idx}`}
                  position={[point.lat, point.lon]}
                  // Optional: use a different icon for internet
                >
                  <Popup >{point.provider}</Popup>
                </Marker>
              ))} */}

              {healthData.map((point, idx) => (
                 <Circle
                    center={point}
                    key = {idx}
                    radius={MapRadius*1000}
                    pathOptions={{ color: "red", fillOpacity: 0.2 }}
                    >
                    <Popup >{point.name}</Popup>
                    </Circle>
              ))}

              <Rectangle
                bounds={[
            [internetData[0], internetData[1]], 
            [internetData[2], internetData[3]] 
          ]}
                pathOptions={{ color: "blue", weight: 2, fillOpacity: 0.1 }}
              />
            </MapContainer>
            <span className="absolute top-20 left-1/2 w-4 h-4 bg-red-600 rounded-full shadow-lg animate-pulse"></span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Map;