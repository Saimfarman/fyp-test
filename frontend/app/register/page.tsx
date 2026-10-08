"use client";
import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export default function RegisterPage() {
  const [email,setEmail]=useState(""); const [password,setPassword]=useState(""); const [workspaceName,setWorkspaceName]=useState(""); const [message,setMessage]=useState("");
  const router = useRouter();
  async function submit(event: FormEvent) { event.preventDefault(); const response=await fetch(`${API_URL}/api/auth/register`,{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password,workspaceName})}); if(response.ok) router.push("/dashboard"); else {const result=await response.json();setMessage(result.error?.message??"Registration failed.");} }
  return <main className="auth-page"><div className="auth-card"><Link href="/" className="brand"><span className="brand-mark">L</span>LeadPitch</Link><p className="eyebrow">Start free</p><h1>Build a healthier pipeline.</h1><form onSubmit={submit}><label>Workspace name<input required value={workspaceName} onChange={e=>setWorkspaceName(e.target.value)} placeholder="My agency" /></label><label>Email<input type="email" required value={email} onChange={e=>setEmail(e.target.value)} /></label><label>Password<input type="password" minLength={10} required value={password} onChange={e=>setPassword(e.target.value)} /></label><button className="primary-action" type="submit">Create workspace</button></form>{message&&<p className="error-text">{message}</p>}<p className="muted">Already have an account? <Link href="/login">Sign in</Link></p></div></main>;
}
