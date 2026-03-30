import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import WorldMapImage from "../assets/worldmap.png"
export default function Home() {
  const [scrollY, setScrollY] = useState(0);
  const [selected, setselected] = useState("Home");
  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);
  return (
    <div className="bg-white text-[#1f2937] font-['Manrope',sans-serif] min-h-screen overflow-x-hidden selection:bg-red-200 selection:text-red-600">
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

      {/* NAVBAR */}
      <nav className="fixed top-0 w-full z-50 flex justify-between items-center px-8 h-20 bg-white border-b border-red-100">
        <div className="text-2xl font-bold text-red-600 font-['Space_Grotesk']">
           <a href="#home" onClick={()=>setselected("home")}>TENeT</a>
        </div>

        <div className="hidden md:flex gap-10">
        <Link to="/map"><a onClick={()=>setselected("map")} className={` hover:text-red-500 ${selected == "map" ? "text-red-600" : "text-gray-700"}`}>Map</a></Link> 
          <a href="#About" onClick={()=>setselected("about")} className={` hover:text-red-500 ${selected == "about" ? "text-red-600" : "text-gray-700"}`}>About</a>
          <a href="#Contribute" onClick={()=>setselected("contribute")} className={` hover:text-red-500 ${selected == "contribute" ? "text-red-600" : "text-gray-700"}`}>Contribution</a>
          <a href = "#contact" onClick={()=>setselected("contact")} className={` hover:text-red-500 ${selected == "contact" ? "text-red-600" : "text-gray-700"}`}>Contact</a>
        </div>

        <button className="hero-gradient px-6 py-2.5 rounded-xl text-white font-bold shadow">
          Login
        </button>
      </nav>

      <main className="pt-20">

        {/* HERO */}
        <section id="home" className="relative h-[80vh] flex items-center px-8 md:px-24">
          <div className="absolute inset-0">
            <img
              src={WorldMapImage}
              className="w-full h-full object-cover opacity-50"
              style={{ transform: `translateY(${scrollY * 0.1}px)` }}
            />
            <div className="absolute inset-0 bg-white/80" />
          </div>

          <div className="relative z-10 max-w-4xl">
            <h1 className="text-7xl font-bold mb-6 text-[#1f2937]">
              TENeT
            </h1>

            <p className="text-2xl text-gray-600 mb-8">
              pinpoints where telehealth can truly change lives connecting underserved communities with the care they need.
            </p>

            <div className="flex gap-4">
              <Link to="/map">
              <button className="hero-gradient px-8 py-4 rounded-xl text-white font-bold">
                Explore Map
              </button>
              </Link>
              <button className="px-8 py-4 border border-red-200 rounded-xl text-red-500">
                Learn More
              </button>
            </div>
          </div>
        </section>

        {/* ABOUT */}
        <section id = "About" className="py-24 px-8 md:px-24 bg-[#fff5f5]">
          <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-12">
            <div>
              <h2 className="text-4xl font-bold mb-6">
                Healthcare Without Boundaries
              </h2>
              <p className="text-gray-600">
                TENeT combines healthcare and connectivity data to reveal underserved regions and unlock telehealth opportunities.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white p-6 rounded-xl border border-red-100 shadow-sm">
                <span className="text-red-500 text-3xl font-bold">01</span>
                <p>Data Mapping</p>
              </div>
              <div className="bg-red-50 p-6 rounded-xl border border-red-100 shadow-sm">
                <span className="text-red-500 text-3xl font-bold">02</span>
                <p>Connectivity Insight</p>
              </div>
            </div>
          </div>
        </section>

        {/* CAPABILITIES */}
        <section className="py-24 px-8 md:px-24">
          <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">

            <div className="bg-white p-8 rounded-xl border border-red-100 shadow-sm">
              <span className="material-symbols-outlined text-red-500 text-4xl">health_and_safety</span>
              <h3 className="text-xl font-bold mt-4">Healthcare Data</h3>
              <p className="text-gray-600">Analyze healthcare facility distribution.</p>
            </div>

            <div className="bg-red-50 p-8 rounded-xl border border-red-100 shadow-sm">
              <span className="material-symbols-outlined text-red-500 text-4xl">wifi</span>
              <h3 className="text-xl font-bold mt-4">Connectivity</h3>
              <p className="text-gray-600">Measure internet access and quality.</p>
            </div>

            <div className="bg-white p-8 rounded-xl border border-red-100 shadow-sm">
              <span className="material-symbols-outlined text-red-500 text-4xl">monitor_heart</span>
              <h3 className="text-xl font-bold mt-4">Smart Metrics</h3>
              <p className="text-gray-600">Evaluate telehealth feasibility.</p>
            </div>

          </div>
        </section>

        {/* CTA */}
        <section id="Contribute" className="py-24 text-center">
          <h2 className="text-4xl font-bold mb-6">
            Contribute to Healthcare Access
          </h2>
          <p className="text-gray-600 mb-8">
            Support open data platforms like Healthsites.io and help improve global healthcare insights.
          </p>
          <button className="hero-gradient px-10 py-4 rounded-xl text-white font-bold">
            Start Contributing
          </button>
        </section>
    <section id = "contact" className="w-full pb-24 bg-whie flex items-center justify-center">

        <div className="w-1/3">
          <h3 className="text-4xl font-bold text-black mb-6">Send a Message</h3>

          <form className="space-y-4 ">
            <div>
              <label className="block text-sm font-medium text-gray-600">Name</label>
              <input
                type="text"
                className="w-full mt-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Your name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-600">Email</label>
              <input
                type="email"
                className="w-full mt-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Your email"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-600">Message</label>
              <textarea
                rows="4"
                className="w-full mt-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Your message"
              ></textarea>
            </div>

            <button
              type="submit"
              className="w-full bg-red-500 text-white py-3 rounded-lg font-semibold hover:bg-red-600 transition"
            >
              Send Message
            </button>
          </form>
        </div>
    </section>

      </main>

      {/* FOOTER */}
      <footer className="border-t border-red-100 py-8 text-center text-gray-500">
        © 2026 TENeT Healthcare Intelligence Platform
      </footer>
    </div>
  );
}