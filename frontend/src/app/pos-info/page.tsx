"use client";

import { FormEvent, useState } from "react";
import { RetroButton, RetroInput, RetroWindow } from "@/components/ui";
import { askPos } from "@/lib/pos/api";
import type { PosQueryAnswer } from "@/lib/pos/types";

type Message = {
  text: string;
  isUser?: boolean;
  citations?: PosQueryAnswer["citations"];
};

const QUICK_PROMPTS = [
  "Summarize POS performance",
  "Which products need restocking?",
  "Show top selling products",
  "Explain purchase conversion",
];

const INTRO_MESSAGE: Message = {
  text: "Ask about POS metrics, product trends, conversion, anomalies, or inventory recommendations. Answers cite internal evidence from the latest analytics run.",
};

function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={`flex ${message.isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[90%] rounded-lg border px-4 py-3 text-sm leading-relaxed",
          message.isUser
            ? "rounded-br-sm border-accent/40 bg-accent/10 text-text"
            : "rounded-bl-sm border-border-soft bg-bg text-text-muted",
        ].join(" ")}
      >
        {!message.isUser && (
          <p className="mb-1 font-mono text-[10px] font-bold uppercase tracking-widest text-accent">
            POS assistant
          </p>
        )}
        <p>{message.text}</p>
        {message.citations?.length ? (
          <div className="mt-3 space-y-1 border-t border-border-soft pt-2">
            {message.citations.map((citation) => (
              <p key={citation.id} className="font-mono text-[10px] leading-relaxed text-text-muted">
                [{citation.id}] {citation.period.from} to {citation.period.to}
              </p>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function PosInfoPage() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([INTRO_MESSAGE]);
  const [submitting, setSubmitting] = useState(false);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  async function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    setSubmitting(true);
    setMessages((current) => [...current, { text: trimmedQuery, isUser: true }]);
    setQuery("");
    try {
      const answer = await askPos(trimmedQuery, { from: dateFrom || undefined, to: dateTo || undefined, horizon: 7 });
      setMessages((current) => [...current, { text: answer.answer, citations: answer.citations }]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        { text: error instanceof Error ? error.message : "The POS assistant could not reach internal evidence." },
      ]);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg px-4 py-8 md:px-6 md:py-12">
      <div className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <RetroWindow title="POS Info - Cited Store Data Assistant">
          <div className="flex min-h-[560px] flex-col">
            <div className="mb-6 flex items-start justify-between gap-4 border-b border-border-soft pb-5">
              <div>
                <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
                  Pillar 2 / POS analytics RAG
                </p>
                <h1 className="font-heading text-2xl font-bold text-text md:text-3xl">
                  Ask the analytics run
                </h1>
                <p className="mt-2 max-w-xl text-sm text-text-muted">
                  The assistant retrieves calculated evidence and cites internal IDs. Unsupported questions return insufficient evidence.
                </p>
              </div>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto pr-1" aria-live="polite">
              {messages.map((message, index) => (
                <MessageBubble key={`${message.text}-${index}`} message={message} />
              ))}
            </div>

            <form onSubmit={submitQuery} className="mt-6 border-t border-border-soft pt-4">
              <div className="grid gap-2 sm:grid-cols-[1fr_1fr]">
                <RetroInput label="From" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                <RetroInput label="To" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
              </div>
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <RetroInput
                  aria-label="Ask the POS assistant"
                  className="flex-1"
                  placeholder="e.g. Which SKUs should I restock?"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
                <RetroButton type="submit" variant="primary" className="sm:self-end" disabled={submitting}>
                  {submitting ? "Checking" : "Ask"}
                </RetroButton>
              </div>
            </form>
          </div>
        </RetroWindow>

        <aside className="space-y-6">
          <RetroWindow title="Try a question">
            <div className="space-y-2">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setQuery(prompt)}
                  className="w-full rounded-md border border-border-soft bg-bg px-3 py-2 text-left text-sm text-text transition-colors hover:border-accent hover:text-accent"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </RetroWindow>

          <RetroWindow title="Evidence Boundary">
            <ul className="space-y-3 text-xs leading-relaxed text-text-muted">
              <li><strong className="text-text">Calculations:</strong> deterministic POS analytics.</li>
              <li><strong className="text-text">Retrieval:</strong> evidence from completed analysis runs.</li>
              <li><strong className="text-text">Security:</strong> manager cookie required for POS APIs.</li>
            </ul>
          </RetroWindow>
        </aside>
      </div>
    </main>
  );
}
