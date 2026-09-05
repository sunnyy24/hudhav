"use client";

import { ChangeEvent, DragEvent, type ReactNode, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Activity,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Clipboard,
  Copy,
  Database,
  ExternalLink,
  FileCheck2,
  FileImage,
  Fingerprint,
  Globe2,
  Gauge,
  Link2,
  LoaderCircle,
  LockKeyhole,
  ScanSearch,
  Search,
  ServerCrash,
  UploadCloud,
  Waves,
  X,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const MAX_FILE_SIZE = 25 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];
const MODEL_ARCHITECTURE = "ViTForImageClassification";

type Stage = "idle" | "uploading" | "analyzing" | "complete" | "error";
type StageStatus = "pending" | "active" | "complete";

type Evidence = {
  name: string;
  status: string;
  strength: string;
  summary: string;
  technical_details: Record<string, unknown>;
};

type ProvenanceFinding = {
  type: string;
  status: string;
  confidence: number | null;
  summary: string;
  technical_details: Record<string, unknown>;
};

type ProvenanceResponse = {
  identity: { sha256: string | null; phash: string | null; identity_status: string };
  metadata_origin: Record<string, { status: string; value: unknown }>;
  content_credentials: { status: string; present: boolean; reason?: string; details?: Record<string, unknown> };
  platform_processing: { status: string; platform_processing: string; reasoning: string[]; technical_details: Record<string, unknown> };
  matches: Array<{ media_id: string; match_type: string; match_strength: string; source_url?: string | null; platform?: string | null; first_seen_at?: string | null; distance?: number }>;
  origin: { source_url: string | null; platform: string | null; first_seen_at: string | null; match_type: string; match_strength: string; status: string };
  timeline: Array<{ event: string; date: string | null; status: string; source: string | null }>;
  findings: ProvenanceFinding[];
  external_search: { performed: boolean; status: string; reason: string };
};

type AnalysisResponse = {
  analysis_version: string;
  investigation_id: string;
  file: { name: string; extension: string; size_bytes: number };
  fingerprints: Record<string, unknown>;
  metadata: Record<string, unknown>;
  forensic_features: Record<string, Record<string, unknown>>;
  ml_detection: {
    status: string;
    model?: string;
    prediction?: string;
    confidence?: number | null;
    ai_probability?: number | null;
    human_probability?: number | null;
    raw_scores?: Record<string, number>;
    reason?: string;
  };
  evidence: Evidence[];
  provenance: ProvenanceResponse;
  ensemble: {
    verdict: string;
    confidence: number;
    evidence_strength: string;
    confidence_note: string;
    signals: Evidence[];
    reasoning: string[];
  };
};

type UploadResponse = { file_id: string; original_filename: string; file_type: string };

type OriginMatch = {
  source_url: string | null;
  platform: string | null;
  title: string | null;
  first_seen: string | null;
  match_type: "EXACT" | "PARTIAL" | "PERCEPTUAL" | "UNKNOWN";
  match_strength: "VERIFIED" | "INFERRED" | "UNKNOWN";
  evidence: Record<string, unknown>;
};

type OriginSearchResponse = {
  file_id: string;
  provider: string;
  status: "VERIFIED" | "UNKNOWN" | "ERROR" | "UNAVAILABLE";
  searched_at: string;
  matches: OriginMatch[];
  error: string | null;
  cached?: boolean;
};

const timeline = [
  "File received",
  "File validated",
  "Metadata extracted",
  "Fingerprint generated",
  "Forensic features extracted",
  "ML detection completed",
  "Ensemble assessment completed",
];

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatValue(value: unknown) {
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(6);
  if (value === null || value === undefined) return "Not available";
  return String(value);
}

function evidenceTone(status: string) {
  if (status.toLowerCase() === "available") return "border-signal/20 bg-signal/[0.06] text-signal";
  if (status.toLowerCase() === "unavailable") return "border-alert/20 bg-alert/[0.06] text-alert";
  return "border-amber/20 bg-amber/[0.06] text-amber";
}

function verdictTone(verdict: string) {
  if (verdict === "LIKELY AUTHENTIC") return "text-signal";
  if (verdict === "LIKELY AI-GENERATED" || verdict === "POTENTIALLY AI-ALTERED") return "text-alert";
  return "text-amber";
}

function provenanceTone(status: string) {
  if (status === "VERIFIED") return "border-signal/20 bg-signal/[0.06] text-signal";
  if (status === "INFERRED") return "border-amber/20 bg-amber/[0.06] text-amber";
  return "border-line bg-white/[0.03] text-slate-400";
}

function EvidenceCard({ evidence }: { evidence: Evidence }) {
  const [open, setOpen] = useState(false);
  return (
    <article className="panel-soft overflow-hidden">
      <button className="flex min-w-0 w-full items-start justify-between gap-4 p-5 text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="flex min-w-0 items-start gap-3">
          <span className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center border text-xs ${evidenceTone(evidence.status)}`}>
            {evidence.status.toLowerCase() === "available" ? <Check size={14} /> : <AlertTriangle size={14} />}
          </span>
          <span className="block min-w-0 break-all"><span className="block font-semibold text-white">{evidence.name}</span><span className="mt-1 block text-sm leading-6 text-slate-400">{evidence.summary}</span></span>
        </span>
        <span className="flex max-w-[44%] shrink-0 flex-wrap items-center justify-end gap-2"><span className={`border px-2 py-1 text-right text-[10px] font-bold uppercase tracking-[0.12em] ${evidenceTone(evidence.status)}`}>{evidence.status} / {evidence.strength}</span><ChevronDown className={`shrink-0 text-slate-500 transition ${open ? "rotate-180" : ""}`} size={16} /></span>
      </button>
      {open && <div className="min-w-0 border-t border-line px-5 py-4"><div className="mb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Technical details</div><pre className="block min-w-0 max-w-full overflow-x-auto whitespace-pre-wrap break-words text-xs leading-6 text-slate-400">{JSON.stringify(evidence.technical_details, null, 2)}</pre></div>}
    </article>
  );
}

function ExplorerSection({
  title,
  description,
  status,
  icon,
  children,
}: {
  title: string;
  description: string;
  status?: string;
  icon: ReactNode;
  children: ReactNode;
}) {
  return <details className="panel-soft group min-w-0" open={title === "ML Detection" || title === "Ensemble Reasoning"}>
    <summary className="flex cursor-pointer list-none items-start justify-between gap-4 p-5 [&::-webkit-details-marker]:hidden">
      <span className="flex min-w-0 items-start gap-3"><span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center border border-signal/20 bg-signal/[0.06] text-signal">{icon}</span><span className="block min-w-0"><span className="block font-semibold text-white">{title}</span><span className="mt-1 block text-sm leading-6 text-slate-500">{description}</span></span></span>
      <span className="flex shrink-0 items-center gap-3">{status && <span className={`hidden border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] sm:inline-flex ${provenanceTone(status)}`}>{status}</span>}<ChevronDown className="text-slate-500 transition group-open:rotate-180" size={17} /></span>
    </summary>
    <div className="min-w-0 border-t border-line p-5">{children}</div>
  </details>;
}

function ValueTable({ fields }: { fields: Array<[string, unknown]> }) {
  return <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">{fields.map(([label, value]) => <div key={label}><dt className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-600">{label}</dt><dd className="mt-1 break-words text-sm text-slate-300">{formatValue(value)}</dd></div>)}</dl>;
}

function NumericSignals({ values }: { values: Record<string, unknown> }) {
  const entries = Object.entries(values).filter(([, value]) => typeof value === "number" && Number.isFinite(value));
  if (!entries.length) return <div className="text-sm text-slate-500">No numeric measurements were returned.</div>;
  const maximum = Math.max(...entries.map(([, value]) => Math.abs(value as number)), 1);
  return <div className="space-y-4">{entries.map(([label, value]) => { const numericValue = value as number; const width = Math.min(100, Math.max(4, (Math.abs(numericValue) / maximum) * 100)); return <div key={label}><div className="flex items-center justify-between gap-4 text-xs"><span className="text-slate-400">{label.replaceAll("_", " ")}</span><span className="font-mono text-slate-300">{formatValue(value)}</span></div><div className="mt-2 h-1.5 bg-white/[0.06]"><div className="h-full bg-signal/70" style={{ width: `${width}%` }} /></div></div>; })}<p className="text-[11px] leading-5 text-slate-600">Bars are a relative visual scale of returned measurements, not confidence or anomaly scores.</p></div>;
}

function RawDetails({ value }: { value: unknown }) {
  return <details className="mt-5 min-w-0 border-t border-line pt-4 group"><summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold text-slate-400 [&::-webkit-details-marker]:hidden">Technical details <ChevronDown className="transition group-open:rotate-180" size={15} /></summary><pre className="mt-4 block min-w-0 max-w-full overflow-x-auto whitespace-pre-wrap break-words text-[11px] leading-5 text-slate-500">{JSON.stringify(value, null, 2)}</pre></details>;
}

function OriginDiscoveryPanel({ analysis }: { analysis: AnalysisResponse }) {
  const [searchState, setSearchState] = useState<"idle" | "confirm" | "searching" | "complete">("idle");
  const [result, setResult] = useState<OriginSearchResponse | null>(null);

  function requestSearch() {
    setSearchState("confirm");
  }

  async function continueSearch() {
    setSearchState("searching");
    try {
      const response = await fetch(`${API_BASE_URL}/api/origin/search/${analysis.investigation_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent: true }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        setResult({
          file_id: analysis.investigation_id,
          provider: "google_web_detection",
          status: "ERROR",
          searched_at: new Date().toISOString(),
          matches: [],
          error: data.detail ?? "External origin discovery failed.",
        });
      } else {
        setResult(data as OriginSearchResponse);
      }
    } catch {
      setResult({
        file_id: analysis.investigation_id,
        provider: "google_web_detection",
        status: "ERROR",
        searched_at: new Date().toISOString(),
        matches: [],
        error: "External origin discovery is unavailable.",
      });
    } finally {
      setSearchState("complete");
    }
  }

  function safeSourceUrl(sourceUrl: string | null) {
    if (!sourceUrl) return null;
    try {
      const parsed = new URL(sourceUrl);
      return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.toString() : null;
    } catch {
      return null;
    }
  }

  return <section className="panel border-amber/20 p-5 sm:p-7" aria-labelledby="origin-discovery-heading">
    <div className="flex flex-wrap items-start justify-between gap-5"><div><div className="eyebrow text-amber">External source discovery</div><h3 id="origin-discovery-heading" className="mt-2 text-2xl font-semibold text-white">Trace Online Origin</h3><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Local forensics is complete. This optional action may transmit the image to a third-party search provider and only displays results that provider returns.</p></div><Search className="text-amber" size={24} /></div>
    {searchState === "idle" && <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border border-line bg-black/10 p-4"><span className="text-sm text-slate-400">External search has not been performed.</span><button onClick={requestSearch} className="inline-flex items-center gap-2 border border-amber/30 bg-amber/[0.08] px-4 py-2.5 text-sm font-semibold text-amber hover:bg-amber/[0.14]"><Search size={15} /> Trace Online Origin</button></div>}
    {searchState === "searching" && <div className="mt-6 flex items-center gap-3 border border-amber/20 bg-amber/[0.06] p-4 text-sm text-amber"><LoaderCircle className="animate-spin" size={16} /> Searching public web sources...</div>}
    {result && <div className="mt-6 border border-line bg-black/10 p-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-600">Online Origin Discovery</div><div className="mt-2 text-lg font-semibold text-white">{result.provider}</div></div><span className={`border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${provenanceTone(result.status)}`}>{result.status}</span></div><div className="mt-4 grid gap-3 text-xs text-slate-500 sm:grid-cols-3"><span>Search time<div className="mt-1 text-slate-300">{result.searched_at}</div></span><span>Matches<div className="mt-1 text-slate-300">{result.matches.length}</div></span><span>Cache<div className="mt-1 text-slate-300">{result.cached ? "Returned from recent search" : "Fresh provider response"}</div></span></div>{result.status === "VERIFIED" && result.matches.length > 0 ? <div className="mt-5 space-y-3">{result.matches.map((match, index) => { const sourceUrl = safeSourceUrl(match.source_url); return <div className="border-l border-signal/50 pl-4" key={`${match.source_url ?? "match"}-${index}`}><div className="text-sm font-semibold text-white">{match.title ?? "Untitled source"}</div><div className="mt-2 flex flex-wrap gap-2 text-[10px] font-bold uppercase tracking-[0.1em] text-slate-500"><span>{match.match_type}</span><span>/</span><span>{match.match_strength}</span>{match.platform && <><span>/</span><span>{match.platform}</span></>}</div>{sourceUrl && <a href={sourceUrl} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-2 break-all text-xs text-signal hover:text-white">{sourceUrl}<ExternalLink size={13} /></a>}<details className="mt-3"><summary className="cursor-pointer text-xs text-slate-500">Evidence</summary><pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-[11px] leading-5 text-slate-500">{JSON.stringify(match.evidence, null, 2)}</pre></details></div>; })}</div> : <div className="mt-5 border-l-2 border-amber/50 bg-amber/[0.05] px-4 py-3 text-sm leading-6 text-slate-300">{result.status === "UNKNOWN" ? "No verified public source was discovered by this provider. This does not prove that the image has never appeared online." : result.status === "UNAVAILABLE" ? "External origin discovery is currently unavailable. Local forensic analysis remains fully available." : result.error ?? "External origin discovery failed safely."}</div>}</div>}
    {searchState === "confirm" && <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-5" role="dialog" aria-modal="true" aria-labelledby="origin-consent-title"><div className="panel max-w-lg p-6 shadow-halo"><div className="eyebrow text-amber">Permission required</div><h4 id="origin-consent-title" className="mt-3 text-2xl font-semibold text-white">Trace Online Origin</h4><p className="mt-4 text-sm leading-7 text-slate-400">External source discovery may transmit this image to a third-party search provider. AIMD will only display results returned by that provider.</p><div className="mt-6 flex justify-end gap-3"><button onClick={() => setSearchState("idle")} className="border border-line px-4 py-2.5 text-sm font-semibold text-slate-300 hover:border-slate-500 hover:text-white">Cancel</button><button onClick={continueSearch} className="bg-amber px-4 py-2.5 text-sm font-bold text-ink hover:bg-[#ffd183]">Continue</button></div></div></div>}
  </section>;
}

function EvidenceExplorer({ analysis }: { analysis: AnalysisResponse }) {
  const [copied, setCopied] = useState<string | null>(null);
  const metadata = analysis.metadata;
  const features = analysis.forensic_features;
  const ml = analysis.ml_detection;
  const provenance = analysis.provenance;
  const mlEvidence = analysis.evidence.find((item) => item.name === "ML Detection");

  async function copyFingerprint(label: string, value: unknown) {
    if (typeof value !== "string" || !value) return;
    await navigator.clipboard.writeText(value);
    setCopied(label);
    window.setTimeout(() => setCopied(null), 1600);
  }

  return <section className="panel p-5 sm:p-7" aria-labelledby="evidence-explorer-heading">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><div className="eyebrow">Evidence explorer</div><h3 id="evidence-explorer-heading" className="mt-2 text-2xl font-semibold text-white">Inspect every signal behind the verdict.</h3><p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">Expand a section to review returned values, status, supporting context, and technical details. AIMD does not turn unavailable evidence into a claim.</p></div><Gauge className="text-signal" size={25} /></div>
    <div className="mt-7 space-y-3">
      <ExplorerSection title="ML Detection" description="The model result and probabilities returned by the detector." status={ml.status === "available" ? "VERIFIED" : "UNKNOWN"} icon={<ScanSearch size={17} />}>
        <div className="grid gap-5 lg:grid-cols-[1fr_1fr]"><ValueTable fields={[["Prediction", ml.prediction ?? "UNKNOWN"], ["Human probability", ml.human_probability == null ? "UNKNOWN" : `${(ml.human_probability * 100).toFixed(2)}%`], ["AI probability", ml.ai_probability == null ? "UNKNOWN" : `${(ml.ai_probability * 100).toFixed(2)}%`], ["Status", ml.status], ["Model", ml.model ?? "UNKNOWN"], ["Architecture", ml.status === "available" ? MODEL_ARCHITECTURE : "UNKNOWN"]]} /><div className="panel-soft min-w-0 p-4"><div className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-600">Raw scores</div><pre className="mt-3 block min-w-0 max-w-full overflow-x-auto whitespace-pre-wrap break-words text-xs leading-6 text-slate-400">{JSON.stringify(ml.raw_scores ?? {}, null, 2)}</pre></div></div><div className="mt-5 border-l-2 border-amber/50 bg-amber/[0.05] px-4 py-3 text-xs leading-6 text-amber">Detector confidence is not a calibrated probability.</div>{ml.reason && <p className="mt-4 text-sm text-slate-500">{ml.reason}</p>}
      </ExplorerSection>

      <ExplorerSection title="Metadata" description="File, camera, capture, software, and location fields from the response." status={metadata.error ? "UNKNOWN" : "VERIFIED"} icon={<Database size={17} />}>
        <div className="grid gap-6 lg:grid-cols-2"><div><div className="eyebrow mb-4">File</div><ValueTable fields={[["Filename", metadata.filename], ["Extension", metadata.extension], ["Format", metadata.format], ["Dimensions", metadata.width && metadata.height ? `${metadata.width} × ${metadata.height}` : "UNKNOWN"], ["Size", metadata.file_size_bytes ? formatBytes(Number(metadata.file_size_bytes)) : "UNKNOWN"], ["Mode", metadata.mode]]} /></div><div><div className="eyebrow mb-4">Camera / capture / software / location</div><ValueTable fields={[["Camera", provenance.metadata_origin.capture_device?.value ?? "UNKNOWN"], ["Camera make", provenance.metadata_origin.camera_make?.value ?? "UNKNOWN"], ["Camera model", provenance.metadata_origin.camera_model?.value ?? "UNKNOWN"], ["Capture timestamp", provenance.metadata_origin.capture_timestamp?.value ?? "UNKNOWN"], ["Editing software", provenance.metadata_origin.editing_software?.value ?? "UNKNOWN"], ["GPS availability", provenance.metadata_origin.gps_availability?.value ?? "UNKNOWN"]]} /></div></div><RawDetails value={{ metadata, metadata_origin: provenance.metadata_origin }} />
      </ExplorerSection>

      <ExplorerSection title="Frequency Analysis" description="Frequency-domain measurements that describe low- and high-frequency image content." status={features.frequency?.status ? String(features.frequency.status).toUpperCase() : "VERIFIED"} icon={<Waves size={17} />}>
        <NumericSignals values={features.frequency ?? {}} /><RawDetails value={features.frequency ?? {}} />
      </ExplorerSection>

      <ExplorerSection title="Compression Analysis" description="JPEG block-boundary and image-dimension evidence returned by the compression detector." status={features.compression?.status ? String(features.compression.status).toUpperCase() : "VERIFIED"} icon={<Activity size={17} />}>
        <div className="grid gap-6 lg:grid-cols-2"><div><div className="eyebrow mb-4">Returned measurements</div><NumericSignals values={features.compression ?? {}} /></div><div><div className="eyebrow mb-4">Format context</div><ValueTable fields={[["Format", metadata.format], ["Dimensions", metadata.width && metadata.height ? `${metadata.width} × ${metadata.height}` : "UNKNOWN"], ["JPEG quantization", "UNKNOWN - not returned by API"], ["Re-encoding indicator", provenance.platform_processing.platform_processing]]} /></div></div><RawDetails value={features.compression ?? {}} />
      </ExplorerSection>

      <ExplorerSection title="Noise Analysis" description="Residual and edge-density measurements that can provide supporting context, not proof of AI generation." status={features.noise?.status ? String(features.noise.status).toUpperCase() : "VERIFIED"} icon={<Waves size={17} />}>
        <NumericSignals values={features.noise ?? {}} /><RawDetails value={features.noise ?? {}} />
      </ExplorerSection>

      <ExplorerSection title="Digital Fingerprint" description="Exact file identity and perceptual similarity identifiers." status={provenance.identity.identity_status} icon={<Fingerprint size={17} />}>
        <div className="space-y-4"><div className="panel-soft p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-600">SHA-256</div><div className="mt-2 break-all font-mono text-xs leading-6 text-slate-300">{provenance.identity.sha256 ?? "UNKNOWN"}</div></div><button onClick={() => copyFingerprint("SHA-256", provenance.identity.sha256)} disabled={!provenance.identity.sha256} className="inline-flex shrink-0 items-center gap-2 border border-line px-3 py-2 text-xs font-semibold text-slate-300 hover:border-signal hover:text-signal disabled:opacity-40"><Copy size={13} />{copied === "SHA-256" ? "Copied" : "Copy SHA-256"}</button></div></div><div className="panel-soft p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-600">pHash</div><div className="mt-2 font-mono text-xs text-slate-300">{provenance.identity.phash ?? "UNKNOWN"}</div></div><button onClick={() => copyFingerprint("pHash", provenance.identity.phash)} disabled={!provenance.identity.phash} className="inline-flex shrink-0 items-center gap-2 border border-line px-3 py-2 text-xs font-semibold text-slate-300 hover:border-signal hover:text-signal disabled:opacity-40"><Copy size={13} />{copied === "pHash" ? "Copied" : "Copy pHash"}</button></div></div></div><RawDetails value={provenance.identity} />
      </ExplorerSection>

      <ExplorerSection title="Provenance" description="Identity, origin, local matches, timeline, and platform-processing evidence." status={provenance.origin.status} icon={<Globe2 size={17} />}>
        <div className="grid gap-5 lg:grid-cols-2"><ValueTable fields={[["Origin status", provenance.origin.status], ["Match type", provenance.origin.match_type], ["Match strength", provenance.origin.match_strength], ["Source URL", provenance.origin.source_url ?? "UNKNOWN"], ["Platform", provenance.origin.platform ?? "UNKNOWN"], ["Local matches", provenance.matches.length]]} /><div><div className="eyebrow mb-4">Timeline</div>{provenance.timeline.length ? <div className="space-y-3">{provenance.timeline.map((event) => <div className="flex gap-3" key={`${event.event}-${event.date}`}><Clock3 className="mt-0.5 shrink-0 text-signal" size={15} /><div className="text-sm text-slate-300">{event.event}<div className="mt-1 text-xs text-slate-500">{event.date ?? "UNKNOWN"} / {event.source ?? "UNKNOWN"}</div></div></div>)}</div> : <div className="text-sm text-slate-500">UNKNOWN</div>}</div></div><RawDetails value={{ origin: provenance.origin, matches: provenance.matches, timeline: provenance.timeline, platform_processing: provenance.platform_processing }} />
      </ExplorerSection>

      <ExplorerSection title="Content Credentials" description="C2PA / Content Credentials inspection state." status={provenance.content_credentials.status} icon={<LockKeyhole size={17} />}>
        <ValueTable fields={[["Parser status", provenance.content_credentials.status], ["Credentials present", provenance.content_credentials.present ? "PRESENT" : "UNKNOWN"], ["Reason", provenance.content_credentials.reason ?? "UNKNOWN"]]} /><p className="mt-5 border-l-2 border-amber/50 bg-amber/[0.05] px-4 py-3 text-xs leading-6 text-amber">Inspection unavailable is different from proving that credentials do not exist. Absence of Content Credentials is not proof of AI generation.</p><RawDetails value={provenance.content_credentials} />
      </ExplorerSection>

      <ExplorerSection title="Ensemble Reasoning" description="The signals and reasoning returned by the baseline ensemble." status={analysis.ensemble.evidence_strength} icon={<Gauge size={17} />}>
        <div className="grid gap-5 lg:grid-cols-[1fr_0.9fr]"><div><div className="eyebrow mb-4">Why did AIMD reach this assessment?</div><ul className="space-y-3">{analysis.ensemble.reasoning.map((reason) => <li className="flex gap-3 text-sm leading-6 text-slate-300" key={reason}><CheckCircle2 className="mt-1 shrink-0 text-signal" size={15} />{reason}</li>)}</ul></div><div className="panel-soft p-4"><div className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-600">Signal aggregation details</div><div className="mt-3 space-y-3">{analysis.ensemble.signals.map((signal) => <div className="flex items-start justify-between gap-3 text-xs" key={signal.name}><span className="text-slate-400">{signal.name}</span><span className={`border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.1em] ${evidenceTone(signal.status)}`}>{signal.status} / {signal.strength}</span></div>)}</div></div></div><div className="mt-5 border-l-2 border-amber/50 bg-amber/[0.05] px-4 py-3 text-xs leading-6 text-amber">{analysis.ensemble.confidence_note}</div><RawDetails value={analysis.ensemble} />
      </ExplorerSection>
    </div>
  </section>;
}

function ProvenancePanel({ provenance }: { provenance: ProvenanceResponse }) {
  const originLabels = Object.entries(provenance.metadata_origin).filter(([, field]) => field.status === "VERIFIED");
  return <section className="panel p-5 sm:p-7">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><div className="eyebrow">Origin & provenance trace</div><h3 className="mt-2 text-2xl font-semibold text-white">Provenance & origin</h3><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">AIMD separates verified identity from forensic inference. No external platform search is implied by local artifact analysis.</p></div><Globe2 className="text-signal" size={24} /></div>
    <div className="mt-7 grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
      <div className="panel-soft p-5"><div className="flex items-center justify-between gap-3"><div><div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Media identity</div><div className="mt-1 text-sm font-semibold text-white">Exact and perceptual fingerprints</div></div><span className={`border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${provenanceTone(provenance.identity.identity_status)}`}>{provenance.identity.identity_status}</span></div><dl className="mt-5 space-y-4 text-xs"><div><dt className="mb-1 text-slate-500">SHA-256</dt><dd className="break-all font-mono leading-5 text-slate-300">{provenance.identity.sha256 ?? "Not available"}</dd></div><div><dt className="mb-1 text-slate-500">pHash</dt><dd className="font-mono text-slate-300">{provenance.identity.phash ?? "Not available"}</dd></div></dl></div>
      <div className="panel-soft p-5"><div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Origin status</div><div className={`mt-3 inline-flex border px-2 py-1 text-xs font-bold uppercase tracking-[0.12em] ${provenanceTone(provenance.origin.status)}`}>{provenance.origin.status}</div><p className="mt-4 text-sm leading-6 text-slate-400">{provenance.origin.match_type === "NONE" ? "No verified origin or prior local match found." : `${provenance.origin.match_type} match recorded locally.`}</p></div>
    </div>
    <div className="mt-3 grid gap-3 md:grid-cols-3">
      <div className="panel-soft p-5"><div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Content Credentials</div><div className={`mt-3 inline-flex border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${provenanceTone(provenance.content_credentials.status)}`}>{provenance.content_credentials.present ? "PRESENT" : provenance.content_credentials.status}</div><p className="mt-3 text-xs leading-5 text-slate-500">{provenance.content_credentials.present ? "Credentials were detected." : provenance.content_credentials.reason}</p></div>
      <div className="panel-soft p-5"><div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Platform processing</div><div className={`mt-3 inline-flex border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] ${provenanceTone(provenance.platform_processing.status)}`}>{provenance.platform_processing.platform_processing}</div><p className="mt-3 text-xs leading-5 text-slate-500">{provenance.platform_processing.reasoning[0]}</p></div>
      <div className="panel-soft p-5"><div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Metadata origin</div><div className="mt-3 text-sm font-semibold text-white">{originLabels.length ? `${originLabels.length} verified fields` : "No verified fields"}</div><p className="mt-3 text-xs leading-5 text-slate-500">Missing metadata is not evidence of AI generation.</p></div>
    </div>
    <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1fr]">
      <div className="panel-soft p-5"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500"><Link2 size={14} /> Known local matches</div>{provenance.matches.length ? <div className="mt-4 space-y-3">{provenance.matches.map((match) => <div className="border-l border-signal/40 pl-3" key={`${match.media_id}-${match.match_type}`}><div className="text-sm font-semibold text-white">{match.match_type} / {match.match_strength}</div><div className="mt-1 font-mono text-xs text-slate-500">{match.media_id}</div>{match.distance !== undefined && <div className="mt-1 text-xs text-slate-500">pHash distance: {match.distance}</div>}</div>)}</div> : <p className="mt-4 text-sm leading-6 text-slate-500">No prior local exact or perceptual matches were found.</p>}</div>
      <div className="panel-soft p-5"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500"><Clock3 size={14} /> Origin timeline</div><div className="mt-4 space-y-3">{provenance.timeline.map((event) => <div className="flex gap-3" key={`${event.event}-${event.date}`}><span className={`mt-1 h-2 w-2 shrink-0 rounded-full ${event.status === "VERIFIED" ? "bg-signal" : "bg-slate-600"}`} /><div><div className="text-sm text-slate-300">{event.event}</div><div className="mt-1 text-xs text-slate-500">{event.date ?? "Date unknown"} / {event.source ?? "Source unknown"}</div></div></div>)}</div></div>
    </div>
    <div className="mt-3 border border-line bg-black/10 p-5"><div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 shrink-0 text-amber" size={16} /><div><div className="text-sm font-semibold text-white">Social media trace</div><p className="mt-2 text-sm leading-6 text-slate-400">{provenance.external_search.reason} AIMD currently analyzes available media evidence locally. External platform discovery requires a verified source/search integration.</p></div></div></div>
    <details className="panel-soft group mt-3"><summary className="flex cursor-pointer list-none items-center justify-between p-4 text-sm font-semibold text-slate-200">Provenance findings <ChevronDown className="transition group-open:rotate-180" size={16} /></summary><div className="space-y-3 border-t border-line p-4">{provenance.findings.map((item) => <EvidenceCard key={item.type} evidence={{ name: item.type, status: item.status, strength: item.confidence === null ? "unknown" : "computed", summary: item.summary, technical_details: item.technical_details }} />)}</div></details>
    <p className="mt-5 text-xs leading-6 text-slate-500">AIMD separates verified provenance from forensic inference. Missing metadata, missing Content Credentials, or platform-like compression alone do not establish that media is AI-generated.</p>
  </section>;
}

export function InvestigationWorkspace() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);

  useEffect(() => {
    return () => { if (previewUrl) URL.revokeObjectURL(previewUrl); };
  }, [previewUrl]);

  function selectFile(file: File) {
    const extension = `.${file.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError("Please choose a JPG, JPEG, PNG, or WEBP image.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setError("This file is larger than the 25 MB upload limit.");
      return;
    }
    setError(null);
    setAnalysis(null);
    setStage("idle");
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  }

  function onInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) selectFile(file);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) selectFile(file);
  }

  async function startAnalysis() {
    if (!selectedFile) return;
    setError(null);
    setStage("uploading");
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      const uploadResponse = await fetch(`${API_BASE_URL}/api/upload`, { method: "POST", body: formData });
      const uploadData = await uploadResponse.json().catch(() => ({}));
      if (!uploadResponse.ok) throw new Error(uploadData.detail ?? "Unable to upload this file.");

      const upload = uploadData as UploadResponse;
      setStage("analyzing");
      const analysisResponse = await fetch(`${API_BASE_URL}/api/analyze/${upload.file_id}`);
      const analysisData = await analysisResponse.json().catch(() => ({}));
      if (!analysisResponse.ok) throw new Error(analysisData.detail ?? "Unable to analyze this file.");
      setAnalysis(analysisData.analysis as AnalysisResponse);
      setStage("complete");
    } catch (caughtError) {
      setStage("error");
      setError(caughtError instanceof Error ? caughtError.message : "The analysis service is unavailable.");
    }
  }

  function reset() {
    setSelectedFile(null);
    setAnalysis(null);
    setError(null);
    setStage("idle");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function copyInvestigationId() {
    if (analysis) await navigator.clipboard.writeText(analysis.investigation_id);
  }

  const completedCount = stage === "complete" ? timeline.length : stage === "analyzing" ? 4 : stage === "uploading" ? 2 : 0;
  const currentStage = stage === "uploading" ? "Uploading securely..." : stage === "analyzing" ? "Running forensic analysis and ML inference..." : stage === "complete" ? "Assessment complete" : "Ready for an image";

  return (
    <main className="aimd-shell min-h-screen overflow-x-hidden">
      <SiteHeader />
      <div className="aimd-container pb-24 pt-12 sm:pt-16">
        <div className="animate-rise flex flex-wrap items-end justify-between gap-5"><div><div className="eyebrow">Investigation workspace</div><h1 className="mt-3 text-4xl font-semibold tracking-[-0.035em] text-white sm:text-5xl">Upload media for forensic analysis.</h1><p className="mt-4 max-w-2xl text-base leading-7 text-slate-400">AIMD correlates machine learning with image-level forensic signals. The backend is the security boundary and the source of truth.</p></div><div className="flex items-center gap-2 text-xs text-slate-500"><LockKeyhole size={14} className="text-signal" /> Files stay local to your AIMD environment</div></div>

        <section className="mt-10 grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="panel p-5 sm:p-7">
            <div className="flex items-center justify-between"><div><div className="eyebrow">01 / Artifact intake</div><h2 className="mt-2 text-xl font-semibold text-white">Choose an image</h2></div><UploadCloud className="text-signal" size={23} /></div>
            <div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop} className={`mt-7 grid min-h-[275px] place-items-center border border-dashed p-6 text-center transition ${dragging ? "border-signal bg-signal/[0.08]" : "border-slate-600/70 bg-black/10 hover:border-slate-400"}`}>
              {selectedFile ? <div className="w-full"><div className="mx-auto grid h-16 w-16 place-items-center border border-signal/30 bg-signal/10 text-signal"><FileImage size={28} /></div><h3 className="mt-5 truncate font-semibold text-white">{selectedFile.name}</h3><p className="mt-2 text-sm text-slate-500">{formatBytes(selectedFile.size)} / {selectedFile.type || "image"}</p><button onClick={reset} className="mt-5 inline-flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white"><X size={14} /> Remove file</button></div> : <div><div className="mx-auto grid h-16 w-16 place-items-center border border-line bg-panel-soft text-signal"><UploadCloud size={28} /></div><h3 className="mt-5 text-lg font-semibold text-white">Drop an image here</h3><p className="mx-auto mt-2 max-w-xs text-sm leading-6 text-slate-500">JPG, JPEG, PNG, or WEBP. Maximum file size: 25 MB.</p><button onClick={() => inputRef.current?.click()} className="mt-6 border border-line px-4 py-2.5 text-sm font-semibold text-slate-200 transition hover:border-signal hover:text-signal">Choose file</button></div>}
            </div>
            <input ref={inputRef} className="hidden" type="file" accept=".jpg,.jpeg,.png,.webp" onChange={onInputChange} />
            {selectedFile && <button onClick={startAnalysis} disabled={stage === "uploading" || stage === "analyzing"} className="mt-4 flex w-full items-center justify-center gap-2 bg-signal px-4 py-3 text-sm font-bold text-ink transition hover:bg-[#7ce4d9] disabled:opacity-50">{stage === "uploading" || stage === "analyzing" ? <LoaderCircle className="animate-spin" size={16} /> : <ScanSearch size={16} />} {stage === "uploading" ? "Uploading..." : stage === "analyzing" ? "Analyzing..." : "Analyze media"}</button>}
            {error && <div role="alert" className="mt-4 flex gap-2 border border-alert/25 bg-alert/[0.07] p-3 text-sm leading-6 text-red-100"><ServerCrash className="mt-1 shrink-0 text-alert" size={16} /> <span>{error}</span></div>}
          </div>

          <div className="panel p-5 sm:p-7">
            <div className="flex items-center justify-between"><div><div className="eyebrow">02 / Evidence pipeline</div><h2 className="mt-2 text-xl font-semibold text-white">Investigation status</h2></div><span className="text-xs text-slate-500">{completedCount}/{timeline.length} complete</span></div>
            <div className="mt-7 space-y-0">{timeline.map((item, index) => { const status: StageStatus = index < completedCount ? "complete" : index === completedCount && (stage === "uploading" || stage === "analyzing") ? "active" : "pending"; return <div className="flex gap-4" key={item}><div className="flex flex-col items-center"><span className={`grid h-7 w-7 shrink-0 place-items-center border ${status === "complete" ? "border-signal/40 bg-signal/10 text-signal" : status === "active" ? "border-amber/40 bg-amber/10 text-amber" : "border-line text-slate-600"}`}>{status === "complete" ? <Check size={14} /> : status === "active" ? <LoaderCircle className="animate-spin" size={14} /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}</span>{index < timeline.length - 1 && <span className={`my-1 min-h-7 w-px ${status === "complete" ? "bg-signal/40" : "bg-line"}`} />}</div><div className="pb-6 pt-1"><div className={`text-sm font-semibold ${status === "pending" ? "text-slate-600" : "text-slate-200"}`}>{item}</div>{status === "active" && <div className="mt-1 text-xs text-amber">{currentStage}</div>}</div></div>; })}</div>
            <div className="mt-2 border-t border-line pt-5 text-xs leading-6 text-slate-500">AIMD never turns a missing signal into a positive claim. Unavailable evidence remains visible in the final assessment.</div>
          </div>
        </section>

        {analysis && <AnalysisReport analysis={analysis} previewUrl={previewUrl} onCopy={copyInvestigationId} onReset={reset} />}
      </div>
    </main>
  );
}

function AnalysisReport({ analysis, previewUrl, onCopy, onReset }: { analysis: AnalysisResponse; previewUrl: string | null; onCopy: () => void; onReset: () => void }) {
  const ml = analysis.ml_detection;
  const confidence = Math.round((analysis.ensemble.confidence ?? 0) * 10000) / 100;
  return <section className="animate-rise mt-8 space-y-5" aria-live="polite">
    <div className="panel overflow-hidden">
      <div className="border-b border-line bg-gradient-to-r from-white/[0.04] to-transparent p-5 sm:p-7"><div className="flex flex-wrap items-start justify-between gap-5"><div><div className="eyebrow">Forensic verdict</div><h2 className={`mt-3 text-3xl font-semibold tracking-tight sm:text-4xl ${verdictTone(analysis.ensemble.verdict)}`}>{analysis.ensemble.verdict}</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">The current assessment combines the available ML result with contextual forensic evidence. It is not absolute proof.</p></div><div className="text-left sm:text-right"><div className="text-4xl font-semibold text-white">{confidence.toFixed(2)}%</div><div className="mt-1 text-xs text-slate-500">Baseline ensemble confidence</div><div className="mt-3 inline-flex border border-amber/25 bg-amber/[0.06] px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-amber">{analysis.ensemble.evidence_strength} evidence</div></div></div></div>
      <div className="grid gap-4 p-5 sm:grid-cols-[1fr_auto] sm:p-7"><div className="flex flex-wrap gap-x-8 gap-y-3 text-sm text-slate-400"><span><span className="block text-[10px] uppercase tracking-[0.14em] text-slate-600">Investigation ID</span><span className="mt-1 block font-mono text-xs text-slate-300">{analysis.investigation_id}</span></span><span><span className="block text-[10px] uppercase tracking-[0.14em] text-slate-600">File</span><span className="mt-1 block text-slate-300">{analysis.file.name}</span></span><span><span className="block text-[10px] uppercase tracking-[0.14em] text-slate-600">Status</span><span className="mt-1 block text-signal">Analysis complete</span></span></div><div className="flex gap-2"><button onClick={onCopy} className="inline-flex items-center gap-2 border border-line px-3 py-2 text-xs font-semibold text-slate-300 hover:border-slate-500 hover:text-white"><Clipboard size={14} /> Copy ID</button><button disabled title="Report generation is not implemented yet" className="inline-flex items-center gap-2 border border-line px-3 py-2 text-xs font-semibold text-slate-600"><FileCheck2 size={14} /> Report unavailable</button><button onClick={onReset} className="border border-signal/30 bg-signal/10 px-3 py-2 text-xs font-semibold text-signal hover:bg-signal/15">New investigation</button></div></div>
    </div>

    <EvidenceExplorer analysis={analysis} />

    <OriginDiscoveryPanel analysis={analysis} />

    <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
      <div className="panel p-5 sm:p-7"><div className="eyebrow">Machine learning signal</div><h3 className="mt-2 text-xl font-semibold text-white">Detection model</h3>{previewUrl && <img src={previewUrl} alt="Uploaded investigation artifact" className="mt-6 aspect-[3/2] w-full object-cover opacity-90" />}<div className="mt-6 grid grid-cols-2 gap-3"><div className="panel-soft p-4"><div className="text-[10px] uppercase tracking-[0.13em] text-slate-500">AI probability</div><div className="mt-2 text-2xl font-semibold text-white">{ml.ai_probability == null ? "N/A" : `${(ml.ai_probability * 100).toFixed(2)}%`}</div></div><div className="panel-soft p-4"><div className="text-[10px] uppercase tracking-[0.13em] text-slate-500">Human probability</div><div className="mt-2 text-2xl font-semibold text-signal">{ml.human_probability == null ? "N/A" : `${(ml.human_probability * 100).toFixed(2)}%`}</div></div></div><dl className="mt-6 space-y-3 border-t border-line pt-5 text-sm"><div className="flex justify-between gap-4"><dt className="text-slate-500">Prediction</dt><dd className="font-semibold text-white">{ml.prediction ?? "Inconclusive"}</dd></div><div className="flex justify-between gap-4"><dt className="text-slate-500">Status</dt><dd className={ml.status === "available" ? "text-signal" : "text-alert"}>{ml.status}</dd></div><div className="flex justify-between gap-4"><dt className="text-slate-500">Model</dt><dd className="max-w-[65%] text-right text-xs text-slate-300">{ml.model ?? "Not available"}</dd></div><div className="flex justify-between gap-4"><dt className="text-slate-500">Architecture</dt><dd className="text-slate-300">{ml.status === "available" ? MODEL_ARCHITECTURE : "Not available"}</dd></div></dl>{ml.status !== "available" && <div className="mt-5 border border-alert/20 bg-alert/[0.05] p-3 text-xs leading-5 text-red-100">The ML detector is unavailable. Available forensic evidence is still shown.</div>}</div>
      <div className="panel p-5 sm:p-7"><div className="flex items-end justify-between gap-4"><div><div className="eyebrow">Signal review</div><h3 className="mt-2 text-xl font-semibold text-white">Forensic evidence</h3></div><Fingerprint className="text-signal" size={22} /></div><div className="mt-6 space-y-3">{analysis.evidence.filter((item) => item.name !== "ML Detection").map((item) => <EvidenceCard key={item.name} evidence={item} />)}</div></div>
    </div>

    {analysis.provenance && <ProvenancePanel provenance={analysis.provenance} />}

    <div className="grid gap-5 lg:grid-cols-[1fr_0.85fr]">
      <div className="panel p-5 sm:p-7"><div className="eyebrow">Assessment rationale</div><h3 className="mt-2 text-xl font-semibold text-white">Why AIMD reached this assessment</h3><ul className="mt-6 space-y-4">{analysis.ensemble.reasoning.map((reason) => <li className="flex gap-3 text-sm leading-6 text-slate-300" key={reason}><CheckCircle2 className="mt-1 shrink-0 text-signal" size={16} />{reason}</li>)}</ul><div className="mt-7 border-l-2 border-amber/50 bg-amber/[0.05] px-4 py-3 text-xs leading-6 text-amber">{analysis.ensemble.confidence_note}</div></div>
      <div className="panel min-w-0 p-5 sm:p-7"><div className="eyebrow">Artifact identity</div><h3 className="mt-2 text-xl font-semibold text-white">Technical details</h3><div className="mt-6 space-y-3"><EvidenceCard evidence={analysis.evidence.find((item) => item.name === "ML Detection") ?? { name: "ML Detection", status: "unavailable", strength: "insufficient", summary: "No ML evidence returned.", technical_details: {} }} /><details className="panel-soft group"><summary className="flex cursor-pointer list-none items-center justify-between p-4 text-sm font-semibold text-slate-200">Raw forensic response <ChevronDown className="transition group-open:rotate-180" size={16} /></summary><pre className="block min-w-0 max-w-full overflow-x-auto whitespace-pre-wrap break-words border-t border-line p-4 text-[11px] leading-5 text-slate-500">{JSON.stringify({ metadata: analysis.metadata, forensic_features: analysis.forensic_features, fingerprints: analysis.fingerprints }, null, 2)}</pre></details></div></div>
    </div>
  </section>;
}
