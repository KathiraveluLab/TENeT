# 🗺️ TENeT: Telehealth Effectiveness and Necessity Tracker

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Alaska GSoC 2026](https://img.shields.io/badge/GSoC-2026-red.svg)](https://summerofcode.withgoogle.com/)

> Identifying where telehealth can make the biggest impact in Alaska

## 🎯 The Problem

Alaska faces unique healthcare challenges:
- **663,300 square miles** - Larger than Texas, California, and Montana combined
- **733,391 residents** - Scattered across vast distances
- **Many communities** lack nearby medical facilities
- **Variable internet** connectivity across regions
- **Weather conditions** can prevent travel for months

## 💡 What TENeT Does

TENeT combines two critical datasets to answer: **"Where is telehealth both NEEDED and FEASIBLE?"**

### Data Integration:
1. **Healthcare Desert Identification**
   - Distance to nearest clinic/hospital
   - Specialist availability
   - Transportation access
   - Number of facilities per capita

2. **Internet Infrastructure Assessment**
   - Connection speeds (upload/download)
   - Reliability and latency
   - ISP coverage
   - Cost and accessibility

### Output:
- **Interactive map** of Alaska
- **Color-coded regions** showing telehealth priority areas
- **Data-driven insights** for policymakers and healthcare providers
- **Searchable database** of healthcare facilities and internet metrics

## 🏗️ Project Status

🚧 **Phase:** Initial Development  
📅 **Timeline:** Alaska GSoC 2026 Project  
👥 **Team:** Seeking contributors!  
📊 **Progress:** Setting up foundation

## 🛠️ Technology Stack

- **Backend:** Python 3.8+, Flask
- **Data Processing:** Pandas, NumPy, GeoPandas
- **Mapping:** Folium (OpenStreetMap), Leaflet
- **Database:** SQLite (dev), PostgreSQL (prod)
- **APIs:** REST with Flask
- **Frontend:** HTML5, CSS3, JavaScript
- **Testing:** pytest, unittest

## 📊 Data Sources

### Healthcare Facilities
| Source | Data | Coverage |
|--------|------|----------|
| [HealthSites.io](https://healthsites.io) | Global health facility database | Alaska subset |
| [Medicare.gov](https://data.medicare.gov) | CMS certified facilities | All US, Alaska focus |
| Alaska DHSS | State health department data | Alaska only |
| Alaska Primary Care Assoc | Community health centers | Alaska only |

### Internet Performance
| Source | Data | Updates |
|--------|------|---------|
| [FCC Broadband Map](https://broadbandmap.fcc.gov) | Coverage, speed, ISP data | Quarterly |
| [M-Lab](https://www.measurementlab.net) | Real-world speed tests | Real-time |
| [Ookla Open Data](https://www.speedtest.net/insights/) | Speedtest results | Quarterly |
| [broadbandmapping.com](https://www.broadbandmapping.com/) | Infrastructure maps | Monthly |

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git
- (Optional) Virtual environment tool

### Installation
```bash
# Clone the repository
git clone https://github.com/KathiraveluLab/TENeT.git
cd TENeT

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp config.example.py config.py
# Edit config.py with your settings

# Initialize database
python init_db.py

# Run development server
python run.py
```

Access the application at: `http://localhost:5000`

## 📂 Project Structure

TENeT/
├── src/
│   ├── data/              # Data collection modules
│   │   ├── healthcare_collector.py
│   │   ├── internet_collector.py
│   │   └── processor.py
│   ├── maps/              # Visualization components
│   │   ├── map_generator.py
│   │   └── styles.py
│   ├── api/               # Flask REST API
│   │   ├── app.py
│   │   └── routes.py
│   ├── models/            # Database models
│   │   ├── facility.py
│   │   └── internet_metric.py
│   └── utils/             # Helper functions
│       ├── geo_utils.py
│       └── validators.py
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
├── data/                  # Cached data files
├── static/                # Frontend assets
├── templates/             # HTML templates
├── requirements.txt       # Python dependencies
├── config.example.py      # Example configuration
├── config.py              # Configuration (gitignored)
└── run.py                 # Entry point

## 🤝 Contributing

We welcome contributions! Areas needing help:

**High Priority:**
- [ ] Data collection implementation
- [ ] Healthcare desert calculation algorithm
- [ ] Map visualization with Folium
- [ ] API endpoint development

**Medium Priority:**
- [ ] Frontend UI/UX improvements
- [ ] Test coverage
- [ ] Documentation
- [ ] Performance optimization

**See:** [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines

### Getting Started as a Contributor
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📖 Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Data Sources](docs/DATA_SOURCES.md)
- [API Documentation](docs/API.md)
- [Contributing Guidelines](CONTRIBUTING.md)

## 👥 Team

**Mentors:**
- Dr. Pradeeban Kathiravelu - pkathiravelu@alaska.edu
- Dr. David Moxley - dpmoxley@alaska.edu

**Contributors:**
- [Your name could be here!]

## 🔗 Links

- [Discussion Forum](https://github.com/KathiraveluLab/TENeT/discussions)
- [Alaska GSoC](https://github.com/uaanchorage/GSoC)
- [Issue Tracker](https://github.com/KathiraveluLab/TENeT/issues)

## 📄 License

[Apache License 2.0](LICENSE)

## 🙏 Acknowledgments

- Alaska GSoC Initiative
- University of Alaska Anchorage
- University of Alaska Fairbanks
- Alaska Developer Alliance
- Healthcare.gov for facility data
- FCC for broadband mapping data

## 📬 Contact

For questions or discussions:
- Open an issue
- Join our [discussion forum](https://github.com/KathiraveluLab/TENeT/discussions)
- Email: pkathiravelu@alaska.edu

---

**Built with ❤️ for Alaska's rural communities**

*Helping bring healthcare to those who need it most*
