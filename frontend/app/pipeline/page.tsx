"use client";

import { useEffect, useState } from "react";

type Card = { id: string; leadId: string; leadName: string; stage: string; notes: string };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STAGES = ["NEW", "CONTACTED", "PITCHED", "NEGOTIATING", "WON", "LOST"];

export default function PipelinePage() {
  const [cards, setCards] = useState<Card[]>([]);
  const [message, setMessage] = useState("Loading pipeline...");

  async function load() {
    const response = await fetch(`${API_URL}/api/pipeline/cards`, { credentials: "include" });
    const result = await response.json();
    if (!response.ok) {
      setMessage(result.error?.message ?? "Pipeline could not be loaded.");
      return;
    }
    setCards(result.items ?? []);
    setMessage(result.items?.length ? "" : "Add a lead to the pipeline from Discovery.");
  }

  useEffect(() => { void load(); }, []);

  async function move(card: Card, stage: string) {
    const response = await fetch(`${API_URL}/api/pipeline/cards/${card.id}/move`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage }),
    });
    if (response.ok) void load();
    else setMessage("The pipeline stage could not be updated.");
  }

  return (
    <main className="pipeline-page">
      <header className="discovery-header">
        <div><p className="eyebrow">Pipeline</p><h1>Move opportunities forward.</h1></div>
        <a className="primary-action" href="/discover">Discover leads</a>
      </header>
      {message && <p className="muted" role="status">{message}</p>}
      <div className="pipeline-board" aria-label="Lead pipeline">
        {STAGES.map((stage) => (
          <section className="pipeline-column" key={stage} aria-labelledby={`stage-${stage}`}>
            <h2 id={`stage-${stage}`}>{stage.replace("_", " ")}</h2>
            {cards.filter((card) => card.stage === stage).map((card) => (
              <article className="pipeline-card" key={card.id}>
                <strong>{card.leadName}</strong>
                <p>{card.notes || "No notes yet."}</p>
                <label>Move stage
                  <select value={card.stage} onChange={(event) => void move(card, event.target.value)}>
                    {STAGES.map((option) => <option key={option}>{option}</option>)}
                  </select>
                </label>
              </article>
            ))}
          </section>
        ))}
      </div>
    </main>
  );
}
