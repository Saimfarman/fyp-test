"use client";

import { useEffect, useState } from "react";
import { API_URL } from "../lib/api";
type Report = { leads: number; pipeline: Record<string, number>; topCategories: Record<string, number>; topCities: Record<string, number> };
export default function ReportsPage() {
  const [report, setReport] = useState<Report | null>(null); const [message, setMessage] = useState("Loading reports...");
  useEffect(() => { fetch(`${API_URL}/api/reports/overview`, { credentials: "include" }).then(r => r.json().then(x => { if (!r.ok) setMessage(x.error?.message ?? "Reports could not be loaded."); else { setReport(x); setMessage(""); } })).catch(() => setMessage("Reports could not be loaded.")); }, []);
  const entries = (values: Record<string, number> | undefined) => Object.entries(values ?? {}).map(([key, value]) => <li key={key}><span>{key}</span><strong>{value}</strong></li>);
  return <main className="section-page"><header className="page-heading"><div><p className="eyebrow">Insights</p><h1>Performance reports.</h1><p className="muted">Understand where your opportunities and wins come from.</p></div><a className="secondary-action" href={`${API_URL}/api/exports/leads.csv`}>Export leads CSV</a></header>{report ? <div className="reports-grid"><section className="panel settings-card"><h2>Funnel</h2><ul className="simple-list">{entries(report.pipeline)}</ul></section><section className="panel settings-card"><h2>Top categories</h2><ul className="simple-list">{entries(report.topCategories)}</ul></section><section className="panel settings-card"><h2>Top areas</h2><ul className="simple-list">{entries(report.topCities)}</ul></section><section className="panel settings-card"><h2>Total leads</h2><div className="metric-value">{report.leads}</div><p className="muted">All discovered businesses in this workspace.</p></section></div> : <p className="notice" role="status">{message}</p>}</main>;
}
