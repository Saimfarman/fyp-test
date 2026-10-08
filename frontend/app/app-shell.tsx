"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const nav = [
  ["Dashboard", "/dashboard"],
  ["Discover", "/discover"],
  ["Pipeline", "/pipeline"],
  ["Pitches", "/pitches"],
  ["Prototypes", "/prototypes"],
];
const manage = [
  ["Team", "/team"],
  ["Services", "/services"],
  ["Reports", "/reports"],
  ["Settings", "/settings"],
  ["Developer", "/developer"],
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [user, setUser] = useState<{ email?: string } | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  useEffect(() => {
    fetch(`${API_URL}/api/auth/me`, { credentials: "include" })
      .then((response) => response.ok ? response.json() : null)
      .then((result) => setUser(result?.user ?? null))
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true));
  }, [pathname]);

  if (pathname === "/" || pathname === "/login" || pathname === "/register" || pathname.startsWith("/share/") || pathname === "/offline") return <>{children}</>;
  if (authChecked && !user && typeof window !== "undefined") {
    router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    return null;
  }
  return (
    <div className="app-shell">
      <aside className={`app-sidebar ${open ? "open" : ""}`}>
        <Link href="/" className="brand" onClick={() => setOpen(false)}><span className="brand-mark">L</span><span>LeadPitch</span></Link>
        <p className="nav-label">Workspace</p>
        <nav aria-label="Workspace navigation">{nav.map(([label, href]) => <Link className={pathname === href || pathname.startsWith(`${href}/`) ? "active" : ""} href={href} key={href} onClick={() => setOpen(false)}>{label}</Link>)}</nav>
        <p className="nav-label">Manage</p>
        <nav aria-label="Management navigation">{manage.map(([label, href]) => <Link className={pathname === href || pathname.startsWith(`${href}/`) ? "active" : ""} href={href} key={href} onClick={() => setOpen(false)}>{label}</Link>)}</nav>
        <div className="sidebar-footer"><span className="avatar">{user?.email?.[0]?.toUpperCase() ?? "G"}</span><span>{user?.email ?? "Guest workspace"}</span>{user && <button className="text-button" onClick={async () => { await fetch(`${API_URL}/api/auth/logout`, { method: "POST", credentials: "include" }); router.push("/"); }}>Log out</button>}</div>
      </aside>
      <div className="app-main">
        <header className="topbar"><button className="menu-button" onClick={() => setOpen(!open)} aria-label="Toggle navigation">☰</button><div className="breadcrumbs">LeadPitch <span>/</span> {pathname === "/" ? "Home" : pathname.split("/")[1]}</div><div className="topbar-actions"><Link href="/discover" className="topbar-cta">+ Find leads</Link><Link href="/settings" aria-label="Settings">⚙</Link></div></header>
        <div className="app-content">{children}</div>
      </div>
    </div>
  );
}
