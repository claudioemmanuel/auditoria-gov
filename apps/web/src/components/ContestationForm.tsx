"use client";

import { useState } from "react";
import { Flag, CheckCircle2, AlertTriangle, Info } from "lucide-react";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { Select } from "@/components/Select";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const REPORT_TYPES = [
  { value: "signal_error",  label: "Sinal incorreto ou impreciso" },
  { value: "entity_error",  label: "Dados de entidade incorretos" },
  { value: "duplicate",     label: "Sinal duplicado" },
  { value: "other",         label: "Outro" },
];

interface Props {
  signalId: string;
}

type Status = "idle" | "submitting" | "success" | "error";

export function ContestationForm({ signalId }: Props) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [reportType, setReportType] = useState("signal_error");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");

  const [nameErr, setNameErr] = useState<string | undefined>();
  const [reasonErr, setReasonErr] = useState<string | undefined>();

  function validate(): boolean {
    let ok = true;
    if (name.trim().length < 2) {
      setNameErr("Nome deve ter pelo menos 2 caracteres.");
      ok = false;
    } else {
      setNameErr(undefined);
    }
    if (reason.trim().length < 8) {
      setReasonErr("Descrição deve ter pelo menos 8 caracteres.");
      ok = false;
    } else {
      setReasonErr(undefined);
    }
    return ok;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setStatus("submitting");
    setErrorMsg(null);

    try {
      const body: Record<string, unknown> = {
        signal_id: signalId,
        report_type: reportType,
        requester_name: name.trim(),
        reason: reason.trim(),
      };
      if (email.trim()) body.requester_email = email.trim();
      if (evidenceUrl.trim()) body.evidence_url = evidenceUrl.trim();

      const res = await fetch(`${API_BASE}/public/contestations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error((detail as { detail?: string }).detail ?? `Erro ${res.status}`);
      }

      setStatus("success");
    } catch (err) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Erro ao enviar.");
    }
  }

  if (status === "success") {
    return (
      <div className="rounded-2xl border border-border bg-surface-card p-6 text-center space-y-2">
        <CheckCircle2 className="h-6 w-6 text-success mx-auto" />
        <p className="text-sm font-semibold text-primary">Contestação enviada</p>
        <p className="text-xs text-muted">
          Obrigado pelo relato. Nossa equipe analisará a contestação em breve.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-border bg-surface-card">
      {/* Header toggle */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-6 py-4 text-left"
      >
        <Flag className="h-4 w-4 shrink-0 text-muted" />
        <span className="text-sm font-medium text-secondary">Contestar este sinal</span>
        <span
          className={cn(
            "ml-auto font-mono text-[10px] uppercase tracking-widest text-muted transition-transform duration-150",
            open && "rotate-180",
          )}
        >
          ▾
        </span>
      </button>

      {open && (
        <div className="border-t border-border px-6 pb-6 pt-5 space-y-4">
          <p className="text-xs text-muted leading-relaxed">
            Identificou dados incorretos, desatualizados ou fora de contexto? Descreva o problema
            abaixo. As informações serão revisadas pela equipe técnica.
          </p>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <Select
              label="Tipo de problema"
              options={REPORT_TYPES}
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
            />

            <Input
              label="Seu nome *"
              placeholder="ex: Maria da Silva"
              value={name}
              onChange={(e) => setName(e.target.value)}
              error={nameErr}
              maxLength={255}
            />

            <Input
              label="E-mail (opcional)"
              type="email"
              placeholder="ex: maria@exemplo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              maxLength={255}
            />

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-secondary">
                Descrição do problema *
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Descreva o erro ou inconsistência encontrada..."
                maxLength={5000}
                rows={4}
                className={cn(
                  "rounded-[10px] border bg-surface-card px-3 py-2 text-sm text-primary placeholder:text-placeholder outline-none resize-none transition-colors duration-120",
                  "focus:border-accent focus:ring-1 focus:ring-accent/20",
                  reasonErr ? "border-error" : "border-border",
                )}
              />
              {reasonErr && <p className="text-xs text-error">{reasonErr}</p>}
            </div>

            <Input
              label="URL de evidência (opcional)"
              type="url"
              placeholder="https://www.gov.br/..."
              value={evidenceUrl}
              onChange={(e) => setEvidenceUrl(e.target.value)}
              maxLength={2048}
            />

            {status === "error" && errorMsg && (
              <div className="flex items-center gap-2 rounded-lg border border-error/30 bg-severity-critical-bg px-3 py-2">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-error" />
                <p className="text-xs text-error">{errorMsg}</p>
              </div>
            )}

            <Button
              type="submit"
              variant="secondary"
              size="sm"
              loading={status === "submitting"}
              className="w-full"
            >
              Enviar contestação
            </Button>
          </form>
        </div>
      )}
    </div>
  );
}

// ── Legal disclaimer ──────────────────────────────────────────────────────────

export function SignalDisclaimer() {
  return (
    <div className="flex gap-3 rounded-2xl border border-border bg-surface-subtle px-5 py-4">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted" />
      <p className="text-xs leading-relaxed text-muted">
        <strong className="font-semibold text-secondary">Aviso legal:</strong> Os dados exibidos
        são coletados exclusivamente de fontes oficiais do Governo Federal (PNCP, TransfereGov,
        Portal da Transparência). Este sinal constitui um <em>indício estatístico</em> para
        orientar investigações — não implica prova de irregularidade nem juízo de valor sobre
        pessoas ou entidades. A decisão de apurar cabe exclusivamente às autoridades competentes.
        O uso indevido destas informações é de responsabilidade do usuário.
      </p>
    </div>
  );
}
