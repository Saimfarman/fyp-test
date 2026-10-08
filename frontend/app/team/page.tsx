"use client";

import { FormEvent, useEffect, useState } from "react";
import { API_URL } from "../lib/api";

type Member = { id: string; email: string; role: string };
type Workspace = { id: string; name: string; role: string };

export default function TeamPage() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("sales");
  const [message, setMessage] = useState("Loading team...");

  async function load() {
    const workspaces = await fetch(`${API_URL}/api/workspaces`, { credentials: "include" });
    const result = await workspaces.json();
    const current = result.items?.[0] as Workspace | undefined;
    if (!workspaces.ok || !current) { setMessage(result.error?.message ?? "Sign in to manage a team."); return; }
    setWorkspace(current);
    const response = await fetch(`${API_URL}/api/workspaces/${current.id}/members`, { credentials: "include" });
    const data = await response.json();
    setMembers(data.items ?? []);
    setMessage(response.ok ? "" : data.error?.message ?? "Members could not be loaded.");
  }
  useEffect(() => { void load(); }, []);

  async function invite(event: FormEvent) {
    event.preventDefault();
    if (!workspace) return;
    const response = await fetch(`${API_URL}/api/workspaces/${workspace.id}/invitations`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, role }),
    });
    const data = await response.json();
    setMessage(response.ok ? `Invitation created. Share this token with ${email}: ${data.inviteToken}` : data.error?.message ?? "Invitation failed.");
    if (response.ok) setEmail("");
  }

  return <main className="section-page"><header className="page-heading"><div><p className="eyebrow">Workspace</p><h1>Your team.</h1><p className="muted">Invite collaborators and assign work with clear roles.</p></div></header>
    <div className="settings-grid"><section className="panel settings-card"><h2>Invite member</h2><form onSubmit={invite}><label>Email<input type="email" required value={email} onChange={event => setEmail(event.target.value)} placeholder="teammate@example.com" /></label><label>Role<select value={role} onChange={event => setRole(event.target.value)}><option value="sales">Sales / BD</option><option value="manager">Manager</option><option value="developer">Developer</option></select></label><button className="primary-action" type="submit">Create invitation</button></form>{message && <p className="notice" role="status">{message}</p>}</section>
      <section className="panel settings-card"><h2>Members</h2>{members.length ? <ul className="simple-list">{members.map(member => <li key={member.id}><span><strong>{member.email}</strong><small>{member.role}</small></span><span className="status-chip">{member.role}</span></li>)}</ul> : <p className="muted">No members loaded yet.</p>}</section></div></main>;
}
