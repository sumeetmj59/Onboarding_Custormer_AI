// src/App.jsx
import React, { useState } from 'react';
import { evaluateNetwork } from './api';

const REGIONS = ['APAC', 'EMEA', 'NA', 'LATAM'];
const CLOUD_PROVIDERS = ['AWS', 'Azure', 'GCP', 'On-prem'];
const TRAFFIC_LEVELS = ['low', 'medium', 'high'];
const COMPLIANCE = ['PCI-DSS', 'ISO27001', 'SOC2', 'HIPAA'];

function Badge({ decision }) {
  const color =
    decision === 'approve'
      ? 'bg-approve'
      : decision === 'reject'
      ? 'bg-reject'
      : 'bg-review';

  return (
    <span className={`badge ${color}`}>
      {decision ? decision.replace('_', ' ') : 'pending'}
    </span>
  );
}

export default function App() {
  // form state
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [regions, setRegions] = useState([]);
  const [trafficLevel, setTrafficLevel] = useState('medium');
  const [cloudProviders, setCloudProviders] = useState([]);
  const [criticalApps, setCriticalApps] = useState('Online banking portal');
  const [hasWaf, setHasWaf] = useState(true);
  const [hasMfa, setHasMfa] = useState(true);
  const [loggingStrategy, setLoggingStrategy] = useState('centralized SIEM');
  const [compliance, setCompliance] = useState(['PCI-DSS']);

  // result state
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // helpers
  const toggleInList = (list, value, setter) => {
    if (list.includes(value)) {
      setter(list.filter(v => v !== value));
    } else {
      setter([...list, value]);
    }
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const payload = {
        company_name: companyName || 'Unknown',
        industry: industry || 'Unknown',
        contact_email: contactEmail || 'security@example.com',
        regions,
        traffic_level: trafficLevel,
        cloud_providers: cloudProviders,
        critical_apps: criticalApps
          .split(',')
          .map(s => s.trim())
          .filter(Boolean),
        has_waf: hasWaf,
        has_mfa_for_admins: hasMfa,
        logging_strategy: loggingStrategy,
        compliance,
      };

      const res = await evaluateNetwork(payload);
      setResult(res);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="topbar">
        <div className="logo-dot" />
        <div>
          <h1>Customer Network Onboarding</h1>
          <p className="subtitle">Prototype – AI-assisted intake for Imperva-style onboarding</p>
        </div>
      </header>

      <main className="layout">
        {/* Left: form */}
        <section className="card form-card">
          <h2>Network Request Form</h2>
          <p className="card-subtitle">
            Capture all the key details for a new customer environment. This is what your
            brother’s team would normally review manually.
          </p>

          <form onSubmit={handleSubmit} className="form-grid">
            <div className="field">
              <label>Company name</label>
              <input
                type="text"
                value={companyName}
                onChange={e => setCompanyName(e.target.value)}
                placeholder="Demo Bank"
              />
            </div>

            <div className="field">
              <label>Industry</label>
              <input
                type="text"
                value={industry}
                onChange={e => setIndustry(e.target.value)}
                placeholder="Financial services"
              />
            </div>

            <div className="field">
              <label>Contact email</label>
              <input
                type="email"
                value={contactEmail}
                onChange={e => setContactEmail(e.target.value)}
                placeholder="security@demobank.com"
              />
            </div>

            <div className="field">
              <label>Regions in scope</label>
              <div className="pill-row">
                {REGIONS.map(r => (
                  <button
                    key={r}
                    type="button"
                    className={`pill ${regions.includes(r) ? 'pill-selected' : ''}`}
                    onClick={() => toggleInList(regions, r, setRegions)}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label>Traffic level</label>
              <div className="pill-row">
                {TRAFFIC_LEVELS.map(l => (
                  <button
                    key={l}
                    type="button"
                    className={`pill ${trafficLevel === l ? 'pill-selected' : ''}`}
                    onClick={() => setTrafficLevel(l)}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label>Cloud providers</label>
              <div className="pill-row">
                {CLOUD_PROVIDERS.map(c => (
                  <button
                    key={c}
                    type="button"
                    className={`pill ${cloudProviders.includes(c) ? 'pill-selected' : ''}`}
                    onClick={() => toggleInList(cloudProviders, c, setCloudProviders)}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>

            <div className="field">
              <label>Critical applications</label>
              <textarea
                rows={2}
                value={criticalApps}
                onChange={e => setCriticalApps(e.target.value)}
                placeholder="Online banking portal, internal trading platform"
              />
              <small>Separate multiple apps with commas.</small>
            </div>

            <div className="field inline">
              <label>Web Application Firewall (WAF) in place?</label>
              <input
                type="checkbox"
                checked={hasWaf}
                onChange={e => setHasWaf(e.target.checked)}
              />
            </div>

            <div className="field inline">
              <label>MFA enforced for admin accounts?</label>
              <input
                type="checkbox"
                checked={hasMfa}
                onChange={e => setHasMfa(e.target.checked)}
              />
            </div>

            <div className="field">
              <label>Logging / monitoring strategy</label>
              <input
                type="text"
                value={loggingStrategy}
                onChange={e => setLoggingStrategy(e.target.value)}
                placeholder="Centralized SIEM with 1-year retention"
              />
            </div>

            <div className="field">
              <label>Compliance frameworks</label>
              <div className="pill-row">
                {COMPLIANCE.map(c => (
                  <button
                    key={c}
                    type="button"
                    className={`pill ${compliance.includes(c) ? 'pill-selected' : ''}`}
                    onClick={() => toggleInList(compliance, c, setCompliance)}
                  >
                    {c}
                  </button>
                ))}
              </div>
            </div>

            <div className="actions">
              <button className="primary-btn" type="submit" disabled={loading}>
                {loading ? 'Evaluating…' : 'Evaluate with AI'}
              </button>
            </div>
          </form>
        </section>

        {/* Right: result */}
        <section className="card result-card">
          <h2>Risk Evaluation</h2>

          {!result && !error && (
            <p className="muted">
              Fill the form on the left and click <strong>Evaluate with AI</strong> to see the
              onboarding decision, risk score, and key issues.
            </p>
          )}

          {error && (
            <div className="alert error">
              <strong>Request failed:</strong> {error}
            </div>
          )}

          {result && (
            <>
              <div className="result-header">
                <Badge decision={result.decision} />
                <div className="score">
                  <span className="score-label">Risk score</span>
                  <span className="score-value">{result.risk_score}/100</span>
                </div>
              </div>

              <div className="issues">
                <h3>Key issues</h3>
                {result.issues && result.issues.length > 0 ? (
                  <ul>
                    {result.issues.map((issue, idx) => (
                      <li key={idx}>{issue}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">No major issues detected.</p>
                )}
              </div>

              <div className="summary">
                <h3>Summary</h3>
                <p>{result.summary}</p>
              </div>

              <div className="footer-note">
                <small>
                  *This is a prototype. In the real Imperva flow, this output would be attached to
                  the onboarding ticket and stored next to the customer’s network definition.
                </small>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}