# TENeT Frontend

React frontend for the Telehealth Effectiveness & Necessity Tracker.

## Features

- Interactive Alaska map with Leaflet
- Community markers color-coded by data completeness
- Detailed community information panel
- Data confidence indicators
- Explicit handling of missing data
- Loading states and error handling

## Quick Start

```bash
# Install dependencies
npm install

# Copy environment template (optional)
cp .env.example .env

# Start development server
npm run dev
```

Open http://localhost:5173

## Prerequisites

- Node.js (version 16 or higher)
- npm or yarn

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser to `http://localhost:5173`

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── components/
│   └── MapView.jsx          # Main map component
├── styles/
│   ├── index.css            # Base styles
│   ├── App.css              # App layout styles
│   └── map.css              # Map-specific styles
├── App.jsx                  # Main application component
└── main.jsx                 # Application entry point
```

## Map Features

- Centered on Alaska with appropriate zoom level
- Alaska boundary visualization with GeoJSON
- Interactive popups with state information
- Responsive design for mobile devices
- OpenStreetMap tiles with proper attribution

## Future Development

This base map is prepared for:
- Healthcare facility markers
- Broadband availability visualization
- Telehealth feasibility metrics
- Interactive filters and controls
- Data integration with backend API

## Environment Variables

- `VITE_API_URL` - Backend API URL (default: http://localhost:5000)
- `VITE_DEFAULT_ZOOM` - Default map zoom level
- `VITE_ALASKA_LAT` - Alaska center latitude
- `VITE_ALASKA_LNG` - Alaska center longitude