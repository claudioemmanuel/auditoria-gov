"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { getDossierTimeline, getDossierSummary } from "@/lib/api";
import { formatBRL, formatDate } from "@/lib/utils";
import type {
  DossierTimelineResponse,
  DossierSummaryResponse,
} from "@/lib/types";

// ── Constants ────────────────────────────────────────────────────────────────

const SEV_COLOR: Record<string, string> = {
  critical: "var(--color-critical)",
  high: "var(--color-high)",
  medium: "var(--color-medium)",
  low: "var(--color-low)",
};
const SEV_LABEL: Record<string, string> = {
  critical: "CRÍTICO",
  high: "ALTO",
  medium: "MÉDIO",
  low: "BAIXO",
};

type DossierTab = "dossie" | "sinais" | "cronologia" | "entidades" | "hipoteses";

const EVENT_TYPE_LABEL: Record<string, string> = {
  licitacao: "Licitação",
  contrato: "Contrato",
  aditivo: "Aditivo",
  empenho: "Empenho",
  pagamento: "Pagamento",
  dispensa: "Dispensa",
  inexigibilidade: "Inexigibilidade",
  pregao: "Pregão",
  credenciamento: "Credenciamento",
};

// ── Shared components ────────────────────────────────────────────────────────

function SectionHeader({ n, title }: { n: number; title: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          color: "var(--color-text-3)",
          letterSpacing: "0.1em",
        }}
      >
        § {n}.
      </span>
      <h2
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: "var(--color-text-2)",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          margin: 0,
        }}
      >
        {title}
      </h2>
    </div>
  );
}

function Card({
  children,
  style,
}: {
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        padding: "16px",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function LoadingScreen() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <div
          style={{
            width: 32,
            height: 32,
            border: "2px solid var(--color-border)",
            borderTopColor: "var(--color-amber)",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
            margin: "0 auto 12px",
          }}
        />
        <p
          style={{
            fontSize: 13,
            color: "var(--color-text-3)",
            fontFamily: "var(--font-mono)",
          }}
        >
          Carregando dossiê…
        </p>
      </div>
    </div>
  );
}

function ErrorScreen({ error }: { error: string | null }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          padding: "32px 40px",
          textAlign: "center",
          maxWidth: 400,
        }}
      >
        <div style={{ fontSize: 32, marginBottom: 12, color: "var(--color-critical)" }}>
          ⚠
        </div>
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 18,
            fontWeight: 700,
            color: "var(--color-text)",
            marginBottom: 8,
          }}
        >
          {error ?? "Erro desconhecido"}
        </h2>
        <p style={{ fontSize: 13, color: "var(--color-text-3)" }}>
          O caso solicitado não pôde ser carregado.
        </p>
      </div>
    </div>
  );
}

// ── DossieTab ────────────────────────────────────────────────────────────────

function DossieTab({
  timeline,
  summary,
}: {
  timeline: DossierTimelineResponse;
  summary: DossierSummaryResponse | null;
}) {
  const cas = timeline.case;
  let sectionN = 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {cas.summary && (
        <div>
          <SectionHeader n={sectionN++} title="Resumo do Caso" />
          <Card>
            <p style={{ fontSize: 14, color: "var(--color-text)", lineHeight: 1.7 }}>
              {cas.summary}
            </p>
            {cas.case_type && (
              <div style={{ marginTop: 10 }}>
                <span
                  style={{
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-3)",
                    background: "var(--color-surface-2)",
                    border: "1px solid var(--color-border)",
                    padding: "2px 6px",
                    borderRadius: 3,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  {cas.case_type}
                </span>
              </div>
            )}
          </Card>
        </div>
      )}

      {summary && summary.chapters.length > 0 && (
        <div>
          <SectionHeader n={sectionN++} title="Capítulos da Investigação" />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
              gap: 12,
            }}
          >
            {summary.chapters.map((ch, i) => {
              const chSevColor = SEV_COLOR[ch.max_severity] ?? "var(--color-text-3)";
              return (
                <div
                  key={i}
                  style={{
                    background: "var(--color-surface)",
                    border: `1px solid var(--color-border)`,
                    borderLeftWidth: 3,
                    borderLeftColor: chSevColor,
                    borderRadius: "0 var(--radius-md) var(--radius-md) 0",
                    padding: "14px 16px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 8,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--font-mono)",
                        fontWeight: 700,
                        color: chSevColor,
                        background: `${chSevColor}18`,
                        border: `1px solid ${chSevColor}40`,
                        padding: "1px 6px",
                        borderRadius: 3,
                      }}
                    >
                      {SEV_LABEL[ch.max_severity]}
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                      }}
                    >
                      {ch.typology_code}
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                        marginLeft: "auto",
                      }}
                    >
                      {ch.signal_count} sinal{ch.signal_count !== 1 ? "is" : ""}
                    </span>
                  </div>
                  <p
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--color-text)",
                      marginBottom: 6,
                    }}
                  >
                    {ch.typology_name}
                  </p>
                  <p
                    style={{
                      fontSize: 12,
                      color: "var(--color-text-2)",
                      lineHeight: 1.5,
                      marginBottom: 10,
                      display: "-webkit-box",
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: "vertical" as const,
                      overflow: "hidden",
                    }}
                  >
                    {ch.top_signal_summary}
                  </p>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      flexWrap: "wrap",
                    }}
                  >
                    {ch.total_value_brl > 0 && (
                      <span
                        style={{
                          fontSize: 12,
                          fontFamily: "var(--font-mono)",
                          fontWeight: 600,
                          color: chSevColor,
                        }}
                      >
                        {formatBRL(ch.total_value_brl)}
                      </span>
                    )}
                    {(ch.period_start || ch.period_end) && (
                      <span style={{ fontSize: 11, color: "var(--color-text-3)" }}>
                        {ch.period_start ? formatDate(ch.period_start) : "—"} →{" "}
                        {ch.period_end ? formatDate(ch.period_end) : "presente"}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {timeline.related_cases.length > 0 && (
        <div>
          <SectionHeader n={sectionN++} title="Casos Relacionados" />
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {timeline.related_cases.map((rc) => {
              const rcSevColor = SEV_COLOR[rc.severity] ?? "var(--color-text-3)";
              return (
                <Link
                  key={rc.id}
                  href={`/radar/dossie/${rc.id}`}
                  style={{ textDecoration: "none" }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "10px 14px",
                      background: "var(--color-surface)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      cursor: "pointer",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--font-mono)",
                        fontWeight: 700,
                        color: rcSevColor,
                        background: `${rcSevColor}18`,
                        border: `1px solid ${rcSevColor}40`,
                        padding: "1px 6px",
                        borderRadius: 3,
                        flexShrink: 0,
                      }}
                    >
                      {SEV_LABEL[rc.severity]}
                    </span>
                    <span style={{ fontSize: 13, color: "var(--color-text)", flex: 1 }}>
                      {rc.title}
                    </span>
                    <span style={{ fontSize: 12, color: "var(--color-amber)" }}>→</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ── SinaisTab ────────────────────────────────────────────────────────────────

function SinaisTab({ signals }: { signals: DossierTimelineResponse["signals"] }) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  function toggleExpand(id: string) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  if (signals.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "48px",
          color: "var(--color-text-3)",
          fontSize: 13,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
        }}
      >
        Nenhum sinal encontrado.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {signals.map((sig) => {
        const sigSevColor = SEV_COLOR[sig.severity] ?? "var(--color-text-3)";
        const isExpanded = expandedIds.has(sig.id);
        const factors = sig.factors ? Object.entries(sig.factors) : [];
        const factorDescs = sig.factor_descriptions ?? {};

        return (
          <div
            key={sig.id}
            style={{
              background: "var(--color-surface)",
              border: `1px solid var(--color-border)`,
              borderLeftWidth: 3,
              borderLeftColor: sigSevColor,
              borderRadius: "0 var(--radius-md) var(--radius-md) 0",
              overflow: "hidden",
            }}
          >
            <Link href={`/signal/${sig.id}`} style={{ textDecoration: "none" }}>
              <div style={{ padding: "14px 16px" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      fontWeight: 700,
                      color: sigSevColor,
                      background: `${sigSevColor}18`,
                      border: `1px solid ${sigSevColor}40`,
                      padding: "1px 6px",
                      borderRadius: 3,
                    }}
                  >
                    {SEV_LABEL[sig.severity]}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-text-3)",
                    }}
                  >
                    {sig.typology_code}
                  </span>
                  <span
                    style={{
                      fontSize: 12,
                      fontFamily: "var(--font-mono)",
                      fontWeight: 600,
                      color: sigSevColor,
                      marginLeft: "auto",
                    }}
                  >
                    {Math.round(sig.confidence * 100)}%
                  </span>
                </div>
                <p
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "var(--color-text)",
                    marginBottom: 6,
                    lineHeight: 1.4,
                  }}
                >
                  {sig.title}
                </p>
                {sig.summary && (
                  <p
                    style={{
                      fontSize: 12,
                      color: "var(--color-text-2)",
                      lineHeight: 1.5,
                      marginBottom: 8,
                    }}
                  >
                    {sig.summary}
                  </p>
                )}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontSize: 11, color: "var(--color-text-3)" }}>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                        color: "var(--color-text-2)",
                      }}
                    >
                      {sig.entity_count}
                    </span>{" "}
                    entidades
                  </span>
                  <span style={{ fontSize: 11, color: "var(--color-text-3)" }}>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                        color: "var(--color-text-2)",
                      }}
                    >
                      {sig.event_count}
                    </span>{" "}
                    eventos
                  </span>
                  {(sig.period_start || sig.period_end) && (
                    <span style={{ fontSize: 11, color: "var(--color-text-3)" }}>
                      {sig.period_start ? formatDate(sig.period_start) : "—"} →{" "}
                      {sig.period_end ? formatDate(sig.period_end) : "presente"}
                    </span>
                  )}
                </div>
              </div>
            </Link>

            {factors.length > 0 && (
              <div style={{ borderTop: "1px solid var(--color-border)" }}>
                <button
                  onClick={() => toggleExpand(sig.id)}
                  style={{
                    width: "100%",
                    padding: "8px 16px",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    fontSize: 11,
                    color: "var(--color-text-3)",
                    fontFamily: "var(--font-mono)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  <span
                    style={{
                      display: "inline-block",
                      transition: "transform 0.2s",
                      transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                    }}
                  >
                    ▾
                  </span>
                  {isExpanded ? "Ocultar fatores" : `${factors.length} fatores`}
                </button>

                {isExpanded && (
                  <div
                    style={{
                      padding: "12px 16px",
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                      gap: 8,
                      background: "var(--color-surface-2)",
                    }}
                  >
                    {factors.map(([key, value]) => {
                      const meta = factorDescs[key];
                      return (
                        <div key={key}>
                          <p
                            style={{
                              fontSize: 10,
                              fontFamily: "var(--font-mono)",
                              color: "var(--color-text-3)",
                              textTransform: "uppercase",
                              letterSpacing: "0.08em",
                              marginBottom: 2,
                            }}
                          >
                            {meta?.label ?? key}
                          </p>
                          <p
                            style={{
                              fontSize: 13,
                              fontWeight: 600,
                              fontFamily: "var(--font-mono)",
                              color: "var(--color-text)",
                            }}
                          >
                            {typeof value === "number"
                              ? value.toLocaleString("pt-BR")
                              : String(value)}
                            {meta?.unit ? ` ${meta.unit}` : ""}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── CronologiaTab ────────────────────────────────────────────────────────────

function CronologiaTab({
  events,
  entities,
}: {
  events: DossierTimelineResponse["events"];
  entities: DossierTimelineResponse["entities"];
}) {
  const entityMap: Record<string, string> = {};
  for (const e of entities) {
    entityMap[e.id] = e.name;
  }

  const sorted = [...events].sort(
    (a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime()
  );

  if (sorted.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "48px",
          color: "var(--color-text-3)",
          fontSize: 13,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
        }}
      >
        Nenhum evento encontrado.
      </div>
    );
  }

  const byDate: Map<string, typeof sorted> = new Map();
  for (const ev of sorted) {
    const dateKey = ev.occurred_at.slice(0, 10);
    const group = byDate.get(dateKey);
    if (group) {
      group.push(ev);
    } else {
      byDate.set(dateKey, [ev]);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {Array.from(byDate.entries()).map(([date, dayEvents]) => (
        <div key={date}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 10,
            }}
          >
            <div
              style={{
                height: 1,
                width: 20,
                background: "var(--color-border)",
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-3)",
                letterSpacing: "0.08em",
                whiteSpace: "nowrap",
              }}
            >
              {formatDate(date)}
            </span>
            <div style={{ height: 1, flex: 1, background: "var(--color-border)" }} />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {dayEvents.map((ev) => (
              <Card key={ev.id}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-text-3)",
                      background: "var(--color-surface-2)",
                      border: "1px solid var(--color-border)",
                      padding: "2px 6px",
                      borderRadius: 3,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    {EVENT_TYPE_LABEL[ev.type] ?? ev.type}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-text-3)",
                    }}
                  >
                    {ev.source_connector}
                  </span>
                  {ev.value_brl != null && (
                    <span
                      style={{
                        fontSize: 13,
                        fontFamily: "var(--font-mono)",
                        fontWeight: 700,
                        color: "var(--color-amber)",
                        marginLeft: "auto",
                      }}
                    >
                      {formatBRL(ev.value_brl)}
                    </span>
                  )}
                </div>

                <p
                  style={{
                    fontSize: 13,
                    color: "var(--color-text)",
                    lineHeight: 1.5,
                    marginBottom:
                      ev.participants.length > 0 || ev.signals.length > 0 ? 10 : 0,
                  }}
                >
                  {ev.description}
                </p>

                {ev.participants.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 4,
                      marginBottom: ev.signals.length > 0 ? 8 : 0,
                    }}
                  >
                    {ev.participants.map((p) => (
                      <Link
                        key={p.entity_id}
                        href={`/entity/${p.entity_id}`}
                        style={{ textDecoration: "none" }}
                      >
                        <span
                          style={{
                            fontSize: 11,
                            color: "var(--color-text-2)",
                            background: "var(--color-surface-2)",
                            border: "1px solid var(--color-border)",
                            padding: "2px 8px",
                            borderRadius: 10,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            cursor: "pointer",
                          }}
                        >
                          <span
                            style={{ color: "var(--color-text-3)", fontSize: 10 }}
                          >
                            {p.role_label}
                          </span>
                          {entityMap[p.entity_id] ?? p.entity_id.slice(0, 8)}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}

                {ev.signals.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {ev.signals.map((s) => {
                      const sSevColor = SEV_COLOR[s.severity] ?? "var(--color-text-3)";
                      return (
                        <Link
                          key={s.id}
                          href={`/signal/${s.id}`}
                          style={{ textDecoration: "none" }}
                        >
                          <span
                            style={{
                              fontSize: 10,
                              fontFamily: "var(--font-mono)",
                              color: sSevColor,
                              background: `${sSevColor}12`,
                              border: `1px solid ${sSevColor}40`,
                              padding: "2px 6px",
                              borderRadius: 3,
                              cursor: "pointer",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 3,
                            }}
                          >
                            ⚑ {s.typology_code}
                          </span>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── EntidadesTab ─────────────────────────────────────────────────────────────

function formatCNPJ(cnpj: string): string {
  const digits = cnpj.replace(/\D/g, "");
  if (digits.length === 14) {
    return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
  }
  return cnpj;
}

function EntidadesTab({
  entities,
}: {
  entities: DossierTimelineResponse["entities"];
}) {
  const TYPE_ICON: Record<string, string> = {
    person: "👤",
    company: "🏢",
    org: "🏛",
  };

  if (entities.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "48px",
          color: "var(--color-text-3)",
          fontSize: 13,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
        }}
      >
        Nenhuma entidade encontrada.
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
        gap: 12,
      }}
    >
      {entities.map((ent) => {
        const cnpj = ent.identifiers["cnpj"];
        const otherIds = Object.entries(ent.identifiers).filter(
          ([k]) => !["name_key", "cpf", "cpf_hash", "cnpj"].includes(k)
        );

        return (
          <Link
            key={ent.id}
            href={`/entity/${ent.id}`}
            style={{ textDecoration: "none" }}
          >
            <Card style={{ cursor: "pointer" }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <span style={{ fontSize: 22, flexShrink: 0 }}>
                  {TYPE_ICON[ent.type] ?? "📄"}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p
                    style={{
                      fontSize: 13,
                      fontWeight: 600,
                      color: "var(--color-text)",
                      marginBottom: 2,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {ent.name}
                  </p>
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-text-3)",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    {ent.type}
                  </span>
                </div>
              </div>

              {cnpj && (
                <p
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-3)",
                    marginBottom: 4,
                  }}
                >
                  CNPJ: {formatCNPJ(cnpj)}
                </p>
              )}

              {otherIds.slice(0, 2).map(([k, v]) => (
                <p
                  key={k}
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-3)",
                    marginBottom: 2,
                  }}
                >
                  {k.toUpperCase()}: {v}
                </p>
              ))}

              <div
                style={{
                  marginTop: 10,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "flex-end",
                }}
              >
                <span style={{ fontSize: 11, color: "var(--color-amber)" }}>
                  Ver entidade →
                </span>
              </div>
            </Card>
          </Link>
        );
      })}
    </div>
  );
}

// ── HipotesesTab ─────────────────────────────────────────────────────────────

function HipotesesTab({
  hypotheses,
}: {
  hypotheses: DossierTimelineResponse["legal_hypotheses"];
}) {
  if (hypotheses.length === 0) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "48px",
          color: "var(--color-text-3)",
          fontSize: 13,
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
        }}
      >
        Nenhuma hipótese legal identificada.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {hypotheses.map((hyp, i) => (
        <Card key={i}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
            <span
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                fontWeight: 700,
                color: "var(--color-text-3)",
                background: "var(--color-surface-2)",
                border: "1px solid var(--color-border)",
                borderRadius: "50%",
                width: 28,
                height: 28,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {i + 1}
            </span>

            <div style={{ flex: 1 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  marginBottom: 8,
                  flexWrap: "wrap",
                }}
              >
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "var(--color-text)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {hyp.law}
                </span>
                <span
                  style={{
                    fontSize: 12,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-3)",
                  }}
                >
                  {hyp.article}
                </span>
              </div>

              <div style={{ marginBottom: hyp.description ? 8 : 0 }}>
                <span
                  style={{
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                    color: "var(--color-high)",
                    background: "rgba(255,100,0,0.08)",
                    border: "1px solid rgba(255,100,0,0.2)",
                    padding: "2px 8px",
                    borderRadius: 3,
                    letterSpacing: "0.06em",
                    textTransform: "uppercase",
                  }}
                >
                  {hyp.violation_type}
                </span>
              </div>

              {hyp.description && (
                <p
                  style={{
                    fontSize: 13,
                    color: "var(--color-text-2)",
                    lineHeight: 1.6,
                    marginBottom: 8,
                    marginTop: 8,
                  }}
                >
                  {hyp.description}
                </p>
              )}

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  marginTop: 8,
                }}
              >
                {hyp.confidence != null && (
                  <span style={{ fontSize: 12, color: "var(--color-text-3)" }}>
                    Confiança:{" "}
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                        color: "var(--color-text-2)",
                      }}
                    >
                      {Math.round(hyp.confidence * 100)}%
                    </span>
                  </span>
                )}
                {hyp.signal_cluster && hyp.signal_cluster.length > 0 && (
                  <span style={{ fontSize: 12, color: "var(--color-text-3)" }}>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                        color: "var(--color-text-2)",
                      }}
                    >
                      {hyp.signal_cluster.length}
                    </span>{" "}
                    sinal{hyp.signal_cluster.length !== 1 ? "is" : ""} vinculado
                    {hyp.signal_cluster.length !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function RadarDossierPage() {
  const params = useParams();
  const caseId = params["caseId"] as string;
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") as DossierTab) ?? "dossie";

  const [timeline, setTimeline] = useState<DossierTimelineResponse | null>(null);
  const [summary, setSummary] = useState<DossierSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    setLoading(true);
    Promise.all([getDossierTimeline(caseId), getDossierSummary(caseId)])
      .then(([t, s]) => {
        setTimeline(t);
        setSummary(s);
      })
      .catch(() => setError("Caso não encontrado"))
      .finally(() => setLoading(false));
  }, [caseId]);

  function setTab(t: DossierTab) {
    const p = new URLSearchParams(searchParams.toString());
    p.set("tab", t);
    router.replace(`?${p.toString()}`, { scroll: false });
  }

  if (loading) return <LoadingScreen />;
  if (error || !timeline) return <ErrorScreen error={error} />;

  const cas = timeline.case;
  const sevColor = SEV_COLOR[cas.severity] ?? "var(--color-text-3)";

  const tabDefs: { key: DossierTab; label: string; count?: number }[] = [
    { key: "dossie", label: "Dossiê" },
    { key: "sinais", label: "Sinais", count: timeline.signals.length },
    { key: "cronologia", label: "Cronologia", count: timeline.events.length },
    { key: "entidades", label: "Entidades", count: timeline.entities.length },
    {
      key: "hipoteses",
      label: "Hipóteses Legais",
      count: timeline.legal_hypotheses.length,
    },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "var(--color-bg)" }}>
      {/* Sticky header */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          background: "var(--color-bg)",
        }}
      >
        <div style={{ padding: "0 16px", maxWidth: 1056, margin: "0 auto" }}>
          <div
            style={{
              borderLeft: `4px solid ${sevColor}`,
              background: "var(--color-surface)",
              borderRadius: "0 var(--radius-lg) var(--radius-lg) 0",
              padding: "16px 20px",
              marginTop: 16,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 8,
                flexWrap: "wrap",
              }}
            >
              <span
                style={{
                  background: `${sevColor}18`,
                  color: sevColor,
                  border: `1px solid ${sevColor}40`,
                  borderRadius: 4,
                  padding: "1px 8px",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  fontWeight: 700,
                  letterSpacing: "0.12em",
                }}
              >
                {SEV_LABEL[cas.severity]}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--color-text-3)",
                }}
              >
                CASO DE INVESTIGAÇÃO
              </span>
              <div style={{ marginLeft: "auto" }}>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 9,
                    letterSpacing: "0.15em",
                    color: "var(--color-text-3)",
                    border: "1px solid var(--color-border)",
                    padding: "2px 6px",
                    borderRadius: 2,
                    textTransform: "uppercase" as const,
                    opacity: 0.7,
                  }}
                >
                  Dossiê de Investigação
                </span>
              </div>
            </div>

            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 20,
                fontWeight: 700,
                color: "var(--color-text)",
                lineHeight: 1.3,
                margin: "0 0 8px",
              }}
            >
              {cas.title}
            </h1>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              <span style={{ fontSize: 12, color: "var(--color-text-3)" }}>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                    color: "var(--color-text-2)",
                  }}
                >
                  {timeline.signals.length}
                </span>{" "}
                sinais
              </span>
              <span style={{ fontSize: 12, color: "var(--color-text-3)" }}>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                    color: "var(--color-text-2)",
                  }}
                >
                  {timeline.entities.length}
                </span>{" "}
                entidades
              </span>
              {summary?.case.total_value_brl != null && (
                <span style={{ fontSize: 12, color: "var(--color-text-3)" }}>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontWeight: 600,
                      color: sevColor,
                    }}
                  >
                    {formatBRL(summary.case.total_value_brl)}
                  </span>{" "}
                  total
                </span>
              )}
              <span
                style={{
                  fontSize: 11,
                  color: "var(--color-text-3)",
                  border: "1px solid var(--color-border)",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontFamily: "var(--font-mono)",
                  marginLeft: "auto",
                }}
              >
                {cas.status.toUpperCase()}
              </span>
            </div>
          </div>
        </div>

        {/* Tab strip */}
        <div style={{ padding: "0 16px", maxWidth: 1056, margin: "0 auto" }}>
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid var(--color-border)",
              marginTop: 8,
              overflowX: "auto",
            }}
          >
            {tabDefs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                style={{
                  padding: "10px 16px",
                  fontSize: 13,
                  fontWeight: 500,
                  background: "none",
                  border: "none",
                  borderBottom:
                    tab === t.key
                      ? "2px solid var(--color-amber)"
                      : "2px solid transparent",
                  color:
                    tab === t.key ? "var(--color-amber)" : "var(--color-text-3)",
                  marginBottom: -1,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  whiteSpace: "nowrap" as const,
                  transition: "color 0.15s",
                }}
              >
                {t.label}
                {t.count != null && t.count > 0 && (
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      background:
                        tab === t.key
                          ? "var(--color-amber-dim)"
                          : "var(--color-surface-2)",
                      color:
                        tab === t.key ? "var(--color-amber)" : "var(--color-text-3)",
                      padding: "1px 5px",
                      borderRadius: 10,
                    }}
                  >
                    {t.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div style={{ maxWidth: 1056, margin: "0 auto", padding: "24px 16px" }}>
        {tab === "dossie" && (
          <DossieTab timeline={timeline} summary={summary} />
        )}
        {tab === "sinais" && <SinaisTab signals={timeline.signals} />}
        {tab === "cronologia" && (
          <CronologiaTab events={timeline.events} entities={timeline.entities} />
        )}
        {tab === "entidades" && <EntidadesTab entities={timeline.entities} />}
        {tab === "hipoteses" && (
          <HipotesesTab hypotheses={timeline.legal_hypotheses} />
        )}
      </div>
    </div>
  );
}
