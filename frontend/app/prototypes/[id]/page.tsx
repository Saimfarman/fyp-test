"use client";

import { useEffect, useState } from "react";

type Section = { id: string; type: string; heading: string; subheading?: string; cta?: string; body?: string; items?: string[] };
type Prototype = { id: string; lead: { name: string }; templateId: string; content: { theme: { primary: string; accent: string }; sections: Section[] } };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function PrototypePage({ params }: { params: Promise<{ id: string }> }) {
  const [prototype, setPrototype] = useState<Prototype | null>(null);
  const [message, setMessage] = useState("Loading prototype...");
  const [device, setDevice] = useState<"desktop" | "tablet" | "mobile">("desktop");

  useEffect(() => {
    params.then(({ id }) => fetch(`${API_URL}/api/prototypes/${id}`, { credentials: "include" })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.error?.message ?? "Prototype could not be loaded.");
        setPrototype(result);
      }).catch((error) => setMessage(error instanceof Error ? error.message : "Prototype could not be loaded.")));
  }, [params]);

  async function updateSection(section: Section, field: string, value: string) {
    if (!prototype) return;
    const sections = prototype.content.sections.map((item) => item.id === section.id ? { ...item, [field]: value } : item);
    const response = await fetch(`${API_URL}/api/prototypes/${prototype.id}`, { method: "PATCH", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sections }) });
    const result = await response.json();
    if (response.ok) setPrototype(result);
    else setMessage(result.error?.message ?? "Prototype update failed.");
  }

  if (!prototype) return <main className="prototype-page"><p className="muted">{message}</p></main>;
  const frameClass = `preview-frame ${device}`;
  return <main className="prototype-page">
    <header className="prototype-header"><div><p className="eyebrow">Prototype studio</p><h1>{prototype.lead.name}</h1><p className="muted">Editable {prototype.templateId} template with sanitized text fields.</p></div><div className="device-switcher">{(["desktop", "tablet", "mobile"] as const).map((item) => <button className={device === item ? "active" : ""} key={item} onClick={() => setDevice(item)}>{item}</button>)}</div></header>
    <div className="prototype-layout">
      <section className="prototype-editor"><h2>Content editor</h2>{prototype.content.sections.map((section) => <div className="editor-card" key={section.id}><label>{section.id} heading<input value={section.heading} maxLength={160} onChange={(event) => updateSection(section, "heading", event.target.value)} /></label>{section.subheading !== undefined && <label>Subheading<textarea value={section.subheading} maxLength={300} onChange={(event) => updateSection(section, "subheading", event.target.value)} /></label>}{section.body !== undefined && <label>Body<textarea value={section.body} maxLength={400} onChange={(event) => updateSection(section, "body", event.target.value)} /></label>}</div>)}</section>
      <section className="prototype-preview"><div className={frameClass}><iframe title="Prototype preview" src={`${API_URL}/api/prototypes/${prototype.id}/preview`} /></div><div className="prototype-actions"><a className="primary-action" href={`${API_URL}/api/prototypes/${prototype.id}/export`} onClick={(event) => { event.preventDefault(); fetch(`${API_URL}/api/prototypes/${prototype.id}/export`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ framework: "html" }) }).then((response) => response.blob()).then((blob) => { const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "leadpitch-prototype.zip"; link.click(); URL.revokeObjectURL(url); }); }}>Download HTML project ZIP</a></div></section>
    </div>
  </main>;
}
