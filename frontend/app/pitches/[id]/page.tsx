"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Pitch = {
  id: string;
  title: string;
  lead: { id: string; name: string };
  english: { opening: string; body: string; value: string; callToAction: string };
  urdu: { opening: string; body: string; value: string; callToAction: string };
  recommendations: { phase: string; title: string; description: string; priority: string }[];
  scope: string[];
  timeline: string;
  terms: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function PitchPage({ params }: { params: Promise<{ id: string }> }) {
  const [pitch, setPitch] = useState<Pitch | null>(null);
  const [message, setMessage] = useState("Loading pitch...");
  const [shareUrl, setShareUrl] = useState("");
  const router = useRouter();

  useEffect(() => {
    params.then(({ id }) => fetch(`${API_URL}/api/pitches/${id}`, { credentials: "include" })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.error?.message ?? "Pitch could not be loaded.");
        setPitch(result);
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "Pitch could not be loaded.")));
  }, [params]);

  if (!pitch) return <main className="pitch-page"><p className="muted">{message}</p></main>;
  const pitchId = pitch.id;
  const leadId = pitch.lead.id;
  async function createShare() {
    const response = await fetch(`${API_URL}/api/pitches/${pitchId}/share`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expiresInDays: 30 }) });
    const result = await response.json();
    if (!response.ok) {
      setMessage(result.error?.message ?? "Share link could not be created.");
      return;
    }

    setShareUrl(`${window.location.origin}/share/${result.token}`);
  }

  async function createPrototype() {
    const response = await fetch(`${API_URL}/api/leads/${leadId}/prototypes`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ templateId: "local-service" }),
    });
    const result = await response.json();
    if (response.ok) router.push(`/prototypes/${result.id}`);
    else setMessage(result.error?.message ?? "Prototype could not be created.");
  }

  return (
    <main className="pitch-page">
      <p className="eyebrow">Pitch builder</p>
      <h1>{pitch.title}</h1>
      <p className="muted">Prepared for {pitch.lead.name}. Review the fact-grounded copy before sharing.</p>
      <section className="pitch-card">
        <h2>English outreach</h2>
        <p><strong>{pitch.english.opening}</strong></p>
        <p>{pitch.english.body}</p><p>{pitch.english.value}</p><p>{pitch.english.callToAction}</p>
      </section>
      <section className="pitch-card">
        <h2>Urdu outreach</h2>
        <p dir="rtl">{pitch.urdu.opening}</p><p dir="rtl">{pitch.urdu.body}</p><p dir="rtl">{pitch.urdu.value}</p><p dir="rtl">{pitch.urdu.callToAction}</p>
      </section>
      <section className="pitch-card">
        <h2>Recommended plan</h2>
        {pitch.recommendations.map((item) => <div className="recommendation-row" key={item.title}><strong>{item.phase}: {item.title}</strong><span>{item.description}</span></div>)}
        <p><strong>Scope:</strong> {pitch.scope.join(" · ")}</p><p><strong>Timeline:</strong> {pitch.timeline}</p><p className="muted">{pitch.terms}</p>
      </section>
      <div className="pitch-actions"><a className="primary-action" href={`${API_URL}/api/pitches/${pitch.id}/pdf`}>Download proposal PDF</a> <button className="primary-action" onClick={createShare}>Create 30-day share link</button> <button className="primary-action" onClick={createPrototype}>Create prototype</button></div>
      {shareUrl && <p className="share-result"><strong>Share link:</strong> <a href={shareUrl}>{shareUrl}</a></p>}
    </main>
  );
}
