"use client";

import { FormEvent, useState } from "react";
import { Badge, RetroButton, RetroCard, RetroInput, RetroWindow } from "@/components/ui";
import { answerPosQuestion, POS_EVIDENCE, type EvidenceCitation } from "@/lib/pos/dummy-assistant";

type Message = {
  text: string;
  isUser?: boolean;
  citations?: EvidenceCitation[];
};

const QUICK_PROMPTS = [
  "Summarize POS performance",
  "Which products need restocking?",
  "Compare Maggi and Knorr",
  "How is conversion calculated?",
];

const INTRO_MESSAGE: Message = {
  text: "Ask about the demo POS run. I answer from dummy analytics evidence and show internal evidence IDs, just like the planned RAG flow.",
};

function MessageBubble({ message }: { message: Message }) {
  return (
    <div className={`flex ${message.isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[92%] rounded-lg border px-4 py-3 text-sm leading-relaxed",
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
          <div className="mt-3 space-y-2 border-t border-border-soft pt-2">
            {message.citations.map((citation) => (
              <p key={citation.id} className="font-mono text-[10px] leading-relaxed text-text-muted">
                [{citation.id}] {citation.period}
              </p>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function EvidenceCard({ evidence }: { evidence: EvidenceCitation }) {
  return (
    <div className="rounded-md border border-border-soft bg-bg p-3">
      <div className="mb-2 flex items-start justify-between gap-2">
        <p className="font-heading text-sm font-bold text-text">{evidence.title}</p>
        <Badge variant="neutral">{evidence.id}</Badge>
      </div>
      <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-text-muted">{evidence.period}</p>
      <p className="text-xs leading-relaxed text-text-muted">{evidence.text}</p>
    </div>
  );
}

export default function PosInfoPage() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([INTRO_MESSAGE]);

  function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    const answer = answerPosQuestion(trimmed);
    setMessages((current) => [
      ...current,
      { text: trimmed, isUser: true },
      { text: answer.answer, citations: answer.citations },
    ]);
    setQuery("");
  }

  return (
    <main className="min-h-screen bg-bg px-4 py-8 md:px-6 md:py-12">
      <div className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <RetroWindow title="POS Assistant - Demo Evidence Chat">
          <div className="flex min-h-[560px] flex-col">
            <div className="mb-6 border-b border-border-soft pb-5">
              <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-accent">
                Dummy RAG output / Defense demo
              </p>
              <h1 className="font-heading text-2xl font-bold text-text md:text-3xl">
                Ask the POS analytics run
              </h1>
              <p className="mt-2 max-w-xl text-sm text-text-muted">
                This branch keeps dummy data only. The assistant retrieves prepared evidence snippets and cites them so the final demo mirrors the planned RAG experience.
              </p>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto pr-1" aria-live="polite">
              {messages.map((message, index) => (
                <MessageBubble key={`${message.text}-${index}`} message={message} />
              ))}
            </div>

            <form onSubmit={submitQuery} className="mt-6 border-t border-border-soft pt-4">
              <div className="flex flex-col gap-2 sm:flex-row">
                <RetroInput
                  aria-label="Ask the POS assistant"
                  className="flex-1"
                  placeholder="e.g. Which SKUs should I restock?"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
                <RetroButton type="submit" variant="primary" className="sm:self-end">
                  Ask
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

          <RetroWindow title="Demo KPIs">
            <div className="grid grid-cols-2 gap-3">
              <RetroCard label="Revenue"><p className="font-mono text-lg font-bold text-text">Rs. 184k</p></RetroCard>
              <RetroCard label="Conversion"><p className="font-mono text-lg font-bold text-text">68.0%</p></RetroCard>
              <RetroCard label="Forecast"><p className="font-mono text-lg font-bold text-text">7 days</p></RetroCard>
              <RetroCard label="Action"><p className="font-mono text-lg font-bold text-danger">RESTOCK</p></RetroCard>
            </div>
          </RetroWindow>

          <RetroWindow title="Evidence Library">
            <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
              {POS_EVIDENCE.map((evidence) => (
                <EvidenceCard key={evidence.id} evidence={evidence} />
              ))}
            </div>
          </RetroWindow>
        </aside>
      </div>
    </main>
  );
}
