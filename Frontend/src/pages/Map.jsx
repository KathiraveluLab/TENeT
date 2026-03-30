import React, { useState, useEffect } from "react";
import { MapContainer, TileLayer , Marker, Popup, Circle,GeoJSON} from "react-leaflet";
import { Link } from "react-router-dom";
import Healthicon from "../assets/hospital.png"
import L from "leaflet";
function Map() {
  const [selected, setSelected] = useState("map");
  const [internetData, setInternetData] = useState(null);
  const [healthData, setHealthData] = useState([]);
  const [MapRadius, setMapRadius] = useState(10);
  const [longtiude,setlongtiude] = useState(63.5795);
  const [latitiude,setlatitiude] = useState(-162.3874);
  const [score, setscore] = useState(null);
  const radius = 60;
  const stroke = 10;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const apiUrl = import.meta.env.VITE_BACKEND_ADDRESS || "http://localhost:8000";
  console.log(apiUrl)
  useEffect(() => {
    fetch(`${apiUrl}/api/tenet/`)
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
  const geojsonStyle = {
        fillColor: "#2ecc71",
        weight: 2,
        opacity: 1,
        color: 'blue',
        fillOpacity: 0.7,
    };
  const handleCalculate = async () => {
    console.log("test")
    const payload = { 
      longtiude, 
      latitiude,
      MapRadius
    };

    try {
      const response = await fetch(`${apiUrl}/api/calculate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      setscore(data.result)
      console.log('Update successful:', data);
    } catch (error) {
      console.error('Update failed:', error);
    }
  };
  delete L.Icon.Default.prototype._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  });
  console.log(internetData)
  console.log(healthData)
  console.log(score)
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
      <div className="pt-24 px-8 md:px-24">
        <div className="flex flex-col justify-center items-center md:flex-row gap-8">
          <div className="md:w-1/4 h-[50vh] bg-white/80 backdrop-blur-md p-8 rounded-xl self-start flex flex-col gap-6 shadow-lg z-20">
            <h3 className="text-2xl font-bold text-black mb-3">Feasibility</h3>
            <div className="flex flex-col gap-2">
              <label className="text-black font-semibold"> Longtiude </label>
              <input className="border-2 px-3 py-1" type = "text" placeholder = "longtiude" value = {longtiude} onChange={(e)=> setlongtiude(e.target.value)}></input>
              <label className="text-black font-semibold"> Latitude </label>
              <input className="border-2 px-3 py-1" type = "text" value = {latitiude} placeholder = "latitude" onChange={(e)=>setlatitiude(e.target.value)}></input>
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
            <button onClick={handleCalculate} className="bg-red-500 text-white p-3">
                Calculate
              </button>
          </div>
             <div>
              {score && (
            <div className="flex flex-col w-full mt-2 items-start justify-center bg-white/80 backdrop-blur-md p-2 rounded-xl  shadow-lg">
                    <h2 className="text-xl font-bold mb-1">
                      Score
                    </h2>
                    <div className="flex justify-center">
                      <svg height={radius * 2} width={radius * 2}>
                        <circle
                          stroke="#fee2e2"
                          fill="transparent"
                          strokeWidth={stroke}
                          r={normalizedRadius}
                          cx={radius}
                          cy={radius}
                        />
                        <circle
                          className="text-green-600"
                          stroke="currentColor"
                          fill="transparent"
                          strokeWidth={stroke}
                          strokeDasharray={`${circumference} ${circumference}`}
                          strokeDashoffset={circumference - (score / 100) * circumference}
                          strokeLinecap="round"
                          style={{ transition: "stroke-dashoffset 0.5s" }}
                          r={normalizedRadius}
                          cx={radius}
                          cy={radius}
                        />
                        <text
                          x="50%"
                          y="50%"
                          dominantBaseline="middle"
                          textAnchor="middle"
                          className="fill-green-500 text-lg font-bold"
                        >
                          {score.score}
                        </text>
                        </svg>
                    </div>

                    <ul className="text-gray-700 mt-2 self-start">
                      <li>
                        <lable className="text-black font-semibold">Closest HealthCenter</lable>
                        <p className="text-black font-semibold pl-2">{score.closestHospital}</p>
                      </li>
                      <li>
                        <lable className="text-black font-semibold">Closest HealthCenter Distance</lable>
                        <p className="text-black font-semibold pl-2">{score.distanceToHospital? Number(score.distanceToHospital.toFixed(2)): "0.00"} KM</p>
                      </li>
                    </ul>
                  </div>
            )}
          </div>
          </div>

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
                <Marker
                  key={`search`}
                  position={[longtiude, latitiude]}
                >
                  <Popup >Searched Location</Popup>
                </Marker>
              {healthData.map((point, idx) => (
                 <Circle
                    center={[point.lon,point.lat]}
                    key = {idx}
                    radius={MapRadius*1000}
                    pathOptions={{ color: "red", fillOpacity: 0.2 }}
                    >
                    <Popup >{point.name}</Popup>
                    </Circle>
              ))}


          {internetData && (
                <GeoJSON 
                    data={internetData} 
                    style={geojsonStyle}
                    onEachFeature={(feature, layer) => {
                        layer.bindPopup(`Provider: ${feature.properties.brandname}`);
                    }}
                />
            )}
            </MapContainer>
            <span className="absolute top-20 left-1/2 w-4 h-4 bg-red-600 rounded-full shadow-lg animate-pulse"></span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Map;