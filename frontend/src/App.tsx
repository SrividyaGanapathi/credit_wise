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
  is_anonymous: boolean
}

type CardCatalogItem = {
  id: number
  issuer: string
  name: string
  network: string
  annual_fee: number
  fx_fee_bps: number
}

type WalletCard = {
  id: number
  user_id: number
  card_id: number
  nickname: string
  is_active: boolean
  card_name: string
  network: string
}

type RecommendationMode = 'wallet' | 'catalog'

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

function buildRequestId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `req-${Date.now()}`
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
  const [walletLoading, setWalletLoading] = useState(false)
  const [walletSavingCardId, setWalletSavingCardId] = useState<number | null>(null)
  const [catalogSearch, setCatalogSearch] = useState('')
  const [issuerFilter, setIssuerFilter] = useState('All issuers')
  const [recommendationMode, setRecommendationMode] = useState<RecommendationMode>('catalog')
  const [authError, setAuthError] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState<RecommendResponse | null>(null)
  const [latestRequestId, setLatestRequestId] = useState<string | null>(null)
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null)
  const [walletCards, setWalletCards] = useState<WalletCard[]>([])
  const [catalogCards, setCatalogCards] = useState<CardCatalogItem[]>([])

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
        setWalletCards([])
        setCatalogCards([])
        setRecommendationMode('catalog')
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

        if (!data.is_anonymous) {
          setRecommendationMode('wallet')
          setWalletLoading(true)
          const [walletResponse, cardsResponse] = await Promise.all([
            fetch(`${API_BASE_URL}/users/me/cards`, {
              headers: { Authorization: `Bearer ${token}` },
            }),
            fetch(`${API_BASE_URL}/cards`),
          ])
          if (walletResponse.ok) {
            const walletData: WalletCard[] = await walletResponse.json()
            setWalletCards(walletData)
          }
          if (cardsResponse.ok) {
            const cardsData: CardCatalogItem[] = await cardsResponse.json()
            setCatalogCards(cardsData)
          }
        } else {
          setWalletCards([])
          setRecommendationMode('catalog')
        }
      } catch (e) {
        setAuthError(e instanceof Error ? e.message : 'Unknown auth error')
      } finally {
        setWalletLoading(false)
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

  function getAuthMode(): string {
    if (!authUser) {
      return 'unauthenticated'
    }
    if (authUser.isAnonymous || backendUser?.is_anonymous) {
      return 'guest'
    }
    const providerId = authUser.providerData[0]?.providerId
    if (providerId === 'password') {
      return 'email'
    }
    if (providerId === 'google.com') {
      return 'google'
    }
    return 'authenticated'
  }

  async function logRecommendationEvent(payload: Record<string, unknown>) {
    try {
      const authHeaders = await buildAuthHeaders()
      await fetch(`${API_BASE_URL}/events/recommendation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
    } catch {
      // Event logging should not block core recommendation UX.
    }
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
    setWalletCards([])
    setResult(null)
  }

  async function refreshWallet() {
    const authHeaders = await buildAuthHeaders()
    const response = await fetch(`${API_BASE_URL}/users/me/cards`, {
      headers: authHeaders,
    })
    if (!response.ok) {
      throw new Error(`Wallet fetch failed with ${response.status}`)
    }
    const walletData: WalletCard[] = await response.json()
    setWalletCards(walletData)
  }

  async function handleAddCard(card: CardCatalogItem) {
    setAuthError('')
    setWalletSavingCardId(card.id)
    try {
      const authHeaders = await buildAuthHeaders()
      const response = await fetch(`${API_BASE_URL}/users/me/cards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({
          card_id: card.id,
          nickname: card.name,
          is_active: true,
        }),
      })

      if (!response.ok) {
        throw new Error(`Add card failed with ${response.status}`)
      }

      await refreshWallet()
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : 'Unable to add card')
    } finally {
      setWalletSavingCardId(null)
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    setSelectedCardId(null)

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
        body: JSON.stringify({
          ...payload,
          recommendation_mode: effectiveRecommendationMode,
        }),
      })

      if (!response.ok) {
        throw new Error(`Request failed with ${response.status}`)
      }

      const data: RecommendResponse = await response.json()
      setResult(data)
      const requestId = buildRequestId()
      setLatestRequestId(requestId)
      void logRecommendationEvent({
        event_type: 'impression',
        request_id: requestId,
        auth_mode: getAuthMode(),
        amount: Number(amount),
        category,
        country,
        channel,
        recommended_card_ids: data.top_3.map((card) => card.card_id),
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  function handleCardSelection(card: Recommendation, rank: number) {
    setSelectedCardId(card.card_id)
    if (!latestRequestId) {
      return
    }

    void logRecommendationEvent({
      event_type: 'selection',
      request_id: latestRequestId,
      auth_mode: getAuthMode(),
      amount: Number(amount),
      category,
      country,
      channel,
      recommended_card_ids: result?.top_3.map((item) => item.card_id) ?? [card.card_id],
      selected_card_id: card.card_id,
      selected_rank: rank,
    })
  }

  const canUseWalletMode = Boolean(authUser && !authUser.isAnonymous && backendUser && walletCards.length > 0)
  const effectiveRecommendationMode: RecommendationMode = canUseWalletMode && recommendationMode === 'wallet' ? 'wallet' : 'catalog'
  const requiresWalletSetup = Boolean(authUser && !authUser.isAnonymous && backendUser && walletCards.length === 0 && recommendationMode === 'wallet')
  const availableCatalogCards = catalogCards.filter((card) => !walletCards.some((walletCard) => walletCard.card_id === card.id))
  const normalizedSearch = catalogSearch.trim().toLowerCase()
  const issuerOptions = ['All issuers', ...new Set(availableCatalogCards.map((card) => card.issuer))]
  const filteredCatalogCards = availableCatalogCards.filter((card) => {
    const matchesSearch =
      normalizedSearch.length === 0
      || `${card.issuer} ${card.name} ${card.network}`.toLowerCase().includes(normalizedSearch)
    const matchesIssuer = issuerFilter === 'All issuers' || card.issuer === issuerFilter
    return matchesSearch && matchesIssuer
  })
  const groupedCatalogCards = filteredCatalogCards.reduce<Record<string, CardCatalogItem[]>>((groups, card) => {
    const bucket = groups[card.issuer] ?? []
    bucket.push(card)
    groups[card.issuer] = bucket
    return groups
  }, {})

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
              <strong>{effectiveRecommendationMode === 'wallet' ? 'Firebase-backed wallet' : 'Full catalog browse mode'}</strong>
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
                  : 'Signed-in sessions keep a persistent wallet. You can recommend from your saved cards or switch to the full catalog anytime.'}
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
          <p className="section-note">
            {requiresWalletSetup
              ? 'Add at least one card to start in wallet mode, or skip setup for now and browse the full catalog.'
              : effectiveRecommendationMode === 'wallet'
                ? 'Start with a spend scenario. We’ll rank the strongest match from your saved cards.'
                : 'Start with a spend scenario. We’ll rank the strongest matches from the full card catalog.'}
          </p>
        </div>
        {authUser && !authUser.isAnonymous ? (
          <div className="wallet-strip">
            <div>
              <p className="wallet-title">Your wallet</p>
              <p className="wallet-copy">
                {walletLoading
                  ? 'Loading your saved cards...'
                  : walletCards.length > 0
                    ? `${walletCards.length} card${walletCards.length === 1 ? '' : 's'} ready for personalized recommendations.`
                    : 'No cards saved yet. Add your cards below, or browse the full catalog until you finish setup.'}
              </p>
            </div>
            <div className="mode-toggle" role="tablist" aria-label="Recommendation mode">
              <button
                className={effectiveRecommendationMode === 'wallet' ? 'mode-chip mode-chip-light active' : 'mode-chip mode-chip-light'}
                type="button"
                onClick={() => setRecommendationMode('wallet')}
                disabled={!canUseWalletMode}
              >
                My Wallet
              </button>
              <button
                className={effectiveRecommendationMode === 'catalog' ? 'mode-chip mode-chip-light active' : 'mode-chip mode-chip-light'}
                type="button"
                onClick={() => setRecommendationMode('catalog')}
              >
                Full Catalog
              </button>
            </div>
            {walletCards.length > 0 ? (
              <div className="wallet-chip-row">
                {walletCards.map((card) => (
                  <span key={card.id} className="wallet-chip">{card.card_name}</span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {requiresWalletSetup ? (
          <div className="wallet-onboarding">
            <div className="section-heading">
              <div>
                <p className="section-kicker">New user setup</p>
                <h3>Add your cards</h3>
              </div>
              <p className="section-note">Pick the cards you already have. We’ll use that wallet for personalized recommendations, but you can still browse the full catalog while you decide.</p>
            </div>
            <div className="onboarding-toolbar">
              <label className="field">
                <span>Search cards</span>
                <input
                  value={catalogSearch}
                  onChange={(e) => setCatalogSearch(e.target.value)}
                  type="text"
                  placeholder="Search issuer, card, or network"
                />
              </label>
              <label className="field">
                <span>Issuer</span>
                <select value={issuerFilter} onChange={(e) => setIssuerFilter(e.target.value)}>
                  {issuerOptions.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              </label>
              <button className="ghost-button onboarding-skip" type="button" onClick={() => setRecommendationMode('catalog')}>
                Skip for now and browse all cards
              </button>
            </div>
            {Object.keys(groupedCatalogCards).length > 0 ? (
              <div className="issuer-groups">
                {Object.entries(groupedCatalogCards).map(([issuer, cards]) => (
                  <section key={issuer} className="issuer-group">
                    <div className="issuer-group-header">
                      <h4>{issuer}</h4>
                      <span>{cards.length} option{cards.length === 1 ? '' : 's'}</span>
                    </div>
                    <div className="catalog-grid">
                      {cards.map((card) => (
                        <article key={card.id} className="catalog-card">
                          <div>
                            <h4>{card.name}</h4>
                            <p>{card.network} · Annual fee ${card.annual_fee} · FX fee {card.fx_fee_bps} bps</p>
                          </div>
                          <button
                            className="primary-button catalog-button"
                            type="button"
                            onClick={() => handleAddCard(card)}
                            disabled={walletSavingCardId === card.id}
                          >
                            {walletSavingCardId === card.id ? 'Adding...' : 'Add to Wallet'}
                          </button>
                        </article>
                      ))}
                    </div>
                  </section>
                ))}
              </div>
            ) : (
              <p className="empty">No cards match the current search and issuer filter.</p>
            )}
          </div>
        ) : null}
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
          <button className="primary-button" type="submit" disabled={loading || requiresWalletSetup}>
            {loading ? 'Ranking cards...' : requiresWalletSetup ? 'Add Cards to Continue' : 'Recommend Best Card'}
          </button>
        </form>
        {requiresWalletSetup ? <p className="warning">You are in wallet mode. Add a card above, or switch to Full Catalog to explore without saving cards yet.</p> : null}
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
                    <article
                      key={card.card_id}
                      className={selectedCardId === card.card_id ? 'item item-selected' : 'item'}
                      onClick={() => handleCardSelection(card, index + 1)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault()
                          handleCardSelection(card, index + 1)
                        }
                      }}
                    >
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
                      <p className="item-hint">Click to mark this as the card you would choose.</p>
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
