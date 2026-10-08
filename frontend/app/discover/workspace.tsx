"use client";

import { FormEvent, useMemo, useState } from "react";
import dynamic from "next/dynamic";
const LeadMap = dynamic(() => import("./lead-map"), { ssr: false });

type Lead = {
  id: string;
  name: string;
  category?: string;
  address?: string;
  phone?: string;
  latitude: number;
  longitude: number;
  websiteUrl?: string;
  status: string;
  severity: string;
  rating?: number;
  reviewCount?: number;
};

type Audit = {
  overallScore: number;
  severity: string;
  severityReasons: string[];
  categoryScores: Record<string, number>;
  issueCount: number;
};

type Pitch = {
  id: string;
  title: string;
  language: string;
  english: { opening: string; body: string; value: string; callToAction: string };
  urdu: { opening: string; body: string; value: string; callToAction: string };
  recommendations: { phase: string; title: string; description: string; priority: string }[];
  timeline: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const statusLabels: Record<string, string> = {
  NO_WEBSITE: "No website",
  SOCIAL_ONLY: "Social only",
  DEAD_SITE: "Dead site",
  HAS_WEBSITE: "Website live",
};

function severityClass(severity: string) {
  return severity.toLowerCase();
}

export default function DiscoveryWorkspace() {
  const [query, setQuery] = useState("shop");
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("Search OpenStreetMap to populate this workspace.");
  const [audit, setAudit] = useState<Audit | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [pitch, setPitch] = useState<Pitch | null>(null);
  const [pitchLoading, setPitchLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [categoryFilter, setCategoryFilter] = useState("");

  const visibleLeads = useMemo(() => leads.filter((lead) => severityFilter === "ALL" || lead.severity === severityFilter).slice(0, 100), [leads, severityFilter]);

  async function search(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("Querying OpenStreetMap...");
    try {
      const response = await fetch(`${API_URL}/api/discovery/search`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      if (!response.ok) throw new Error("Search failed. Sign in and try again.");
      const result = await response.json();
      const params = new URLSearchParams();
      if (severityFilter !== "ALL") params.set("severity", severityFilter);
      if (statusFilter !== "ALL") params.set("status", statusFilter);
      if (categoryFilter) params.set("category", categoryFilter);
      window.history.replaceState(null, "", `/discover?${params.toString()}`);
      const listResponse = await fetch(`${API_URL}/api/leads?${params.toString()}`, { credentials: "include" });
      if (!listResponse.ok) throw new Error("Leads could not be loaded.");
      const list = await listResponse.json();
      setLeads(list.items ?? []);
      setMessage(`${result.count} businesses added. Select a lead to inspect it.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Search failed.");
    } finally {
      setLoading(false);
    }

  }

  async function runAudit() {
    if (!selected) return;
    setAuditLoading(true);
    setAudit(null);
    try {
      const response = await fetch(`${API_URL}/api/leads/${selected.id}/audit`, {
        method: "POST",
        credentials: "include",
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error?.message ?? "Audit failed.");
      setAudit(result);
      setMessage(`Audit completed for ${selected.name}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Audit failed.");
    } finally {
      setAuditLoading(false);
    }

  }

  async function generatePitch() {
    if (!selected) return;
    setPitchLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/leads/${selected.id}/pitches`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: "both" }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error?.message ?? "Pitch generation failed.");
      setPitch(result);
      setMessage(`Pitch draft created for ${selected.name}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Pitch generation failed.");
    } finally {
      setPitchLoading(false);
    }

  }

  async function saveToPipeline() {
    if (!selected) return;
    const response = await fetch(`${API_URL}/api/leads/${selected.id}/pipeline`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ stage: "NEW" }) });
    setMessage(response.ok ? `${selected.name} was saved to your pipeline.` : "The lead could not be saved to your pipeline.");
  }

  return (
    <main className="discovery-shell">
      <header className="discovery-header">
        <div>
          <p className="eyebrow">Discover</p>
          <h1>Find businesses you can help.</h1>
        </div>
        <form onSubmit={search} className="search-form">
          <label htmlFor="query">Category or keyword</label>
          <div className="search-row">
            <input id="query" value={query} onChange={(event) => setQuery(event.target.value)} />
            <button type="submit" disabled={loading}>{loading ? "Searching..." : "Search area"}</button>
          </div>
        </form>
        <div className="filter-row"><label className="filter-control">Severity<select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}><option value="ALL">All severities</option><option>CRITICAL</option><option>HIGH</option><option>MEDIUM</option><option>LOW</option><option>UNSCANNED</option></select></label><label className="filter-control">Website<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="ALL">All statuses</option><option value="NO_WEBSITE">No website</option><option value="SOCIAL_ONLY">Social only</option><option value="DEAD_SITE">Dead site</option><option value="HAS_WEBSITE">Website live</option></select></label><label className="filter-control">Category<input value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} placeholder="e.g. salon" /></label></div>
        <a className="secondary-action" href="/pipeline">Pipeline</a>
      </header>
      <div className="discovery-layout">
        <aside className="lead-list" aria-label="Lead list">
          <div className="list-heading"><strong>{leads.length} leads</strong><span>{message}</span></div>
          {visibleLeads.map((lead) => (
            <button key={lead.id} className={`lead-row ${selected?.id === lead.id ? "selected" : ""}`} onClick={() => setSelected(lead)}>
              <span className={`severity-dot ${severityClass(lead.severity)}`} aria-hidden="true" />
              <span><strong>{lead.name}</strong><small>{lead.category ?? "Local business"} · {statusLabels[lead.status] ?? lead.status}</small></span>
            </button>
          ))}
          {!leads.length && <p className="empty-state">Your discovered businesses will appear here.</p>}
        </aside>
        <section className="map-surface" aria-label="Discovery map">{leads.length ? <LeadMap leads={leads} selectedId={selected?.id} onSelect={setSelected} /> : <div className="map-empty"><strong>Your map starts here.</strong><span>Search a category to discover nearby businesses.</span></div>}</section>
        <aside className={`lead-detail ${selected ? "open" : ""}`} aria-label="Lead details">
          {selected ? <>
            <p className={`severity-label ${severityClass(selected.severity)}`}>{selected.severity}</p>
            <h2>{selected.name}</h2>
            <p className="muted">{selected.category ?? "Local business"} · {statusLabels[selected.status] ?? selected.status}</p>
            <div className="score-bars"><span><i style={{ width: selected.severity === "CRITICAL" ? "92%" : selected.severity === "HIGH" ? "72%" : "46%" }} />Opportunity need</span><span><i style={{ width: `${Math.min(100, (selected.reviewCount ?? 0) / 2)}%` }} />Review reach</span></div>
            <dl>
              <dt>Address</dt><dd>{selected.address || "Not listed in OpenStreetMap"}</dd>
              <dt>Rating</dt><dd>{selected.rating ? `${selected.rating}/5 (${selected.reviewCount ?? 0} reviews)` : "Not available"}</dd>
              <dt>Website</dt><dd>{selected.websiteUrl ? <a href={selected.websiteUrl} target="_blank" rel="noreferrer">{selected.websiteUrl}</a> : "No website listed"}</dd>
            </dl>
            <button className="primary-action" onClick={runAudit} disabled={auditLoading || selected.status === "NO_WEBSITE" || selected.status === "SOCIAL_ONLY"}>{auditLoading ? "Auditing..." : "Run website audit"}</button>
            <div className="detail-actions"><button className="secondary-action" onClick={saveToPipeline}>Save to pipeline</button><a className="secondary-action" href={`tel:${selected.phone ?? ""}`}>Call</a>{selected.websiteUrl && <a className="secondary-action" href={selected.websiteUrl} target="_blank" rel="noreferrer">Open site</a>}</div>
            {audit && <section className="audit-summary" aria-live="polite">
              <div className="audit-score"><strong>{audit.overallScore}</strong><span>/100 audit score</span></div>
              <p className={`severity-label ${severityClass(audit.severity)}`}>{audit.severity} opportunity</p>
              {audit.severityReasons.map((reason) => <p className="muted" key={reason}>{reason}</p>)}
              <div className="score-bars">{Object.entries(audit.categoryScores).map(([category, score]) => <div className="score-bar" key={category}><span>{category}</span><span>{score}</span><i><b style={{ width: `${score}%` }} /></i></div>)}</div>
              <p className="muted">{audit.issueCount} prioritized issues found. Detailed fixes are available through the audit API.</p>
            </section>}
            <button className="primary-action secondary-action" onClick={generatePitch} disabled={pitchLoading}>{pitchLoading ? "Creating pitch..." : "Generate bilingual pitch"}</button>
            {pitch && <section className="pitch-preview" aria-live="polite">
              <p className="eyebrow">Pitch draft</p>
              <h3>{pitch.title}</h3>
              <p><strong>{pitch.english.opening}</strong></p>
              <p className="muted">{pitch.english.body}</p>
              <p className="muted">{pitch.english.callToAction}</p>
              <div className="recommendation-list">
                {pitch.recommendations.map((item) => <div key={item.title}><strong>{item.phase}: {item.title}</strong><span>{item.description}</span></div>)}
              </div>
              <p className="muted">{pitch.timeline}</p>
              <a className="text-link" href={`/pitches/${pitch.id}`}>Open pitch builder</a>
            </section>}
          </> : <p className="empty-state">Choose a pin or lead to see details.</p>}
        </aside>
      </div>
    </main>
  );
}
