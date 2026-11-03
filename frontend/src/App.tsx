<<<<<<< HEAD
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
=======
﻿import { useState, type FormEvent } from 'react'
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
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

<<<<<<< HEAD
type GoogleCredentialResponse = {
  credential: string
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (options: {
            client_id: string
            callback: (response: GoogleCredentialResponse) => void
            auto_select: boolean
            cancel_on_tap_outside: boolean
          }) => void
          renderButton: (
            element: HTMLElement,
            options: {
              theme: 'outline'
              size: 'large'
              text: 'continue_with'
              shape: 'rectangular'
              width: number
            },
          ) => void
        }
      }
    }
  }
}

=======
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
function Login({
  onLogin,
}: {
  onLogin: (token: string) => void
}) {
<<<<<<< HEAD
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [googleClientId, setGoogleClientId] = useState('')
  const [googleScriptLoaded, setGoogleScriptLoaded] = useState(false)
  const [googleScriptError, setGoogleScriptError] = useState(false)
  const googleButtonRef = useRef<HTMLDivElement>(null)
  const googleCallbackRef = useRef<(credential: string) => void>(() => {})

  const saveTokens = useCallback((
    response: { data: { access?: string } },
  ) => {
    const access = response.data.access
    if (!access) {
      throw new Error('No access token received')
    }

    localStorage.setItem('aks_token', access)
    onLogin(access)
  }, [onLogin])

  const loginWithGoogle = useCallback(async (credential: string) => {
    setLoading(true)
    setError('')

    try {
      const response = await axios.post(`${API}/auth/google/`, {
        credential,
      })
      saveTokens(response)
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Google sign-in failed. Try again.',
      )
    } finally {
      setLoading(false)
    }
  }, [saveTokens])

  useEffect(() => {
    googleCallbackRef.current = (credential) => {
      void loginWithGoogle(credential)
    }
  }, [loginWithGoogle])

  useEffect(() => {
    let active = true
    axios.get(`${API}/auth/google/config/`)
      .then((response) => {
        if (active) {
          setGoogleClientId(response.data.client_id || '')
        }
      })
      .catch(() => {
        if (active) {
          setGoogleClientId('')
        }
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    if (!googleClientId) {
      return
    }

    const scriptId = 'google-identity-services'
    let script = document.getElementById(scriptId) as HTMLScriptElement | null
    let createdScript = false

    const initializeGoogle = () => {
      if (!window.google || !googleButtonRef.current) {
        return
      }

      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: (response) => {
          if (response.credential) {
            googleCallbackRef.current(response.credential)
          }
        },
        auto_select: false,
        cancel_on_tap_outside: true,
      })
      googleButtonRef.current.replaceChildren()
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        shape: 'rectangular',
        width: Math.min(350, googleButtonRef.current.clientWidth || 350),
      })
      setGoogleScriptLoaded(true)
    }

    if (!script) {
      script = document.createElement('script')
      script.id = scriptId
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      createdScript = true
    }

    script.addEventListener('load', initializeGoogle)
    script.addEventListener('error', () => setGoogleScriptError(true))
    document.head.appendChild(script)

    if (window.google) {
      initializeGoogle()
    }

    return () => {
      script?.removeEventListener('load', initializeGoogle)
      if (createdScript) {
        script?.remove()
      }
    }
  }, [googleClientId])
=======
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d

  const login = async (e: FormEvent) => {
    e.preventDefault()

    setLoading(true)
    setError('')

    try {
<<<<<<< HEAD
      if (mode === 'register') {
        const response = await axios.post(`${API}/auth/register/`, {
          username,
          email,
          password,
          password_confirm: passwordConfirm,
        })
        saveTokens(response)
      } else {
        const response = await axios.post(`${API}/auth/token/`, {
          username,
          password,
        })
        saveTokens(response)
      }
    } catch (err: any) {
      const data = err?.response?.data
      const fieldError = data && Object.values(data)
        .flat()
        .find((value) => typeof value === 'string')
      setError(
        (typeof fieldError === 'string' && fieldError) ||
          data?.detail ||
          err?.message ||
          (mode === 'register'
            ? 'Registration failed. Check your details.'
            : 'Login failed. Check username and password.'),
=======
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
>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
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

<<<<<<< HEAD
        <div className="auth-mode-tabs" role="tablist" aria-label="Account access">
          <button
            aria-selected={mode === 'login'}
            className={mode === 'login' ? 'active' : ''}
            onClick={() => {
              setMode('login')
              setError('')
            }}
            role="tab"
            type="button"
          >
            Sign in
          </button>
          <button
            aria-selected={mode === 'register'}
            className={mode === 'register' ? 'active' : ''}
            onClick={() => {
              setMode('register')
              setError('')
            }}
            role="tab"
            type="button"
          >
            Create account
          </button>
        </div>

        <form onSubmit={login}>
          {mode === 'register' && (
            <>
              <label htmlFor="register-email">Email</label>
              <input
                autoComplete="email"
                id="register-email"
                onChange={(e) => setEmail(e.target.value)}
                required
                type="email"
                value={email}
              />
            </>
          )}

          <label htmlFor="auth-username">Username</label>
          <input
            autoComplete={mode === 'register' ? 'username' : 'username'}
            id="auth-username"
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
            required
            value={username}
          />

          <label htmlFor="auth-password">Password</label>
          <input
            autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
            id="auth-password"
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            required
            type="password"
            value={password}
          />

          {mode === 'register' && (
            <>
              <label htmlFor="auth-password-confirm">Confirm password</label>
              <input
                autoComplete="new-password"
                id="auth-password-confirm"
                onChange={(e) => setPasswordConfirm(e.target.value)}
                required
                type="password"
                value={passwordConfirm}
              />
            </>
          )}

          {error && <div className="alert error" role="alert">{error}</div>}

=======
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

>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
          <button
            className="primary-button"
            disabled={loading}
            type="submit"
          >
<<<<<<< HEAD
            {loading
              ? mode === 'register' ? 'Creating account...' : 'Signing in...'
              : mode === 'register' ? 'Create account' : 'Sign In'}
          </button>
        </form>

        <div className="auth-divider"><span>or</span></div>
        {googleClientId ? (
          <div
            aria-label="Continue with Google"
            className={`google-sign-in ${loading || !googleScriptLoaded ? 'loading' : ''}`}
            ref={googleButtonRef}
          />
        ) : (
          <p className="google-config-note">
            Google sign-in is unavailable until an administrator configures
            GOOGLE_CLIENT_ID.
          </p>
        )}
        {googleScriptError && (
          <p className="google-config-note">
            Google sign-in could not load. Check your network connection.
          </p>
        )}

=======
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
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
          <Route path="/" element={<Overview token={token} />} />
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


<<<<<<< HEAD
=======


>>>>>>> 32e82354c709145cb1b25fa9ae0911d3f7b8107d
