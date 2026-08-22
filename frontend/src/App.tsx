import { useState, type FormEvent } from 'react'
import axios from 'axios'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import './App.css'

import DashboardLayout from './layouts/DashboardLayout'

import Overview from './pages/Overview'
import Cameras from './pages/Cameras'
import Tracking from './pages/Tracking'
import Detections from './pages/Detections'
import Events from './pages/Events'
import Alerts from './pages/Alerts'
import Persons from './pages/Persons'
import Vehicles from './pages/Vehicles'
import Settings from './pages/Settings'
import Recordings from './pages/Recordings'

const API = '/api'

function Login({
  onLogin,
}: {
  onLogin: (token: string) => void
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const login = async (e: FormEvent) => {
    e.preventDefault()

    setLoading(true)
    setError('')

    try {
      const response = await axios.post(`${API}/auth/token/`, {
        username,
        password,
      })

      const access = response.data.access

      if (!access) {
        throw new Error('No access token received')
      }

      localStorage.setItem('aks_token', access)
      onLogin(access)
    } catch (err: any) {
      console.error('LOGIN ERROR:', err)

      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Login failed. Check username and password.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="brand-mark">AX</div>

        <h1>AKS VisionX</h1>

        <p className="subtitle">
          Intelligent Camera Monitoring & AI Surveillance
        </p>

        <form onSubmit={login}>
          <label>Username</label>

          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
            autoComplete="username"
            required
          />

          <label>Password</label>

          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            placeholder="Enter password"
            autoComplete="current-password"
            required
          />

          {error && (
            <div className="alert error">
              {error}
            </div>
          )}

          <button
            className="primary-button"
            disabled={loading}
            type="submit"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="login-footer">
          AKS VisionX • Secure Monitoring Platform
        </div>
      </div>
    </div>
  )
}

function App() {
  const [token, setToken] = useState(
    localStorage.getItem('aks_token') || '',
  )

  const logout = () => {
    localStorage.removeItem('aks_token')
    setToken('')
  }

  if (!token) {
    return <Login onLogin={setToken} />
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <DashboardLayout onLogout={logout} />
          }
        >
          <Route path="/" element={<Overview />} />
          <Route path="/cameras" element={<Cameras />} />
          <Route path="/recordings" element={<Recordings />} />
          <Route path="/tracking" element={<Tracking />} />
          <Route path="/detections" element={<Detections />} />
          <Route path="/events" element={<Events />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/persons" element={<Persons />} />
          <Route path="/vehicles" element={<Vehicles />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App




