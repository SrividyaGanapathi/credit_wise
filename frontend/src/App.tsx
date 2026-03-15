import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { onAuthStateChanged, signInWithPopup, signOut, type User } from 'firebase/auth'
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

type UsageLogResponse = {
  id: number
  user_id: number
  rule_id: number
  period_start: string
  spent_amount: number
  cap_amount?: number | null
  cap_remaining?: number | null
}

type AuthMeResponse = {
  id: number
  email: string
  firebase_uid: string
}

function App() {
  const [amount, setAmount] = useState('120')
  const [category, setCategory] = useState('DINING')
  const [country, setCountry] = useState('US')
  const [channel, setChannel] = useState('ONLINE')

  const [usageRuleId, setUsageRuleId] = useState('')
  const [usageAmount, setUsageAmount] = useState('')
  const [usagePeriodStart, setUsagePeriodStart] = useState('')

  const [authUser, setAuthUser] = useState<User | null>(null)
  const [backendUser, setBackendUser] = useState<AuthMeResponse | null>(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [loading, setLoading] = useState(false)
  const [usageLoading, setUsageLoading] = useState(false)
  const [authError, setAuthError] = useState('')
  const [error, setError] = useState('')
  const [usageError, setUsageError] = useState('')
  const [result, setResult] = useState<RecommendResponse | null>(null)
  const [usageResult, setUsageResult] = useState<UsageLogResponse | null>(null)

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
    try {
      await signInWithPopup(auth, googleProvider)
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : 'Sign-in failed')
    }
  }

  async function handleSignOut() {
    if (!auth) {
      return
    }

    await signOut(auth)
    setBackendUser(null)
    setResult(null)
    setUsageResult(null)
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
      if (data.best_card?.applied_rule_ids?.length) {
        setUsageRuleId(String(data.best_card.applied_rule_ids[0]))
      }
      setUsageAmount(amount)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  async function onUsageSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setUsageLoading(true)
    setUsageError('')

    const payload: Record<string, unknown> = {
      rule_id: Number(usageRuleId),
      amount: Number(usageAmount),
    }
    if (usagePeriodStart.trim()) payload.period_start = usagePeriodStart

    try {
      const authHeaders = await buildAuthHeaders()
      const response = await fetch(`${API_BASE_URL}/usage/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        throw new Error(`Usage log failed with ${response.status}`)
      }

      const data: UsageLogResponse = await response.json()
      setUsageResult(data)
    } catch (e) {
      setUsageError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setUsageLoading(false)
    }
  }

  return (
    <main className="app">
      <section className="panel auth-panel">
        <h1>Credit Wise</h1>
        <p className="subtitle">Recommend cards with cap and FX-aware net value.</p>
        {!firebaseConfigured ? (
          <p className="warning">
            Firebase Auth is not configured for this build. Add the `VITE_FIREBASE_*` env vars to enable sign-in.
          </p>
        ) : authLoading ? (
          <p className="empty">Checking sign-in status...</p>
        ) : authUser ? (
          <div className="auth-box">
            <p>Signed in as {authUser.email}</p>
            {backendUser ? <p>Backend user #{backendUser.id}</p> : null}
            <button type="button" onClick={handleSignOut}>Sign Out</button>
          </div>
        ) : (
          <div className="auth-box">
            <p>Sign in with Google to keep wallet and usage tracking user-specific.</p>
            <button type="button" onClick={handleSignIn}>Sign In with Google</button>
          </div>
        )}
        {authError ? <p className="error">{authError}</p> : null}
      </section>

      <section className="panel">
        <h2>Recommend</h2>
        <form className="form" onSubmit={onSubmit}>
          <label>
            Amount
            <input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" min="1" step="0.01" />
          </label>
          <label>
            Category
            <input value={category} onChange={(e) => setCategory(e.target.value)} />
          </label>
          <label>
            Country
            <input value={country} onChange={(e) => setCountry(e.target.value)} />
          </label>
          <label>
            Channel
            <input value={channel} onChange={(e) => setChannel(e.target.value)} />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? 'Running...' : 'Recommend'}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="panel">
        <h2>Usage Log</h2>
        <p className="subtitle">Log spend to update cap tracking before recommending again.</p>
        <form className="form" onSubmit={onUsageSubmit}>
          <label>
            Rule ID
            <input value={usageRuleId} onChange={(e) => setUsageRuleId(e.target.value)} type="number" min="1" required />
          </label>
          <label>
            Amount
            <input value={usageAmount} onChange={(e) => setUsageAmount(e.target.value)} type="number" min="0.01" step="0.01" required />
          </label>
          <label>
            Period Start (optional YYYY-MM-DD)
            <input value={usagePeriodStart} onChange={(e) => setUsagePeriodStart(e.target.value)} placeholder="2026-03-01" />
          </label>
          <button type="submit" disabled={usageLoading || (!authUser && firebaseConfigured)}>
            {usageLoading ? 'Logging...' : 'Log Usage'}
          </button>
        </form>
        {!authUser && firebaseConfigured ? (
          <p className="warning">Sign in first to log usage against your own reward caps.</p>
        ) : null}
        {usageError ? <p className="error">{usageError}</p> : null}
        {usageResult ? (
          <div className="usage-result">
            <p>Logged: {usageResult.spent_amount.toFixed(2)}</p>
            <p>Period: {usageResult.period_start}</p>
            <p>
              Cap Remaining:{' '}
              {usageResult.cap_remaining === null || usageResult.cap_remaining === undefined
                ? 'N/A'
                : usageResult.cap_remaining.toFixed(2)}
            </p>
          </div>
        ) : null}
      </section>

      <section className="panel result-panel">
        <h2>Recommendation Result</h2>
        {!result ? (
          <p className="empty">Submit a transaction to see recommendations.</p>
        ) : (
          <>
            <div className="best">
              <h3>Best Card</h3>
              {result.best_card ? (
                <div>
                  <p>{result.best_card.card_name}</p>
                  <p>Net Value: {result.best_card.net_value.toFixed(2)}</p>
                  <p>Score: {result.best_card.score.toFixed(2)}</p>
                  <p>
                    Cap Remaining:{' '}
                    {result.best_card.cap_remaining === null || result.best_card.cap_remaining === undefined
                      ? 'N/A'
                      : result.best_card.cap_remaining.toFixed(2)}
                  </p>
                  <p>Primary Rule ID: {result.best_card.applied_rule_ids[0] ?? 'N/A'}</p>
                </div>
              ) : (
                <p>No card found.</p>
              )}
            </div>
            <div className="list">
              <h3>Top 3</h3>
              {result.top_3.map((card) => (
                <article key={card.card_id} className="item">
                  <h4>{card.card_name}</h4>
                  <p>Net Value: {card.net_value.toFixed(2)}</p>
                  <p>Score: {card.score.toFixed(2)}</p>
                  <p>Reason: {card.reasons.join(', ')}</p>
                  {card.warnings.length > 0 ? (
                    <ul>
                      {card.warnings.map((warning, index) => (
                        <li key={`${card.card_id}-${index}`}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                </article>
              ))}
            </div>
            <div className="explanations">
              <h3>Explanations</h3>
              <ul>
                {result.explanations.map((line, index) => (
                  <li key={index}>{line}</li>
                ))}
              </ul>
            </div>
          </>
        )}
      </section>
    </main>
  )
}

export default App
