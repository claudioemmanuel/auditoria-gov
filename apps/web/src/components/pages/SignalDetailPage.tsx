"use client";

import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  getSignal,
  getSignalEvidence,
  getSignalGraph,
  fetchTypologyLegalBasis,
  fetchRelatedSignals,
} from "@/lib/api";
import type { GNode, GLink } from "@/hooks/useCaseGraph";
import { formatBRL, formatDate, relativeTime } from "@/lib/utils";
import type {
  SignalDetail,
  SignalEvidencePage,
  SignalGraphResponse,
  TypologyLegalBasis,
  RelatedSignal,
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

type SignalTab = "dossie" | "evidencias" | "entidades" | "analise";

// ── Shared small components ──────────────────────────────────────────────────

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
        <div
          style={{
            fontSize: 32,
            marginBottom: 12,
            color: "var(--color-critical)",
          }}
        >
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
          O sinal solicitado não pôde ser carregado.
        </p>
      </div>
    </div>
  );
}

// ── DossieTab ────────────────────────────────────────────────────────────────

function DossieTab({ signal }: { signal: SignalDetail }) {
  const sevColor = SEV_COLOR[signal.severity] ?? "var(--color-text-3)";

  const paragraphs = signal.explanation_md
    ? signal.explanation_md.split(/\n\n+/)
    : signal.summary
    ? [signal.summary]
    : [];

  const inv = signal.investigation_summary;
  const factors = signal.factors ? Object.entries(signal.factors) : [];
  const factorDescs = signal.factor_descriptions ?? {};

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "2fr 1fr",
        gap: 24,
        alignItems: "start",
      }}
    >
      {/* Left column */}
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* Narrative */}
        {paragraphs.length > 0 && (
          <div>
            <SectionHeader n={1} title="Narrativa do Sinal" />
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {paragraphs.map((p, i) => (
                <p
                  key={i}
                  style={{
                    fontSize: 14,
                    color: "var(--color-text)",
                    lineHeight: 1.7,
                    margin: 0,
                  }}
                >
                  {p.trim()}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Investigation Summary */}
        {inv && (
          <div>
            <SectionHeader n={2} title="Resumo da Investigação" />
            <Card>
              {inv.what_crossed.length > 0 && (
                <div style={{ marginBottom: 12 }}>
                  <p
                    style={{
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-text-3)",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      marginBottom: 6,
                    }}
                  >
                    Limiares cruzados
                  </p>
                  <ul style={{ margin: 0, paddingLeft: 16 }}>
                    {inv.what_crossed.map((item, i) => (
                      <li
                        key={i}
                        style={{
                          fontSize: 13,
                          color: "var(--color-text)",
                          marginBottom: 4,
                          lineHeight: 1.5,
                        }}
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  marginTop: 12,
                }}
              >
                {inv.observed_total_brl != null && (
                  <div>
                    <p
                      style={{
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 4,
                      }}
                    >
                      Total observado
                    </p>
                    <p
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        color: sevColor,
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {formatBRL(inv.observed_total_brl)}
                    </p>
                  </div>
                )}
                {inv.legal_threshold_brl != null && (
                  <div>
                    <p
                      style={{
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 4,
                      }}
                    >
                      Limite legal
                    </p>
                    <p
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        color: "var(--color-text)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {formatBRL(inv.legal_threshold_brl)}
                    </p>
                  </div>
                )}
                {inv.ratio_over_threshold != null && (
                  <div>
                    <p
                      style={{
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 4,
                      }}
                    >
                      Razão sobre limite
                    </p>
                    <p
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        color: sevColor,
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {inv.ratio_over_threshold.toFixed(2)}×
                    </p>
                  </div>
                )}
                {inv.legal_reference && (
                  <div>
                    <p
                      style={{
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 4,
                      }}
                    >
                      Referência legal
                    </p>
                    <p style={{ fontSize: 12, color: "var(--color-text-2)" }}>
                      {inv.legal_reference}
                    </p>
                  </div>
                )}
              </div>
            </Card>
          </div>
        )}

        {/* Factors */}
        {factors.length > 0 && (
          <div>
            <SectionHeader n={3} title="Fatores de Risco" />
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                gap: 10,
              }}
            >
              {factors.map(([key, value]) => {
                const meta = factorDescs[key];
                return (
                  <Card key={key}>
                    <p
                      style={{
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 4,
                      }}
                    >
                      {meta?.label ?? key}
                    </p>
                    <p
                      style={{
                        fontSize: 15,
                        fontWeight: 700,
                        color: "var(--color-text)",
                        fontFamily: "var(--font-mono)",
                        marginBottom: meta?.description ? 4 : 0,
                      }}
                    >
                      {typeof value === "number"
                        ? value.toLocaleString("pt-BR")
                        : String(value)}
                      {meta?.unit ? ` ${meta.unit}` : ""}
                    </p>
                    {meta?.description && (
                      <p style={{ fontSize: 11, color: "var(--color-text-3)" }}>
                        {meta.description}
                      </p>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Right sidebar */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Confidence bar */}
        <Card>
          <p
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: "var(--color-text-3)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: 10,
            }}
          >
            Confiança
          </p>
          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: 12,
            }}
          >
            <div
              style={{
                width: 20,
                height: 100,
                background: "var(--color-surface-2)",
                borderRadius: 4,
                overflow: "hidden",
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  width: "100%",
                  height: `${Math.round(signal.confidence * 100)}%`,
                  background: sevColor,
                  borderRadius: 4,
                  marginTop: `${100 - Math.round(signal.confidence * 100)}%`,
                  transition: "height 0.4s ease",
                }}
              />
            </div>
            <div>
              <p
                style={{
                  fontSize: 28,
                  fontWeight: 700,
                  fontFamily: "var(--font-mono)",
                  color: sevColor,
                  lineHeight: 1,
                  marginBottom: 4,
                }}
              >
                {Math.round(signal.confidence * 100)}%
              </p>
              <p style={{ fontSize: 11, color: "var(--color-text-3)" }}>
                {signal.confidence >= 0.8
                  ? "Alta confiança"
                  : signal.confidence >= 0.5
                  ? "Confiança moderada"
                  : "Confiança baixa"}
              </p>
            </div>
          </div>
        </Card>

        {/* Completeness */}
        {signal.completeness_score != null && (
          <Card>
            <p
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-3)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                marginBottom: 8,
              }}
            >
              Completude
            </p>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 6,
              }}
            >
              <p
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  fontFamily: "var(--font-mono)",
                  color: "var(--color-text)",
                  lineHeight: 1,
                }}
              >
                {Math.round(signal.completeness_score * 100)}%
              </p>
              {signal.completeness_status && (
                <span
                  style={{
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                    letterSpacing: "0.1em",
                    padding: "2px 6px",
                    borderRadius: 3,
                    background:
                      signal.completeness_status === "sufficient"
                        ? "rgba(0,200,100,0.1)"
                        : "rgba(255,100,0,0.1)",
                    color:
                      signal.completeness_status === "sufficient"
                        ? "var(--color-low)"
                        : "var(--color-high)",
                    border: `1px solid ${
                      signal.completeness_status === "sufficient"
                        ? "rgba(0,200,100,0.3)"
                        : "rgba(255,100,0,0.3)"
                    }`,
                  }}
                >
                  {signal.completeness_status === "sufficient"
                    ? "SUFICIENTE"
                    : "INSUFICIENTE"}
                </span>
              )}
            </div>
            <div
              style={{
                height: 4,
                background: "var(--color-surface-2)",
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${Math.round(signal.completeness_score * 100)}%`,
                  background:
                    signal.completeness_status === "sufficient"
                      ? "var(--color-low)"
                      : "var(--color-high)",
                  borderRadius: 2,
                }}
              />
            </div>
          </Card>
        )}

        {/* Period */}
        {(signal.period_start || signal.period_end) && (
          <Card>
            <p
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-3)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                marginBottom: 8,
              }}
            >
              Período
            </p>
            <p style={{ fontSize: 13, color: "var(--color-text)", marginBottom: 2 }}>
              {signal.period_start ? formatDate(signal.period_start) : "—"}
            </p>
            <p
              style={{
                fontSize: 11,
                color: "var(--color-text-3)",
                marginBottom: 6,
              }}
            >
              até
            </p>
            <p style={{ fontSize: 13, color: "var(--color-text)" }}>
              {signal.period_end ? formatDate(signal.period_end) : "presente"}
            </p>
          </Card>
        )}

        {/* Case link */}
        {signal.case_id && (
          <Card>
            <p
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-3)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                marginBottom: 8,
              }}
            >
              Caso vinculado
            </p>
            <Link
              href={`/radar/dossie/${signal.case_id}`}
              style={{
                fontSize: 13,
                color: "var(--color-amber)",
                textDecoration: "none",
                display: "flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              {signal.case_title ?? signal.case_id.slice(0, 8)} →
            </Link>
          </Card>
        )}

        {/* Created */}
        <Card>
          <p
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: "var(--color-text-3)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: 6,
            }}
          >
            Criado
          </p>
          <p style={{ fontSize: 12, color: "var(--color-text-2)" }}>
            {formatDate(signal.created_at)}
          </p>
          <p style={{ fontSize: 11, color: "var(--color-text-3)", marginTop: 2 }}>
            {relativeTime(signal.created_at)}
          </p>
        </Card>
      </div>
    </div>
  );
}

// ── EvidenciasTab ────────────────────────────────────────────────────────────

function EvidenciasTab({
  signal,
  evidence,
  loading,
  offset,
  pageSize,
  onPageChange,
}: {
  signal: SignalDetail;
  evidence: SignalEvidencePage | null;
  loading: boolean;
  offset: number;
  pageSize: number;
  onPageChange: (offset: number) => void;
}) {
  const refs = signal.evidence_refs ?? [];
  const stats = signal.evidence_stats;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Evidence refs */}
      {refs.length > 0 && (
        <div>
          <SectionHeader n={1} title="Referências de Evidência" />
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {refs.map((ref, i) => (
              <Card key={i}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 12,
                  }}
                >
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-text-3)",
                      background: "var(--color-surface-2)",
                      padding: "2px 6px",
                      borderRadius: 3,
                      flexShrink: 0,
                      marginTop: 2,
                    }}
                  >
                    {ref.ref_type}
                  </span>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: 13, color: "var(--color-text)", marginBottom: 4 }}>
                      {ref.description}
                    </p>
                    {ref.url && (
                      <a
                        href={ref.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: 11,
                          color: "var(--color-amber)",
                          textDecoration: "none",
                        }}
                      >
                        {ref.url} ↗
                      </a>
                    )}
                    {ref.ref_id && !ref.url && (
                      <span
                        style={{
                          fontSize: 11,
                          fontFamily: "var(--font-mono)",
                          color: "var(--color-text-3)",
                        }}
                      >
                        {ref.ref_id}
                      </span>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Events */}
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <SectionHeader n={refs.length > 0 ? 2 : 1} title="Eventos de Evidência" />
          {stats && (
            <div style={{ display: "flex", gap: 12 }}>
              <span style={{ fontSize: 11, color: "var(--color-text-3)" }}>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontWeight: 600,
                    color: "var(--color-text-2)",
                  }}
                >
                  {stats.total_events}
                </span>{" "}
                total
              </span>
              {stats.omitted_refs > 0 && (
                <span style={{ fontSize: 11, color: "var(--color-text-3)" }}>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-medium)",
                    }}
                  >
                    {stats.omitted_refs}
                  </span>{" "}
                  omitidos
                </span>
              )}
            </div>
          )}
        </div>

        {loading ? (
          <div
            style={{
              textAlign: "center",
              padding: "40px",
              color: "var(--color-text-3)",
              fontSize: 13,
            }}
          >
            Carregando evidências…
          </div>
        ) : evidence && evidence.items.length > 0 ? (
          <>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {evidence.items.map((item) => (
                <Card key={item.event_id}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 12,
                      marginBottom: 8,
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          marginBottom: 6,
                          flexWrap: "wrap",
                        }}
                      >
                        <span
                          style={{
                            fontSize: 10,
                            fontFamily: "var(--font-mono)",
                            color: "var(--color-text-3)",
                            background: "var(--color-surface-2)",
                            padding: "2px 6px",
                            borderRadius: 3,
                          }}
                        >
                          {item.modality}
                        </span>
                        <span
                          style={{
                            fontSize: 10,
                            fontFamily: "var(--font-mono)",
                            color: "var(--color-text-3)",
                          }}
                        >
                          {item.source_connector}
                        </span>
                        {item.occurred_at && (
                          <span
                            style={{ fontSize: 11, color: "var(--color-text-3)" }}
                          >
                            {formatDate(item.occurred_at)}
                          </span>
                        )}
                        {item.value_brl != null && (
                          <span
                            style={{
                              fontSize: 12,
                              fontFamily: "var(--font-mono)",
                              fontWeight: 600,
                              color: "var(--color-amber)",
                              marginLeft: "auto",
                            }}
                          >
                            {formatBRL(item.value_brl)}
                          </span>
                        )}
                      </div>
                      <p
                        style={{
                          fontSize: 13,
                          color: "var(--color-text)",
                          lineHeight: 1.5,
                          marginBottom: 6,
                        }}
                      >
                        {item.description}
                      </p>
                      <p
                        style={{
                          fontSize: 11,
                          color: "var(--color-text-3)",
                          fontStyle: "italic",
                        }}
                      >
                        {item.evidence_reason}
                      </p>
                    </div>
                  </div>
                  <div
                    style={{
                      borderTop: "1px solid var(--color-border)",
                      paddingTop: 6,
                      marginTop: 4,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                      }}
                    >
                      {item.catmat_group} · {item.source_id}
                    </span>
                  </div>
                </Card>
              ))}
            </div>

            {/* Pagination */}
            {evidence.total > pageSize && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginTop: 16,
                  padding: "12px 0",
                  borderTop: "1px solid var(--color-border)",
                }}
              >
                <span style={{ fontSize: 12, color: "var(--color-text-3)" }}>
                  {offset + 1}–{Math.min(offset + pageSize, evidence.total)} de{" "}
                  {evidence.total}
                </span>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    disabled={offset === 0}
                    onClick={() => onPageChange(Math.max(0, offset - pageSize))}
                    style={{
                      padding: "6px 14px",
                      fontSize: 12,
                      background: "var(--color-surface-2)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      color:
                        offset === 0
                          ? "var(--color-text-3)"
                          : "var(--color-text)",
                      cursor: offset === 0 ? "not-allowed" : "pointer",
                      opacity: offset === 0 ? 0.5 : 1,
                    }}
                  >
                    ← Anterior
                  </button>
                  <button
                    disabled={offset + pageSize >= evidence.total}
                    onClick={() => onPageChange(offset + pageSize)}
                    style={{
                      padding: "6px 14px",
                      fontSize: 12,
                      background: "var(--color-surface-2)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "var(--radius-md)",
                      color:
                        offset + pageSize >= evidence.total
                          ? "var(--color-text-3)"
                          : "var(--color-text)",
                      cursor:
                        offset + pageSize >= evidence.total
                          ? "not-allowed"
                          : "pointer",
                      opacity: offset + pageSize >= evidence.total ? 0.5 : 1,
                    }}
                  >
                    Próxima →
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div
            style={{
              textAlign: "center",
              padding: "40px",
              color: "var(--color-text-3)",
              fontSize: 13,
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
            }}
          >
            Nenhuma evidência encontrada.
          </div>
        )}
      </div>
    </div>
  );
}

// ── EntidadesTab ─────────────────────────────────────────────────────────────

function EntidadesTab({
  signal,
  graph,
  graphLoading,
  graphData,
  showExpanded,
  setShowExpanded,
  selectedNode,
  setSelectedNode,
}: {
  signal: SignalDetail;
  graph: SignalGraphResponse | null;
  graphLoading: boolean;
  graphData: { nodes: GNode[]; links: GLink[] };
  showExpanded: boolean;
  setShowExpanded: (v: boolean) => void;
  selectedNode: GNode | null;
  setSelectedNode: (n: GNode | null) => void;
}) {
  const entities = signal.entities ?? [];

  const TYPE_ICON: Record<string, string> = {
    person: "👤",
    company: "🏢",
    org: "🏛",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Entity list */}
      {entities.length > 0 && (
        <div>
          <SectionHeader n={1} title="Entidades Envolvidas" />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 10,
            }}
          >
            {entities.map((ent) => (
              <Card key={ent.id}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    marginBottom: 8,
                  }}
                >
                  <span style={{ fontSize: 20 }}>
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
                    <p
                      style={{
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                        textTransform: "uppercase",
                      }}
                    >
                      {ent.type}
                    </p>
                  </div>
                </div>

                {/* Roles */}
                {ent.roles.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 4,
                      marginBottom: 8,
                    }}
                  >
                    {ent.roles_detailed
                      ? ent.roles_detailed.map((r) => (
                          <span
                            key={r.code}
                            style={{
                              fontSize: 10,
                              fontFamily: "var(--font-mono)",
                              color: "var(--color-text-3)",
                              background: "var(--color-surface-2)",
                              border: "1px solid var(--color-border)",
                              padding: "2px 6px",
                              borderRadius: 10,
                            }}
                          >
                            {r.label}
                            {r.count_in_signal > 1 && (
                              <span
                                style={{
                                  marginLeft: 4,
                                  color: "var(--color-amber)",
                                }}
                              >
                                ×{r.count_in_signal}
                              </span>
                            )}
                          </span>
                        ))
                      : ent.roles.map((r) => (
                          <span
                            key={r}
                            style={{
                              fontSize: 10,
                              fontFamily: "var(--font-mono)",
                              color: "var(--color-text-3)",
                              background: "var(--color-surface-2)",
                              border: "1px solid var(--color-border)",
                              padding: "2px 6px",
                              borderRadius: 10,
                            }}
                          >
                            {r}
                          </span>
                        ))}
                  </div>
                )}

                {/* Identifiers */}
                {Object.keys(ent.identifiers).length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    {Object.entries(ent.identifiers)
                      .filter(([k]) => !["name_key", "cpf_hash"].includes(k))
                      .slice(0, 3)
                      .map(([k, v]) => (
                        <span
                          key={k}
                          style={{
                            fontSize: 11,
                            fontFamily: "var(--font-mono)",
                            color: "var(--color-text-3)",
                          }}
                        >
                          {k.toUpperCase()}: {v}
                        </span>
                      ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Graph section */}
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <SectionHeader n={entities.length > 0 ? 2 : 1} title="Rede de Relacionamentos" />
          {graph && graph.overview.expanded_nodes && (
            <button
              onClick={() => setShowExpanded(!showExpanded)}
              style={{
                fontSize: 12,
                color: showExpanded ? "var(--color-amber)" : "var(--color-text-3)",
                background: "none",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "4px 10px",
                cursor: "pointer",
              }}
            >
              {showExpanded ? "← Ocultar expandido" : "Mostrar rede expandida →"}
            </button>
          )}
        </div>

        {graphLoading ? (
          <div
            style={{
              height: 400,
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--color-text-3)",
              fontSize: 13,
            }}
          >
            Carregando grafo…
          </div>
        ) : graph && graphData.nodes.length > 0 ? (
          <div
            style={{
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              padding: "16px",
              background: "var(--color-surface)",
            }}
          >
            {/* Node list — canvas requires extra maps not available here */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                gap: 8,
              }}
            >
              {graphData.nodes.map((n) => (
                <button
                  key={n.id}
                  onClick={() => setSelectedNode(selectedNode?.id === n.id ? null : n)}
                  style={{
                    padding: "8px 12px",
                    background:
                      selectedNode?.id === n.id
                        ? "var(--color-surface-3)"
                        : "var(--color-surface-2)",
                    border: `1px solid ${
                      n.isSeed
                        ? "var(--color-amber)"
                        : selectedNode?.id === n.id
                        ? "var(--color-amber-dim)"
                        : "var(--color-border)"
                    }`,
                    borderRadius: "var(--radius-md)",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <p
                    style={{
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-text-3)",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      marginBottom: 2,
                    }}
                  >
                    {n.node_type}
                    {n.isSeed && (
                      <span style={{ color: "var(--color-amber)", marginLeft: 4 }}>
                        ★
                      </span>
                    )}
                  </p>
                  <p
                    style={{
                      fontSize: 12,
                      color: "var(--color-text)",
                      fontWeight: 500,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {n.label}
                  </p>
                </button>
              ))}
            </div>
            {graphData.links.length > 0 && (
              <p
                style={{
                  fontSize: 11,
                  color: "var(--color-text-3)",
                  marginTop: 12,
                  fontFamily: "var(--font-mono)",
                }}
              >
                {graphData.nodes.length} nós · {graphData.links.length} conexões
              </p>
            )}
          </div>
        ) : (
          <div
            style={{
              height: 200,
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--color-text-3)",
              fontSize: 13,
            }}
          >
            Dados de grafo não disponíveis.
          </div>
        )}
      </div>
    </div>
  );
}

// ── AnaliseTab ───────────────────────────────────────────────────────────────

function AnaliseTab({
  signal,
  legalBasis,
  relatedSignals,
  graph,
}: {
  signal: SignalDetail;
  legalBasis: TypologyLegalBasis | null;
  relatedSignals: RelatedSignal[];
  graph: SignalGraphResponse | null;
}) {
  let sectionN = 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Pattern Story */}
      {graph?.pattern_story && (
        <div>
          <SectionHeader n={sectionN++} title="História do Padrão" />
          <Card>
            <p
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text)",
                marginBottom: 8,
              }}
            >
              {graph.pattern_story.pattern_label}
            </p>
            {(graph.pattern_story.started_at || graph.pattern_story.ended_at) && (
              <p
                style={{
                  fontSize: 12,
                  color: "var(--color-text-3)",
                  fontFamily: "var(--font-mono)",
                  marginBottom: 10,
                }}
              >
                {graph.pattern_story.started_at
                  ? formatDate(graph.pattern_story.started_at)
                  : "—"}{" "}
                →{" "}
                {graph.pattern_story.ended_at
                  ? formatDate(graph.pattern_story.ended_at)
                  : "presente"}
              </p>
            )}
            <p
              style={{
                fontSize: 13,
                color: "var(--color-text-2)",
                lineHeight: 1.6,
                marginBottom: 12,
              }}
            >
              {graph.pattern_story.why_flagged}
            </p>

            {graph.pattern_story.started_from_entities.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <p
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-3)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: 6,
                  }}
                >
                  Originado em
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {graph.pattern_story.started_from_entities.map((e) => (
                    <span
                      key={e.entity_id}
                      style={{
                        fontSize: 12,
                        color: "var(--color-text)",
                        background: "var(--color-surface-2)",
                        border: "1px solid var(--color-border)",
                        padding: "3px 8px",
                        borderRadius: 4,
                      }}
                    >
                      {e.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {graph.pattern_story.flow_targets.length > 0 && (
              <div>
                <p
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-3)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: 6,
                  }}
                >
                  Destinos do fluxo
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {graph.pattern_story.flow_targets.map((e) => (
                    <span
                      key={e.entity_id}
                      style={{
                        fontSize: 12,
                        color: "var(--color-text)",
                        background: "var(--color-surface-2)",
                        border: "1px solid var(--color-border)",
                        padding: "3px 8px",
                        borderRadius: 4,
                      }}
                    >
                      {e.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Completeness */}
      {signal.completeness_score != null && (
        <div>
          <SectionHeader n={sectionN++} title="Completude da Análise" />
          <Card>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: "50%",
                  background: `conic-gradient(var(--color-amber) ${Math.round(signal.completeness_score * 100 * 3.6)}deg, var(--color-surface-2) 0deg)`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    width: 34,
                    height: 34,
                    borderRadius: "50%",
                    background: "var(--color-surface)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 11,
                    fontWeight: 700,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text)",
                  }}
                >
                  {Math.round(signal.completeness_score * 100)}%
                </div>
              </div>
              <div>
                <p style={{ fontSize: 13, color: "var(--color-text)", fontWeight: 600 }}>
                  {signal.completeness_status === "sufficient"
                    ? "Evidências suficientes"
                    : "Evidências insuficientes"}
                </p>
                <p style={{ fontSize: 12, color: "var(--color-text-3)", marginTop: 2 }}>
                  {signal.completeness_status === "sufficient"
                    ? "O sinal possui base factual adequada."
                    : "Podem existir lacunas de informação."}
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Legal Basis */}
      {legalBasis && (
        <div>
          <SectionHeader n={sectionN++} title="Base Legal" />
          <Card style={{ marginBottom: 12 }}>
            <p
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text)",
                marginBottom: 6,
              }}
            >
              {legalBasis.name}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
              {legalBasis.corruption_types.map((ct) => (
                <span
                  key={ct}
                  style={{
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-high)",
                    background: "rgba(255,100,0,0.08)",
                    border: "1px solid rgba(255,100,0,0.2)",
                    padding: "2px 6px",
                    borderRadius: 3,
                  }}
                >
                  {ct}
                </span>
              ))}
              {legalBasis.spheres.map((s) => (
                <span
                  key={s}
                  style={{
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-3)",
                    background: "var(--color-surface-2)",
                    border: "1px solid var(--color-border)",
                    padding: "2px 6px",
                    borderRadius: 3,
                  }}
                >
                  {s}
                </span>
              ))}
            </div>
            <p
              style={{
                fontSize: 13,
                color: "var(--color-text-2)",
                lineHeight: 1.6,
                marginBottom: 12,
              }}
            >
              {legalBasis.description_legal}
            </p>

            {legalBasis.law_articles.length > 0 && (
              <div>
                <p
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-3)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    marginBottom: 8,
                  }}
                >
                  Artigos de Lei
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {legalBasis.law_articles.map((art, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "8px 10px",
                        background: "var(--color-surface-2)",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      <span
                        style={{
                          fontSize: 11,
                          fontFamily: "var(--font-mono)",
                          fontWeight: 600,
                          color: "var(--color-text)",
                          flexShrink: 0,
                        }}
                      >
                        {art.law_name}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          fontFamily: "var(--font-mono)",
                          color: "var(--color-text-3)",
                        }}
                      >
                        {art.article}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          color: "var(--color-text-3)",
                          marginLeft: "auto",
                          fontStyle: "italic",
                        }}
                      >
                        {art.violation_type}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Related Signals */}
      {relatedSignals.length > 0 && (
        <div>
          <SectionHeader n={sectionN++} title="Sinais Relacionados" />
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {relatedSignals.map((rs) => {
              const rSevColor = SEV_COLOR[rs.severity] ?? "var(--color-text-3)";
              return (
                <Link
                  key={rs.id}
                  href={`/signal/${rs.id}`}
                  style={{ textDecoration: "none" }}
                >
                  <div
                    style={{
                      borderLeft: `3px solid ${rSevColor}`,
                      background: "var(--color-surface)",
                      border: `1px solid var(--color-border)`,
                      borderLeftWidth: 3,
                      borderLeftColor: rSevColor,
                      borderRadius: "0 var(--radius-md) var(--radius-md) 0",
                      padding: "12px 14px",
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      cursor: "pointer",
                      transition: "background 0.15s",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--font-mono)",
                        fontWeight: 700,
                        color: rSevColor,
                        background: `${rSevColor}18`,
                        border: `1px solid ${rSevColor}40`,
                        padding: "1px 6px",
                        borderRadius: 3,
                        flexShrink: 0,
                      }}
                    >
                      {SEV_LABEL[rs.severity]}
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-text-3)",
                        flexShrink: 0,
                      }}
                    >
                      {rs.typology_code}
                    </span>
                    <span
                      style={{
                        fontSize: 13,
                        color: "var(--color-text)",
                        flex: 1,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {rs.title}
                    </span>
                    <span
                      style={{
                        fontSize: 12,
                        fontFamily: "var(--font-mono)",
                        fontWeight: 600,
                        color: rSevColor,
                        flexShrink: 0,
                      }}
                    >
                      {Math.round(rs.confidence * 100)}%
                    </span>
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

// ── Main Page ────────────────────────────────────────────────────────────────

export default function SignalDetailPage() {
  const params = useParams();
  const signalId = params["id"] as string;
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") as SignalTab) ?? "dossie";

  const [signal, setSignal] = useState<SignalDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Evidence tab state
  const [evidence, setEvidence] = useState<SignalEvidencePage | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceOffset, setEvidenceOffset] = useState(0);
  const EVIDENCE_PAGE = 15;

  // Entidades tab state
  const [graph, setGraph] = useState<SignalGraphResponse | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [showExpanded, setShowExpanded] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GNode | null>(null);

  // Analise tab state
  const [legalBasis, setLegalBasis] = useState<TypologyLegalBasis | null>(null);
  const [legalLoaded, setLegalLoaded] = useState(false);
  const [relatedSignals, setRelatedSignals] = useState<RelatedSignal[]>([]);
  const [relatedLoaded, setRelatedLoaded] = useState(false);

  // Load signal
  useEffect(() => {
    if (!signalId) return;
    setLoading(true);
    getSignal(signalId)
      .then(setSignal)
      .catch(() => setError("Sinal não encontrado"))
      .finally(() => setLoading(false));
  }, [signalId]);

  // Lazy load evidence
  useEffect(() => {
    if (tab !== "evidencias" || !signalId) return;
    setEvidenceLoading(true);
    getSignalEvidence(signalId, { offset: evidenceOffset, limit: EVIDENCE_PAGE })
      .then(setEvidence)
      .catch(() => {})
      .finally(() => setEvidenceLoading(false));
  }, [tab, signalId, evidenceOffset]);

  // Lazy load graph
  useEffect(() => {
    if (tab !== "entidades" || !signalId || graph) return;
    setGraphLoading(true);
    getSignalGraph(signalId)
      .then(setGraph)
      .catch(() => {})
      .finally(() => setGraphLoading(false));
  }, [tab, signalId, graph]);

  // Lazy load legal basis + related
  useEffect(() => {
    if (tab !== "analise" || !signal) return;
    if (!legalLoaded) {
      setLegalLoaded(true);
      fetchTypologyLegalBasis(signal.typology_code)
        .then(setLegalBasis)
        .catch(() => {});
    }
    if (!relatedLoaded) {
      setRelatedLoaded(true);
      fetchRelatedSignals(signal.id)
        .then(setRelatedSignals)
        .catch(() => {});
    }
  }, [tab, signal, legalLoaded, relatedLoaded]);

  // Graph data memo
  const graphData = useMemo(() => {
    if (!graph) return { nodes: [] as GNode[], links: [] as GLink[] };
    const starterIds = new Set(
      graph.pattern_story.started_from_entities.map((e) => e.entity_id)
    );
    const directNodes: GNode[] = graph.overview.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      node_type: n.node_type,
      entity_id: n.entity_id,
      isSeed: starterIds.has(n.entity_id),
      isFocused: false,
    }));
    const bfsNodes: GNode[] = showExpanded
      ? (graph.overview.expanded_nodes ?? []).map((n) => ({
          id: n.id,
          label: n.label,
          node_type: n.node_type,
          entity_id: n.entity_id,
          isSeed: false,
          isFocused: false,
          isExpanded: true,
        }))
      : [];
    const allNodes = [...directNodes, ...bfsNodes];
    const e2n: Record<string, string> = {};
    for (const n of allNodes) e2n[n.entity_id] = n.id;
    const directLinks: GLink[] = graph.overview.edges.map((e) => ({
      id: e.id,
      source: e.from_node_id,
      target: e.to_node_id,
      type: e.type,
      weight: e.weight,
      isFocused: false,
    }));
    const bfsLinks: GLink[] = showExpanded
      ? (graph.overview.expansion_edges ?? [])
          .map((e) => ({
            id: e.id,
            source: e2n[e.from_entity_id] ?? "",
            target: e2n[e.to_entity_id] ?? "",
            type: e.edge_type,
            weight: e.weight,
            isFocused: false,
            isExpansion: true,
          }))
          .filter((l) => l.source && l.target)
      : [];
    return { nodes: allNodes, links: [...directLinks, ...bfsLinks] };
  }, [graph, showExpanded]);

  function setTab(t: SignalTab) {
    const p = new URLSearchParams(searchParams.toString());
    p.set("tab", t);
    router.replace(`?${p.toString()}`, { scroll: false });
  }

  if (loading) return <LoadingScreen />;
  if (error || !signal) return <ErrorScreen error={error} />;

  const sevColor = SEV_COLOR[signal.severity] ?? "var(--color-text-3)";
  const tabDefs: { key: SignalTab; label: string; count?: number }[] = [
    { key: "dossie", label: "Dossiê" },
    {
      key: "evidencias",
      label: "Evidências",
      count: signal.evidence_stats?.total_events,
    },
    { key: "entidades", label: "Entidades", count: signal.entities?.length },
    { key: "analise", label: "Análise" },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "var(--color-bg)" }}>
      {/* Sticky wrapper */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          background: "var(--color-bg)",
        }}
      >
        {/* Masthead */}
        <div
          style={{ padding: "0 16px", maxWidth: 1056, margin: "0 auto" }}
        >
          <div
            style={{
              borderLeft: `4px solid ${sevColor}`,
              background: "var(--color-surface)",
              borderRadius: "0 var(--radius-lg) var(--radius-lg) 0",
              padding: "16px 20px",
              marginTop: 16,
            }}
          >
            {/* Top row */}
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
                {SEV_LABEL[signal.severity]}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--color-text-3)",
                }}
              >
                {signal.typology_code}
              </span>
              <span
                style={{ fontSize: 12, color: "var(--color-text-2)" }}
              >
                —
              </span>
              <span style={{ fontSize: 12, color: "var(--color-text-2)" }}>
                {signal.typology_name}
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
            {/* Title */}
            <h1
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 20,
                fontWeight: 700,
                color: "var(--color-text)",
                lineHeight: 1.3,
                marginBottom: 8,
                margin: "0 0 8px",
              }}
            >
              {signal.title}
            </h1>
            {/* Meta row */}
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
                    color: sevColor,
                  }}
                >
                  {Math.round(signal.confidence * 100)}%
                </span>{" "}
                confiança
              </span>
              {(signal.period_start || signal.period_end) && (
                <span style={{ fontSize: 12, color: "var(--color-text-3)" }}>
                  {signal.period_start
                    ? formatDate(signal.period_start)
                    : "—"}{" "}
                  →{" "}
                  {signal.period_end
                    ? formatDate(signal.period_end)
                    : "presente"}
                </span>
              )}
              {signal.case_id && (
                <Link
                  href={`/radar/dossie/${signal.case_id}`}
                  style={{
                    fontSize: 12,
                    color: "var(--color-amber)",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    textDecoration: "none",
                  }}
                >
                  Caso: {signal.case_title ?? signal.case_id.slice(0, 8)} →
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Tab strip */}
        <div
          style={{ padding: "0 16px", maxWidth: 1056, margin: "0 auto" }}
        >
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid var(--color-border)",
              marginTop: 8,
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
                    tab === t.key
                      ? "var(--color-amber)"
                      : "var(--color-text-3)",
                  marginBottom: -1,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
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
                        tab === t.key
                          ? "var(--color-amber)"
                          : "var(--color-text-3)",
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

      {/* Tab content */}
      <div
        style={{ maxWidth: 1056, margin: "0 auto", padding: "24px 16px" }}
      >
        {tab === "dossie" && <DossieTab signal={signal} />}
        {tab === "evidencias" && (
          <EvidenciasTab
            signal={signal}
            evidence={evidence}
            loading={evidenceLoading}
            offset={evidenceOffset}
            pageSize={EVIDENCE_PAGE}
            onPageChange={setEvidenceOffset}
          />
        )}
        {tab === "entidades" && (
          <EntidadesTab
            signal={signal}
            graph={graph}
            graphLoading={graphLoading}
            graphData={graphData}
            showExpanded={showExpanded}
            setShowExpanded={setShowExpanded}
            selectedNode={selectedNode}
            setSelectedNode={setSelectedNode}
          />
        )}
        {tab === "analise" && (
          <AnaliseTab
            signal={signal}
            legalBasis={legalBasis}
            relatedSignals={relatedSignals}
            graph={graph}
          />
        )}
      </div>

    </div>
  );
}
