"use client";
import { FormEvent, useState } from "react";
import Link from "next/link";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export default function LoginPage() {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [message, setMessage] = useState("");
  async function submit(event: FormEvent) { event.preventDefault(); const response = await fetch(`${API_URL}/api/auth/login`, { method: "POST", credentials: "include", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ email, password }) }); if (response.ok) window.location.href=new URLSearchParams(window.location.search).get("next") || "/dashboard"; else { const result=await response.json(); setMessage(result.error?.message ?? "Login failed."); } }
  return <main className="auth-page"><div className="auth-card"><Link href="/" className="brand"><span className="brand-mark">L</span>LeadPitch</Link><p className="eyebrow">Welcome back</p><h1>Turn local demand into your next project.</h1><form onSubmit={submit}><label>Email<input type="email" required value={email} onChange={e=>setEmail(e.target.value)} /></label><label>Password<input type="password" required value={password} onChange={e=>setPassword(e.target.value)} /></label><button className="primary-action" type="submit">Sign in</button></form>{message && <p className="error-text">{message}</p>}<p className="muted">New to LeadPitch? <Link href="/register">Create an account</Link></p></div></main>;
}
