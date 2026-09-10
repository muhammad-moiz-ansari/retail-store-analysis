"use client";

import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { Badge, RetroButton, RetroCard, RetroInput, RetroWindow } from "@/components/ui";

type ProviderStatus = {
  huggingFace?: {
    configured: boolean;
    model: string;
    routerUrl: string;
  };
  elevenLabs?: {
    configured: boolean;
    voiceId: string;
    modelId: string;
    outputFormat: string;
  };
};

type GenerateResponse = {
  script: {
    script: string;
    provider: string;
    fallback: boolean;
    reason?: string;
  };
  audio?: {
    audioBase64: string | null;
    contentType: string;
    provider: string;
    fallback: boolean;
    reason?: string;
  } | null;
};

const EVENT_TYPES = [
  { value: "unattended_customer", label: "Unattended Customer" },
  { value: "unstaffed_zone", label: "Unstaffed Zone" },
  { value: "crowding", label: "Crowding" },
  { value: "manual_event", label: "Manual Update" },
];

const ZONES = [
  "Entrance Lobby",
  "Aisle 1 - Snacks",
  "Aisle 2 - Beverages",
  "Aisle 3 - Household",
  "Promo Display",
  "Checkout Counter",
];

export default function VoiceAgentPage() {
  const [status, setStatus] = useState<ProviderStatus>({});
  const [eventType, setEventType] = useState("unattended_customer");
  const [severity, setSeverity] = useState("high");
  const [zoneName, setZoneName] = useState("Aisle 2 - Beverages");
  const [title, setTitle] = useState("Customer waiting without assistance");
  const [instruction, setInstruction] = useState("Please approach the customer, ask what they need, and confirm the zone is covered.");
  const [context, setContext] = useState("Customer has waited longer than the configured unattended threshold.");
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/backend/voice-agent/status", { cache: "no-store" })
      .then((response) => (response.ok ? response.json() : {}))
      .then(setStatus)
      .catch(() => setStatus({}));
  }, []);

  const audioUrl = useMemo(() => {
    if (!result?.audio?.audioBase64) return "";
    return `data:${result.audio.contentType};base64,${result.audio.audioBase64}`;
  }, [result]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch("/api/backend/voice-agent/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          includeAudio: true,
          event: {
            eventType,
            severity,
            zoneName,
            title,
            context,
            instruction,
            source: "manager-demo",
          },
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || data.detail || "Voice agent generation failed");
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice agent generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-[1180px] px-4 py-8 md:px-6 md:py-12 space-y-8">
      <RetroWindow title="Voice Agent - Script & Speech Generator">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-accent">
              Orchestrator → NLP Agent → ElevenLabs
            </p>
            <h1 className="mt-2 font-heading text-3xl font-bold text-text">
              Generate staff-ready voice updates
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-muted">
              Turn an operational event into a concise spoken script, then synthesize it into playable audio for the demo voice agent.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={status.huggingFace?.configured ? "success" : "neutral"}>
              HF {status.huggingFace?.configured ? "Configured" : "Fallback"}
            </Badge>
            <Badge variant={status.elevenLabs?.configured ? "success" : "neutral"}>
              ElevenLabs {status.elevenLabs?.configured ? "Configured" : "No Key"}
            </Badge>
          </div>
        </div>
      </RetroWindow>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <RetroWindow title="Orchestration Event">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <SelectField label="Event Type" value={eventType} onChange={setEventType} options={EVENT_TYPES} />
              <SelectField
                label="Severity"
                value={severity}
                onChange={setSeverity}
                options={[
                  { value: "high", label: "High" },
                  { value: "medium", label: "Medium" },
                  { value: "low", label: "Low" },
                ]}
              />
            </div>

            <SelectField
              label="Target Zone"
              value={zoneName}
              onChange={setZoneName}
              options={ZONES.map((zone) => ({ value: zone, label: zone }))}
            />

            <RetroInput label="Event Title" value={title} onChange={(event) => setTitle(event.target.value)} />

            <TextAreaField label="Event Context" value={context} onChange={setContext} rows={3} />
            <TextAreaField label="Staff Instruction" value={instruction} onChange={setInstruction} rows={4} />

            <div className="flex items-center gap-3">
              <RetroButton type="submit" variant="primary" disabled={loading}>
                {loading ? "Generating..." : "Generate Voice Agent Output"}
              </RetroButton>
              {error && <span className="text-sm font-semibold text-danger">{error}</span>}
            </div>
          </form>
        </RetroWindow>

        <RetroWindow title="Voice Agent Output">
          <div className="space-y-5">
            <RetroCard label="Generated Script">
              <p className="min-h-[120px] whitespace-pre-wrap pt-2 text-sm leading-relaxed text-text">
                {result?.script.script || "Generate an event to create the staff voice script."}
              </p>
              {result?.script && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge variant={result.script.fallback ? "neutral" : "success"}>{result.script.provider}</Badge>
                  {result.script.reason && <Badge variant="neutral">{result.script.reason}</Badge>}
                </div>
              )}
            </RetroCard>

            <RetroCard label="ElevenLabs Audio">
              {audioUrl ? (
                <audio className="mt-2 w-full" controls src={audioUrl} />
              ) : (
                <p className="pt-2 text-sm text-text-muted">
                  Add `ELEVENLABS_API_KEY` to your environment to synthesize playable audio.
                </p>
              )}
              {result?.audio && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge variant={result.audio.fallback ? "neutral" : "success"}>{result.audio.provider}</Badge>
                  {result.audio.reason && <Badge variant="neutral">{result.audio.reason}</Badge>}
                </div>
              )}
            </RetroCard>

            <RetroCard label="Provider Setup">
              <dl className="grid gap-3 pt-2 text-xs text-text-muted">
                <InfoRow label="HF model" value={status.huggingFace?.model || "Not loaded"} />
                <InfoRow label="HF router" value={status.huggingFace?.routerUrl || "Not loaded"} />
                <InfoRow label="Voice ID" value={status.elevenLabs?.voiceId || "Not loaded"} />
                <InfoRow label="TTS model" value={status.elevenLabs?.modelId || "Not loaded"} />
              </dl>
            </RetroCard>
          </div>
        </RetroWindow>
      </div>
    </main>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-heading text-xs font-semibold uppercase tracking-wide text-text-muted">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border-2 border-border-soft bg-surface px-3 py-2 font-body text-sm text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function TextAreaField({
  label,
  value,
  rows,
  onChange,
}: {
  label: string;
  value: string;
  rows: number;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-heading text-xs font-semibold uppercase tracking-wide text-text-muted">
        {label}
      </span>
      <textarea
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full resize-y rounded-md border-2 border-border-soft bg-surface px-3 py-2 font-body text-sm leading-relaxed text-text shadow-[inset_1px_2px_4px_rgba(74,46,30,0.15)] focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
      />
    </label>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[110px_minmax(0,1fr)]">
      <dt className="font-mono font-semibold uppercase tracking-wide text-text">{label}</dt>
      <dd className="break-all font-mono">{value}</dd>
    </div>
  );
}
