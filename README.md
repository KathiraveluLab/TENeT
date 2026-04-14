# TENeT: Telehealth Effectiveness and Necessity Tracker (+Alaska)

TENeT is a full-stack geospatial web application that maps healthcare deficits alongside internet capability across Alaskan cities and villages to identify where telehealth deployment is most urgent and most viable.

## 📁 Project Structure

```text
TENeT/
├── frontend/               # React + TypeScript (Vite, Leaflet, Recharts)
│   ├── src/                # UI components and map visualization logic
│   └── Dockerfile          # Frontend container definition
├── backend/                # Python (FastAPI)
│   ├── app/                # API routes and core services
│   └── Dockerfile          # Backend container definition
├── pipeline/               # Data Ingestion & Processing (Pandas, GeoPandas)
│   ├── ingest.py           # Queries healthsites.io and FCC data
│   ├── process.py          # Computes the Healthcare Desert Index (HDI)
│   └── Dockerfile          # Pipeline execution container
├── data/                   # Data storage (Git ignored)
│   ├── raw/                # Original GeoJSON and CSV datasets
│   └── processed/          # Normalized and computed HDI outputs
├── docs/                   # Documentation and research findings
├── docker-compose.yml      # Orchestrates all services
└── README.md
```

## ⚙️ Configuration

### 1. API Keys
The data pipeline requires access to external APIs. Create a `.env` file in the root or set the following environment variables:
- `HEALTHSITES_API_KEY`: Required for fetching healthcare facility data from healthsites.io.

### 2. Data Persistence
The `data/` directory is mounted as a volume across the `backend` and `pipeline` services to allow seamless sharing of processed GeoJSON files.

## 🚀 Setup and Start Commands

### Prerequisites
- [Docker](https://www.docker.com/get-started) and Docker Compose installed.
- (Optional) Python 3.11+ for local pipeline development.

### Step 1: Clone and Environment Setup
```bash
git clone <repository-url>
cd TENeT
# Add your API key
echo "HEALTHSITES_API_KEY=your_key_here" >> .env
```

### Step 2: Initialize Data (Run Ingestion)
The pipeline service is configured to run scripts that fetch and process data. You can run the ingestion script manually via Docker:
```bash
docker-compose run pipeline python ingest.py
```
This will generate `data/raw/alaska_healthsites.geojson`.

### Step 3: Start the Full Stack
Use Docker Compose to build and start the frontend and backend services:
```bash
docker-compose up --build
```

- **Frontend**: Accessible at `http://localhost:5173`
- **Backend API**: Accessible at `http://localhost:8000`
- **API Docs**: Swagger UI available at `http://localhost:8000/docs`

### Step 4: Local Frontend Development (Without Docker)
If you prefer to run the frontend locally for faster hot-reloading:
```bash
cd frontend
npm install
npm run dev
```

## 📊 Data Quality Findings
Our initial analysis reveals a significant **coverage gap in remote Western Alaska**. Public datasets from healthsites.io often miss tribal clinics and village-level health aides. Future phases will integrate ANTHC records and FCC broadband maps to provide a more accurate Healthcare Desert Index (HDI).
