import Link from "next/link";
import { ArrowRight, Binary, Fingerprint, Layers3, ScanLine, ShieldCheck, Waves } from "lucide-react";
import { Pipeline } from "@/components/pipeline";
import { SiteHeader } from "@/components/site-header";

const capabilities = [
  { icon: ScanLine, title: "AI detection", copy: "Open-weight vision inference with an explicit model identity and uncertainty." },
  { icon: Layers3, title: "Metadata forensics", copy: "Inspect dimensions, format, EXIF availability, and artifact context." },
  { icon: Waves, title: "Signal analysis", copy: "Frequency, compression, and noise measurements stay visible as evidence." },
  { icon: Fingerprint, title: "Digital fingerprinting", copy: "Exact SHA-256 and perceptual hashes help identify the artifact." },
];

export default function Dashboard() {
  return (
    <main className="aimd-shell relative overflow-hidden">
      <div className="aimd-grid pointer-events-none absolute inset-0" />
      <SiteHeader />
      <div className="aimd-container relative pb-24 pt-20 sm:pt-28">
        <section className="grid items-end gap-12 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="animate-rise">
            <div className="eyebrow mb-6">AIMD / AI media detection & digital forensics</div>
            <h1 className="max-w-4xl text-5xl font-semibold leading-[0.98] tracking-[-0.045em] text-white sm:text-7xl">Find the evidence behind every image.</h1>
            <p className="mt-7 max-w-2xl text-lg leading-8 text-slate-400">Analyze digital media using machine learning and forensic signals to identify potential AI-generated or AI-altered content.</p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link href="/investigate" className="inline-flex items-center gap-3 bg-signal px-5 py-3 text-sm font-bold text-ink transition hover:bg-[#7ce4d9]">Start investigation <ArrowRight size={17} /></Link>
              <Link href="/methodology" className="inline-flex items-center gap-2 border border-line px-5 py-3 text-sm font-semibold text-slate-300 transition hover:border-slate-500 hover:text-white">How it works</Link>
            </div>
            <p className="mt-5 flex items-center gap-2 text-xs text-slate-500"><ShieldCheck size={14} className="text-signal" /> AI detection is probabilistic. AIMD reports evidence, not absolute truth.</p>
          </div>
          <div className="panel animate-rise-delay p-6 sm:p-8">
            <div className="flex items-start justify-between border-b border-line pb-5">
              <div><div className="eyebrow">Investigation model</div><h2 className="mt-2 text-2xl font-semibold text-white">Multi-signal by design.</h2></div>
              <Binary className="text-signal" size={25} strokeWidth={1.5} />
            </div>
            <p className="mt-5 text-sm leading-7 text-slate-400">AIMD makes the pipeline inspectable: every signal keeps its source, status, and technical detail.</p>
            <div className="mt-7"><Pipeline /></div>
          </div>
        </section>

        <section className="mt-24 border-t border-white/[0.08] pt-8">
          <div className="flex flex-wrap items-end justify-between gap-4"><div><div className="eyebrow">What gets examined</div><h2 className="mt-3 text-3xl font-semibold tracking-tight text-white">A forensic brief, not a black box.</h2></div><span className="text-xs text-slate-500">ML + metadata + image signals + ensemble</span></div>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {capabilities.map(({ icon: Icon, title, copy }) => <div className="panel-soft p-5" key={title}><Icon className="text-signal" size={20} strokeWidth={1.7} /><h3 className="mt-8 font-semibold text-white">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-500">{copy}</p></div>)}
          </div>
        </section>

        <section className="mt-16 grid gap-4 border border-amber/20 bg-amber/[0.05] p-5 sm:grid-cols-[auto_1fr] sm:p-6">
          <div className="eyebrow text-amber">Judge note</div><p className="max-w-3xl text-sm leading-7 text-slate-300">Forensic measurements are contextual evidence. The current baseline ensemble is intentionally transparent and its confidence is not a calibrated probability.</p>
        </section>
      </div>
    </main>
  );
}
