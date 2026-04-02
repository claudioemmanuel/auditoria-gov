import Link from "next/link";
import { DATA_SOURCES, TYPOLOGY_LABELS } from "@/lib/constants";
import { ArrowRight, Radar, BookOpen, Activity, Scale, Shield, Code, FileText, BarChart3 } from "lucide-react";
import { Button } from "@/components/Button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, MetricCard } from "@/components/Card";

export default function HomePage() {
  const typologyCount = Object.keys(TYPOLOGY_LABELS).length;
  const sourceCount = DATA_SOURCES.length;

  return (
    <div className="min-h-screen bg-[var(--color-surface-base)]">
      {/* ── Hero Section ──────────────────────────────────────────────── */}
      <section className="bg-gradient-to-br from-[var(--color-primary-dark)] via-[var(--color-primary-dark)] to-[#1A2847] text-white py-20 md:py-28">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <h1 className="text-5xl md:text-6xl font-bold font-[var(--font-display)] mb-6 leading-tight">
              Citizen Audit Platform for Federal Government Data
            </h1>
            <p className="text-lg text-blue-100 mb-8 leading-relaxed">
              Evidence-based corruption risk signals from public data. Deterministic, auditable, reproducible. 
              Open source, LGPD-compliant, built for citizen investigation.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/radar">
                <Button variant="primary" size="lg" className="flex items-center gap-2">
                  Explore Risk Signals
                  <ArrowRight className="h-5 w-5" />
                </Button>
              </Link>
              <Link href="/methodology">
                <Button variant="secondary" size="lg">
                  Learn Methodology
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Stats Strip ───────────────────────────────────────────────── */}
      <section className="bg-white border-b border-[var(--color-border-light)]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <MetricCard 
              label="Active Typologies"
              value={typologyCount}
              accentColor="var(--color-accent-alert)"
            />
            <MetricCard 
              label="Data Sources"
              value={sourceCount}
              accentColor="var(--color-accent-trust)"
            />
            <MetricCard 
              label="Detection Patterns"
              value={12}
              accentColor="var(--color-metric-signals)"
            />
            <MetricCard 
              label="Pipeline Stages"
              value={5}
              accentColor="var(--color-metric-typologies)"
            />
          </div>
        </div>
      </section>

      {/* ── Quick Actions ─────────────────────────────────────────────── */}
      <section className="py-16 md:py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold font-[var(--font-display)] mb-4 text-[var(--color-text-primary)]">
            Get Started
          </h2>
          <p className="text-lg text-[var(--color-text-secondary)] mb-12 max-w-2xl">
            Three main pathways to explore government data and investigate corruption risks
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                href: "/radar",
                icon: Radar,
                title: "Risk Radar",
                desc: "Signals and cases classified by typology, severity, and period. Starting point for citizen investigations.",
                delay: "0ms"
              },
              {
                href: "/coverage",
                icon: Activity,
                title: "Data Coverage",
                desc: "Operational status of sources and connectors. Monitor pipeline ingestion, normalization, and quality.",
                delay: "50ms"
              },
              {
                href: "/methodology",
                icon: BookOpen,
                title: "Methodology",
                desc: "Technical and legal foundations of typologies, risk factors, and evidence classification criteria.",
                delay: "100ms"
              },
            ].map((item) => (
              <Link key={item.href} href={item.href}>
                <Card
                  className="hover:shadow-lg cursor-pointer transition-all duration-300 h-full flex flex-col group animate-slideup"
                  style={{ animationDelay: item.delay }}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between mb-3">
                      <div className="p-2 bg-[var(--color-accent-dim)] rounded-[var(--radius-md)] group-hover:bg-[var(--color-accent-alert)] group-hover:text-white transition-all">
                        <item.icon className="h-6 w-6 text-[var(--color-accent-alert)] group-hover:text-white" />
                      </div>
                      <ArrowRight className="h-5 w-5 text-[var(--color-text-muted)] group-hover:text-[var(--color-accent-alert)] transition-colors" />
                    </div>
                    <CardTitle className="group-hover:text-[var(--color-accent-alert)] transition-colors">
                      {item.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1">
                    <CardDescription className="text-[var(--color-text-secondary)]">
                      {item.desc}
                    </CardDescription>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Institutional Pillars ─────────────────────────────────────── */}
      <section className="bg-[var(--color-surface-hover)] py-16 md:py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold font-[var(--font-display)] mb-4 text-[var(--color-text-primary)]">
            Built for Trust
          </h2>
          <p className="text-lg text-[var(--color-text-secondary)] mb-12 max-w-2xl">
            We commit to four pillars that make OpenWatch a reliable instrument for citizen audit
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                title: "Technologically Robust",
                desc: "Whitelist gov APIs, open source code, auditable data provenance",
                icon: Code,
              },
              {
                title: "Methodologically Sound",
                desc: "Typologies with legal basis, deterministic scoring, reproducible results",
                icon: FileText,
              },
              {
                title: "Legally Responsible",
                desc: "FOI + Constitution + LGPD + Anti-Corruption Law compliant",
                icon: Scale,
              },
              {
                title: "Publicly Auditable",
                desc: "Open source repository, public data sources, transparent APIs",
                icon: Shield,
              },
            ].map((item) => (
              <div key={item.title} className="bg-white p-6 rounded-[var(--radius-md)] border border-[var(--color-border-light)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow">
                <div className="flex items-start gap-3 mb-4">
                  <div className="p-2 bg-[var(--color-accent-dim)] rounded-[var(--radius-md)]">
                    <item.icon className="h-6 w-6 text-[var(--color-accent-alert)]" />
                  </div>
                </div>
                <h3 className="font-semibold text-[var(--color-text-primary)] mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Featured Signals / Recent Activity ──────────────────────── */}
      <section className="py-16 md:py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between mb-12">
            <div>
              <h2 className="text-3xl font-bold font-[var(--font-display)] mb-2 text-[var(--color-text-primary)]">
                Recent Signals
              </h2>
              <p className="text-[var(--color-text-secondary)]">
                Latest corruption risk flags across federal procurement
              </p>
            </div>
            <Link href="/radar">
              <Button variant="secondary" size="md" className="flex items-center gap-2">
                View All
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>

          <div className="space-y-4">
            {[
              {
                severity: "critical",
                title: "High-Value Sole Source Contracts",
                desc: "Pattern detected: Single-vendor contracts above R$500k without competitive bidding",
              },
              {
                severity: "high",
                title: "Repeated Bidder Networks",
                desc: "Companies with interconnected leadership appearing in same procurements",
              },
              {
                severity: "medium",
                title: "Geographic Price Anomalies",
                desc: "Regional pricing discrepancies suggest potential fraud or market manipulation",
              },
            ].map((signal, idx) => (
              <div
                key={idx}
                className="p-4 rounded-[var(--radius-md)] border-l-4 bg-white shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow cursor-pointer"
                style={{
                  borderLeftColor: {
                    critical: "var(--color-critical)",
                    high: "var(--color-high)",
                    medium: "var(--color-medium)",
                  }[signal.severity],
                }}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-semibold text-[var(--color-text-primary)] mb-1">
                      {signal.title}
                    </h4>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                      {signal.desc}
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ml-4 ${
                    {
                      critical: "bg-[#FEE2E2] text-[#991B1B]",
                      high: "bg-[#FEF3C7] text-[#92400E]",
                      medium: "bg-[#FEF9E7] text-[#78350F]",
                    }[signal.severity]
                  }`}>
                    {signal.severity.toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer / Compliance ───────────────────────────────────────── */}
      <footer className="bg-[var(--color-primary-dark)] text-white py-12 border-t border-[#1A2847]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
            <div>
              <h4 className="font-bold mb-4">Navigation</h4>
              <ul className="space-y-2 text-sm text-blue-100">
                <li><Link href="/radar" className="hover:text-white transition">Risk Radar</Link></li>
                <li><Link href="/coverage" className="hover:text-white transition">Data Coverage</Link></li>
                <li><Link href="/methodology" className="hover:text-white transition">Methodology</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Compliance</h4>
              <ul className="space-y-2 text-sm text-blue-100">
                <li><Link href="/methodology#legal" className="hover:text-white transition">Legal Basis</Link></li>
                <li><Link href="/methodology#lgpd" className="hover:text-white transition">LGPD Policy</Link></li>
                <li><Link href="/compliance" className="hover:text-white transition">Compliance</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Resources</h4>
              <ul className="space-y-2 text-sm text-blue-100">
                <li><a href="https://github.com" target="_blank" rel="noopener noreferrer" className="hover:text-white transition">GitHub</a></li>
                <li><a href="https://docs.openwatch.org" target="_blank" rel="noopener noreferrer" className="hover:text-white transition">Documentation</a></li>
                <li><a href="https://api.openwatch.org" target="_blank" rel="noopener noreferrer" className="hover:text-white transition">API</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">System Status</h4>
              <p className="text-sm text-blue-100 mb-2">API Status: <span className="text-green-400 font-semibold">Operational</span></p>
              <p className="text-xs text-blue-200">Last updated: Now</p>
            </div>
          </div>

          <div className="border-t border-[#1A2847] pt-8">
            <div className="bg-[#1A2847] p-4 rounded-[var(--radius-md)] mb-6">
              <p className="text-xs text-blue-100 leading-relaxed">
                <strong className="text-white">Legal Notice:</strong> This platform is a screening tool for social control and citizen audit. 
                Results represent investigable hypotheses based on public data and{" "}
                <strong>do not constitute accusations, definitive proof, or judgment of guilt.</strong>{" "}
                Data processing per LGPD (Law 13.709/2018), art. 7, VII. Personal data anonymized per art. 12.
              </p>
            </div>

            <div className="flex items-center justify-between text-xs text-blue-200">
              <p>&copy; 2026 OpenWatch. Open source under MIT License.</p>
              <p>FOI • Constitution • LGPD • Anti-Corruption Law</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
