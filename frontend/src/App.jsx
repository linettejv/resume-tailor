import { useEffect, useState } from 'react'

const VERDICT_LABEL = {
  apply: 'Apply',
  apply_with_caveats: 'Apply with caveats',
  skip: 'Skip',
}

const TOOL_LABEL = {
  get_profile: 'Read your fact bank',
  check_bullets: 'Checked draft bullets',
  submit_tailored_resume: 'Submitted resume',
}

function useElapsed(running) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!running) return
    setSeconds(0)
    const id = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [running])
  return seconds
}

export default function App() {
  const [label, setLabel] = useState('')
  const [jd, setJd] = useState('')
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [trends, setTrends] = useState(null)
  const elapsed = useElapsed(loading)

  async function loadTrends() {
    try {
      const res = await fetch('/api/trends?days=30')
      if (res.ok) setTrends(await res.json())
    } catch {
      // trends are a nice-to-have; ignore if the backend is down
    }
  }

  useEffect(() => {
    loadTrends()
  }, [])

  async function tailor(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setData(null)
    try {
      const res = await fetch('/api/tailor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_description: jd, label }),
      })
      const body = await res.json()
      if (body.trace) setData(body) // show the trace even when the agent failed
      if (!res.ok) setError(body.error || `Request failed (${res.status})`)
    } catch {
      setError("Couldn't reach the backend. Is Flask running on port 5001?")
    } finally {
      setLoading(false)
      loadTrends()
    }
  }

  const sub = data?.submission

  return (
    <div className="page">
      <header>
        <h1>Resume Tailor</h1>
        <p className="muted">
          Paste a job description. The agent checks your fit and rewrites your resume using only facts
          from <code>experience.yaml</code>.
        </p>
      </header>

      <main className="grid">
        <form className="card input" onSubmit={tailor}>
          <label>
            Company and role <span className="muted">(used in the file name)</span>
            <input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Razorpay frontend"
            />
          </label>
          <label>
            Job description
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job description from LinkedIn, Wellfound or InstaHire…"
              rows={18}
            />
          </label>
          <button disabled={loading || jd.trim().length < 100}>
            {loading ? `Tailoring… ${elapsed}s` : 'Tailor my resume'}
          </button>
          {jd.trim().length > 0 && jd.trim().length < 100 && (
            <p className="muted small">Paste the full description (at least 100 characters).</p>
          )}
        </form>

        <section className="results">
          {error && <div className="card error">{error}</div>}
          {trends && trends.jobs > 0 && <MarketPulse t={trends} />}

          {!data && !error && !loading && (
            <div className="card empty muted">Your fit check and tailored resume will show up here.</div>
          )}
          {loading && <div className="card empty muted">The agent is reading your profile and the job…</div>}

          {sub && (
            <>
              <div className={`card verdict ${sub.verdict}`}>
                <div className="verdict-row">
                  <span className="badge">{VERDICT_LABEL[sub.verdict]}</span>
                </div>
                <div className="scores">
                  <Score label="Skills fit" hint="your current skills vs this job" value={sub.fit_score} />
                  <Score
                    label="Interest fit"
                    hint="does this job move you where you want to go?"
                    value={sub.interest_alignment.score}
                  />
                </div>
                <p>{sub.verdict_reason}</p>
                <p className="muted small">
                  {sub.interest_alignment.notes}
                  {sub.interest_alignment.matched_interests.length > 0 &&
                    ` Grows: ${sub.interest_alignment.matched_interests.join(', ')}.`}
                </p>
                {data.files && (
                  <div className="downloads">
                    {data.files.pdf && <a className="btn" href={`/api/files/${data.files.pdf}`}>Download PDF</a>}
                    <a className="btn secondary" href={`/api/files/${data.files.tex}`}>Download .tex (Overleaf)</a>
                  </div>
                )}
              </div>

              <div className="two">
                <div className="card">
                  <h2>Matches</h2>
                  <ul className="plain">
                    {sub.matched_requirements.map((m) => (
                      <li key={m.requirement}>
                        <strong>{m.requirement}</strong>
                        <div className="chips">
                          {m.fact_ids.map((f) => <span key={f} className="chip" title={data.facts[f]}>{f}</span>)}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="card">
                  <h2>Gaps</h2>
                  {sub.gaps.length ? (
                    <ul>{sub.gaps.map((g) => <li key={g}>{g}</li>)}</ul>
                  ) : (
                    <p className="muted">No gaps found.</p>
                  )}
                  {sub.skills_to_learn.length > 0 && (
                    <>
                      <h2>Skills to learn</h2>
                      <div className="chips">
                        {sub.skills_to_learn.map((s) => <span key={s} className="chip learn">{s}</span>)}
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div className="card">
                <h2>Summary</h2>
                <p>{sub.summary}</p>
                <h2>Skills, in order</h2>
                <div className="chips">{sub.skills.map((s) => <span key={s} className="chip">{s}</span>)}</div>
              </div>

              <div className="card">
                <h2>Tailored bullets</h2>
                <ol className="bullets">
                  {sub.bullets.map((b, i) => (
                    <li key={i}>
                      <span className="section">{b.section_id}</span>
                      <p>{b.text}</p>
                      <p className="source">Based on: {b.fact_ids.map((f) => data.facts[f]).join(' · ')}</p>
                    </li>
                  ))}
                </ol>
              </div>
            </>
          )}

          {data?.trace && (
            <div className="card">
              <h2>What the agent did</h2>
              <ol className="trace">
                {data.trace.map((t, i) => (
                  <li key={i} className={t.is_error ? 'bad' : ''}>
                    <span className="turn">Turn {t.turn}</span>
                    {TOOL_LABEL[t.tool] || t.tool}
                    {t.is_error && <span className="rejected">rejected, retried</span>}
                  </li>
                ))}
              </ol>
              <p className="muted small">
                {data.turns} turns · {data.tokens.input.toLocaleString()} input + {data.tokens.output.toLocaleString()} output
                tokens · {data.seconds}s · {data.stopped_reason}
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

function Score({ label, hint, value }) {
  const level = value >= 70 ? 'high' : value >= 45 ? 'mid' : 'low'
  return (
    <div className={`score-block ${level}`}>
      <div className="score-head">
        <span>{label}</span>
        <span className="score">{value}<small>/100</small></span>
      </div>
      <div className="meter"><div style={{ width: `${value}%` }} /></div>
      <p className="muted small">{hint}</p>
    </div>
  )
}

function MarketPulse({ t }) {
  const max = Math.max(...t.top_skills_to_learn.map((s) => s.jobs), 1)
  return (
    <div className="card pulse">
      <h2>Market pulse · last {t.days} days</h2>
      <p className="small muted">
        {t.jobs} {t.jobs === 1 ? 'job' : 'jobs'} checked · avg skills fit {t.avg_fit} · avg interest fit {t.avg_interest}
        {' · '}
        {Object.entries(t.verdicts).map(([v, n]) => `${n} ${VERDICT_LABEL[v].toLowerCase()}`).join(', ')}
      </p>
      {t.top_skills_to_learn.length > 0 ? (
        <>
          <p className="small"><strong>Skills you don't have yet that keep coming up:</strong></p>
          <ul className="bars">
            {t.top_skills_to_learn.map((s) => (
              <li key={s.skill}>
                <span className="bar-label">{s.skill}</span>
                <span className="bar"><span style={{ width: `${(s.jobs / max) * 100}%` }} /></span>
                <span className="bar-count">{s.jobs} of {t.jobs}</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="small muted">No missing skills across these jobs.</p>
      )}
    </div>
  )
}
