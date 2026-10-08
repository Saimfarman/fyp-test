import Link from "next/link";

export default function Home() {
  return (
    <main className="shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">LeadPitch foundation</p>
        <h1 id="page-title">Find the next local business you can help.</h1>
        <p className="lede">
          Discover local businesses, diagnose their websites, pitch practical
          improvements, and turn opportunities into editable prototypes.
        </p>
        <div className="hero-actions"><Link className="primary-action" href="/dashboard">Open workspace</Link><Link className="secondary-action" href="/discover">Start discovering</Link></div>
        <div className="status-card" role="status"><strong>One workspace for your next client.</strong><span>Discover, diagnose, pitch, prototype, and close—all in one place.</span></div>
        <div className="feature-grid"><Link href="/discover"><b>01 / Discover</b><span>Find businesses that need your help.</span></Link><Link href="/pipeline"><b>02 / Convert</b><span>Track every opportunity through your funnel.</span></Link><Link href="/prototypes"><b>03 / Show</b><span>Build a prototype worth saying yes to.</span></Link></div>
      </section>
    </main>
  );
}
