"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import { askDashboard, type AskAnswer } from "../../lib/analytics-provider/ask";
import type { AnalyticsRequest } from "../../lib/analytics-provider/contracts";
import { RetroButton } from "../ui/RetroButton";
import { RetroInput } from "../ui/RetroInput";

const labels: Record<AskAnswer["status"], string> = {
  ok: "Answer", partial: "Partial answer", insufficient_evidence: "Insufficient evidence",
  refused: "Unsupported question", unavailable: "Analytics unavailable",
};

export function AskRetailPulse({ selection, unavailable }: { selection?: AnalyticsRequest; unavailable?: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskAnswer | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selection || question.trim().length < 3 || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setPending(true);
    setError("");
    setAnswer(null);
    try {
      const result = await askDashboard(question, selection, controller.signal);
      if (!controller.signal.aborted) setAnswer(result);
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Ask RetailPulse is unavailable.");
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setPending(false);
    }
  }

  return (
    <section aria-labelledby="ask-retailpulse-heading" className="sticky bottom-0 z-20 rounded-xl border border-border-soft bg-surface px-3 py-2 shadow-lg">
      <h2 id="ask-retailpulse-heading" className="text-sm font-semibold">Ask RetailPulse</h2>
      <p className="text-xs text-text-muted">{unavailable ?? "Ask about the configured dashboard window and filters."}</p>
      <form onSubmit={submit} aria-busy={pending} className="mt-1.5 flex items-center gap-2">
        <RetroInput aria-label="Question for Ask RetailPulse" placeholder="Ask about store performance"
          value={question} onChange={(event) => setQuestion(event.target.value)} maxLength={2000} disabled={!selection || pending} />
        <RetroButton type="submit" disabled={!selection || pending || question.trim().length < 3}>Ask</RetroButton>
      </form>
      {pending && <p role="status" className="mt-2 text-sm text-text-muted">Checking analytics…</p>}
      {error && <p role="alert" className="mt-2 text-sm text-danger">{error}</p>}
      {answer && (
        <div className="mt-2 max-h-[35vh] space-y-2 overflow-auto text-sm" role="status">
          <p className="font-semibold">{labels[answer.status]}{answer.synthetic && " · Synthetic backend data"}</p>
          <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{answer.response}</p>
          {(answer.citations.length > 0 || answer.limitations.length > 0) && (
            <details>
              <summary className="cursor-pointer font-semibold">Evidence and limitations</summary>
              <ul className="mt-1 list-disc space-y-1 pl-5 [overflow-wrap:anywhere]">
                {answer.citations.map((citation, index) => (
                  <li key={index}>{citation.source} · {citation.truncated ? `${citation.ids.length} of ${citation.matched_count} records` : `${citation.matched_count} records`}
                    <span className="block text-text-muted">{citation.ids.join(", ")}</span>
                  </li>
                ))}
                {answer.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
              </ul>
            </details>
          )}
        </div>
      )}
    </section>
  );
}
