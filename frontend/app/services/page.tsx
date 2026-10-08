"use client";

import { FormEvent, useEffect, useState } from "react";
import { API_URL } from "../lib/api";
type Service = { id: string; name: string; description: string; unitPrice: number; currency: string; active: boolean };
export default function ServicesPage() {
  const [items, setItems] = useState<Service[]>([]); const [name, setName] = useState(""); const [price, setPrice] = useState("0"); const [message, setMessage] = useState("Loading catalog...");
  async function load() { const r = await fetch(`${API_URL}/api/service-catalog`, { credentials: "include" }); const x = await r.json(); setItems(x.items ?? []); setMessage(r.ok ? "" : x.error?.message ?? "Catalog could not be loaded."); }
  useEffect(() => { void load(); }, []);
  async function add(event: FormEvent) { event.preventDefault(); const r = await fetch(`${API_URL}/api/service-catalog`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, unitPrice: Number(price) }) }); const x = await r.json(); setMessage(r.ok ? "Service added." : x.error?.message ?? "Service could not be added."); if (r.ok) { setName(""); setPrice("0"); void load(); } }
  async function remove(id: string) { await fetch(`${API_URL}/api/service-catalog/${id}`, { method: "DELETE", credentials: "include" }); void load(); }
  return <main className="section-page"><header className="page-heading"><div><p className="eyebrow">Catalog</p><h1>Services & packages.</h1><p className="muted">Keep your offers and PKR pricing consistent across every proposal.</p></div></header><section className="panel settings-card"><h2>Add a service</h2><form className="inline-form" onSubmit={add}><input required placeholder="Website build" value={name} onChange={e => setName(e.target.value)} /><input type="number" min="0" placeholder="Price in PKR" value={price} onChange={e => setPrice(e.target.value)} /><button className="primary-action">Add service</button></form></section><section className="catalog-grid">{items.map(item => <article className="catalog-card" key={item.id}><span>PKR</span><h2>{item.name}</h2><p className="muted">{item.description || "No description yet."}</p><strong>PKR {item.unitPrice.toLocaleString()}</strong><button className="secondary-action" onClick={() => void remove(item.id)}>Archive</button></article>)}{!items.length && <p className="empty-state">{message || "Add your first service."}</p>}</section></main>;
}
