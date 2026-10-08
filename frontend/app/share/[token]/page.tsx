"use client";

import { useEffect, useState } from "react";

type PublicPitch = {
  title: string;
  lead: { name: string };
  english: { opening: string; body: string; value: string; callToAction: string };
  recommendations: { phase: string; title: string; description: string }[];
  scope: string[];
  timeline: string;
  terms: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function PublicSharePage({ params }: { params: Promise<{ token: string }> }) {
  const [pitch, setPitch] = useState<PublicPitch | null>(null);
  const [message, setMessage] = useState("Loading proposal...");

  useEffect(() => {
    params.then(({ token }) => fetch(`${API_URL}/api/share/${token}`)
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.error?.message ?? "This proposal is unavailable.");
        setPitch(result.pitch);
      })
      .catch((error) => setMessage(error instanceof Error ? error.message : "This proposal is unavailable.")));
  }, [params]);

  if (!pitch) return <main className="pitch-page"><p className="muted">{message}</p></main>;
  return (
    <main className="pitch-page">
      <p className="eyebrow">A practical growth proposal</p>
      <h1>{pitch.title}</h1>
      <p className="muted">Prepared for {pitch.lead.name}</p>
      <section className="pitch-card">
        <p><strong>{pitch.english.opening}</strong></p>
        <p>{pitch.english.body}</p>
        <p>{pitch.english.value}</p>
        <p>{pitch.english.callToAction}</p>
      </section>
      <section className="pitch-card">
        <h2>Recommended plan</h2>
        {pitch.recommendations.map((item) => <div className="recommendation-row" key={item.title}><strong>{item.phase}: {item.title}</strong><span>{item.description}</span></div>)}
        <p><strong>Scope:</strong> {pitch.scope.join(" · ")}</p>
        <p><strong>Timeline:</strong> {pitch.timeline}</p>
        <p className="muted">{pitch.terms}</p>
      </section>
    </main>
  );
}
