import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInAnonymously,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  type User,
} from 'firebase/auth'
import './App.css'
import { auth, firebaseConfigured, googleProvider } from './firebase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

type Recommendation = {
  card_id: number
  card_name: string
  score: number
  net_value: number
  applied_rule_ids: number[]
  reasons: string[]
  cap_remaining?: number | null
  warnings: string[]
}

type RecommendResponse = {
  best_card: Recommendation | null
  top_3: Recommendation[]
  explanations: string[]
}

type AuthMeResponse = {
  id: number
  email: string
  firebase_uid: string
}

const categoryOptions = ['DINING', 'TRAVEL', 'GROCERY', 'GAS', 'TRANSIT', 'STREAMING', 'ONLINE_SHOPPING', 'DRUGSTORE', 'OTHER']
const channelOptions = ['ONLINE', 'ANY', 'PORTAL', 'OTHER']
const countryOptions = ['US', 'CA', 'UK', 'IN', 'FR', 'SG']
type AuthMode = 'signin' | 'signup'

function formatDollars(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function App() {
  const [amount, setAmount] = useState('120')
  const [category, setCategory] = useState('DINING')
  const [country, setCountry] = useState('US')
  const [channel, setChannel] = useState('ONLINE')

  const [authUser, setAuthUser] = useState<User | null>(null)
  const [backendUser, setBackendUser] = useState<AuthMeResponse | null>(null)
  const [authMode, setAuthMode] = useState<AuthMode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authLoading, setAuthLoading] = useState(true)
  const [authSubmitting, setAuthSubmitting] = useState(false)
  const [loading, setLoading] = useState(false)
  const [authError, setAuthError] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<RecommendResponse | null>(null)

  useEffect(() => {
    if (!auth) {
      setAuthLoading(false)
      return
    }

    return onAuthStateChanged(auth, async (nextUser) => {
      setAuthUser(nextUser)
      setAuthError('')
      if (!nextUser) {
        setBackendUser(null)
        setAuthLoading(false)
        return
      }

      try {
        const token = await nextUser.getIdToken()
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!response.ok) {
          throw new Error(`Auth sync failed with ${response.status}`)
        }
        const data: AuthMeResponse = await response.json()
        setBackendUser(data)
      } catch (e) {
        setAuthError(e instanceof Error ? e.message : 'Unknown auth error')
      } finally {
        setAuthLoading(false)
      }
    })
  }, [])

  async function buildAuthHeaders(): Promise<Record<string, string>> {
    if (!authUser) {
      return {}
    }

    const token = await authUser.getIdToken()
    return { Authorization: `Bearer ${token}` }
  }

  async function handleSignIn() {
    if (!auth || !googleProvider) {
      return
    }

    setAuthError('')
    setAuthSubmitting(true)
    try {
      await signInWithPopup(auth, googleProvider)
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : 'Sign-in failed')
    } finally {
      setAuthSubmitting(false)
    }
  }

  async function handleEmailAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!auth) {
      return
    }

    setAuthError('')
    setAuthSubmitting(true)
    try {
      if (authMode === 'signup') {
        await createUserWithEmailAndPassword(auth, email.trim(), password)
      } else {
        await signInWithEmailAndPassword(auth, email.trim(), password)
      }
      setPassword('')
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : 'Email sign-in failed')
    } finally {
      setAuthSubmitting(false)
    }
  }

  async function handleGuestAccess() {
    if (!auth) {
      return
    }

    setAuthError('')
    setAuthSubmitting(true)
    try {
      await signInAnonymously(auth)
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : 'Guest sign-in failed')
    } finally {
      setAuthSubmitting(false)
    }
  }

  async function handleSignOut() {
    if (!auth) {
      return
    }

    await signOut(auth)
    setBackendUser(null)
    setResult(null)
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)

    const payload: Record<string, unknown> = {
      amount: Number(amount),
      category,
      country,
      channel,
    }

    try {
      const authHeaders = await buildAuthHeaders()
      const response = await fetch(`${API_BASE_URL}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(`Request failed with ${response.status}`)
      }

      const data: RecommendResponse = await response.json()
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app">
      <section className="hero panel">
        <div className="hero-copy">
          <p className="eyebrow">Explainable credit card recommender</p>
          <h1>Credit Wise</h1>
          <p className="hero-text">
            Compare reward value and FX cost before you swipe. The engine ranks live card rules from the database and explains
            the tradeoffs behind each pick.
          </p>
          <div className="hero-metrics">
            <div className="metric-pill">
              <span className="metric-label">Ranking model</span>
              <strong>Savings + fit score</strong>
            </div>
            <div className="metric-pill">
              <span className="metric-label">Identity</span>
              <strong>{authUser ? 'Firebase-backed wallet' : 'Guest recommend mode'}</strong>
            </div>
            <div className="metric-pill">
              <span className="metric-label">Outputs</span>
              <strong>Top 3 + rule reasons</strong>
            </div>
          </div>
        </div>

        <div className="auth-card">
          {!firebaseConfigured ? (
            <>
              <p className="auth-kicker">Authentication unavailable</p>
              <p className="warning">
                Firebase Auth is not configured for this build. Add the `VITE_FIREBASE_*` env vars to enable sign-in.
              </p>
            </>
          ) : authLoading ? (
            <>
              <p className="auth-kicker">Checking session</p>
              <p className="empty">Loading your sign-in state...</p>
            </>
          ) : authUser ? (
            <>
              <p className="auth-kicker">Wallet session</p>
              <div className="identity-block">
                <p className="identity-email">{authUser.isAnonymous ? 'Guest session' : authUser.email}</p>
                <div className="identity-meta">
                  <span className="status-badge success">
                    {authUser.isAnonymous ? 'Anonymous access' : authUser.providerData[0]?.providerId === 'password' ? 'Email account' : 'Google connected'}
                  </span>
                  {backendUser ? <span className="status-badge">Backend user #{backendUser.id}</span> : null}
                </div>
              </div>
              <p className="auth-copy">
                {authUser.isAnonymous
                  ? 'You can explore the recommender in guest mode and link to email or Google later if you want a persistent account.'
                  : 'Signed-in sessions let you keep a persistent identity as we expand wallet features.'}
              </p>
              <button className="ghost-button" type="button" onClick={handleSignOut}>Sign Out</button>
            </>
          ) : (
            <>
              <p className="auth-kicker">Personalize results</p>
              <p className="auth-copy">Choose a fast sign-in path. Google is quickest, email/password works as a normal account, and guest mode is low-friction for demos.</p>
              <div className="auth-actions">
                <button className="google-button" type="button" onClick={handleSignIn} disabled={authSubmitting}>Sign In with Google</button>
                <button className="ghost-button secondary" type="button" onClick={handleGuestAccess} disabled={authSubmitting}>Continue as Guest</button>
              </div>
              <div className="auth-divider"><span>or use email</span></div>
              <div className="auth-switch">
                <button
                  className={authMode === 'signin' ? 'mode-chip active' : 'mode-chip'}
                  type="button"
                  onClick={() => setAuthMode('signin')}
                >
                  Sign In
                </button>
                <button
                  className={authMode === 'signup' ? 'mode-chip active' : 'mode-chip'}
                  type="button"
                  onClick={() => setAuthMode('signup')}
                >
                  Create Account
                </button>
              </div>
              <form className="auth-form" onSubmit={handleEmailAuth}>
                <label className="field field-wide">
                  <span>Email</span>
                  <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" required />
                </label>
                <label className="field field-wide">
                  <span>Password</span>
                  <input
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    type="password"
                    autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'}
                    minLength={6}
                    required
                  />
                </label>
                <button className="primary-button auth-submit" type="submit" disabled={authSubmitting}>
                  {authSubmitting ? 'Working...' : authMode === 'signup' ? 'Create Email Account' : 'Sign In with Email'}
                </button>
              </form>
            </>
          )}
          {authError ? <p className="error">{authError}</p> : null}
        </div>
      </section>

      <section className="panel input-panel">
        <div className="section-heading">
          <div>
            <p className="section-kicker">Recommendation input</p>
            <h2>Find the best card for a transaction</h2>
          </div>
          <p className="section-note">Start with a spend scenario. We’ll rank the strongest matches from the live card catalog.</p>
        </div>
        <form className="form" onSubmit={onSubmit}>
          <label className="field">
            <span>Amount</span>
            <input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" min="1" step="0.01" />
          </label>
          <label className="field">
            <span>Category</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {categoryOptions.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Country</span>
            <select value={country} onChange={(e) => setCountry(e.target.value)}>
              {countryOptions.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Channel</span>
            <select value={channel} onChange={(e) => setChannel(e.target.value)}>
              {channelOptions.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
          </label>
          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? 'Ranking cards...' : 'Recommend Best Card'}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel result-panel">
        <div className="section-heading result-heading">
          <div>
            <p className="section-kicker">Decision output</p>
            <h2>Recommendation Result</h2>
          </div>
          {result?.best_card ? <p className="section-note">Best current pick: {result.best_card.card_name}</p> : null}
        </div>
        {!result ? (
          <div className="empty-state">
            <p className="empty-title">No recommendation yet</p>
            <p className="empty">Run a transaction through the engine to see ranked cards, rule matches, and warning flags.</p>
          </div>
        ) : (
          <>
            <div className="best">
              <h3>Best Card</h3>
              {result.best_card ? (
                <div className="hero-result">
                  <div className="hero-result-head">
                    <div>
                      <p className="result-label">Best match</p>
                      <h3>{result.best_card.card_name}</h3>
                    </div>
                    <span className="status-badge highlight brand-chip">
                      Rule {result.best_card.applied_rule_ids[0] ?? 'N/A'}
                    </span>
                  </div>
                  <div className="stat-row">
                    <div className="stat-card">
                      <span className="stat-label">Estimated savings</span>
                      <strong>{formatDollars(result.best_card.net_value)}</strong>
                    </div>
                    <div className="stat-card">
                      <span className="stat-label">Card score</span>
                      <strong>{result.best_card.score.toFixed(1)}/10</strong>
                    </div>
                  </div>
                  <p className="best-reason">{result.best_card.reasons.join(' · ')}</p>
                  {result.best_card.warnings.length > 0 ? (
                    <ul className="warning-list">
                      {result.best_card.warnings.map((warning, index) => (
                        <li key={`best-${index}`}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : (
                <p>No card found.</p>
              )}
            </div>
            <div className="result-grid">
              <div className="list">
                <h3>Top 3</h3>
                <div className="rank-list">
                  {result.top_3.map((card, index) => (
                    <article key={card.card_id} className="item">
                      <div className="item-head">
                        <span className="rank-pill">#{index + 1}</span>
                        <div>
                          <h4>{card.card_name}</h4>
                          <p className="item-reason">{card.reasons.join(', ')}</p>
                        </div>
                      </div>
                      <div className="item-stats">
                        <span>Saves {formatDollars(card.net_value)}</span>
                        <span>Score {card.score.toFixed(1)}/10</span>
                        <span>Rule {card.applied_rule_ids[0] ?? 'N/A'}</span>
                      </div>
                      {card.warnings.length > 0 ? (
                        <ul className="warning-list">
                          {card.warnings.map((warning, warningIndex) => (
                            <li key={`${card.card_id}-${warningIndex}`}>{warning}</li>
                          ))}
                        </ul>
                      ) : null}
                    </article>
                  ))}
                </div>
              </div>
              <div className="explanations">
                <h3>Decision Notes</h3>
                <ul>
                  {result.explanations.map((line, index) => (
                    <li key={index}>{line}</li>
                  ))}
                </ul>
              </div>
            </div>
          </>
        )}
      </section>
    </main>
  )
}

export default App
