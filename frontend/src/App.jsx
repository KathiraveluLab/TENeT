import React from 'react'
import DashboardLayout from './layout/DashboardLayout'
import './styles/App.css'

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>TENeT</h1>
        <p>Telehealth Network Tool - Alaska</p>
      </header>
      <main className="app-main">
        <DashboardLayout />
      </main>
    </div>
  )
}

export default App