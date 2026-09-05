import Link from "next/link";
import { ArrowUpRight, ScanSearch } from "lucide-react";

export function SiteHeader() {
  return (
    <header className="relative z-10 border-b border-white/[0.07]">
      <div className="aimd-container flex min-h-[76px] items-center justify-between gap-6">
        <Link href="/" className="flex items-center gap-3" aria-label="AIMD dashboard">
          <span className="grid h-9 w-9 place-items-center border border-signal/40 bg-signal/10 text-signal">
            <ScanSearch size={19} strokeWidth={1.8} />
          </span>
          <span>
            <span className="block text-[15px] font-bold tracking-[0.18em]">AIMD</span>
            <span className="block text-[10px] uppercase tracking-[0.12em] text-slate-500">Media forensics</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-7 text-sm text-slate-400 md:flex" aria-label="Primary navigation">
          <Link className="transition hover:text-white" href="/">Dashboard</Link>
          <Link className="transition hover:text-white" href="/investigate">Investigate</Link>
          <Link className="transition hover:text-white" href="/methodology">Methodology</Link>
          <Link className="transition hover:text-white" href="/about">About</Link>
        </nav>
        <Link href="/investigate" className="inline-flex items-center gap-2 border border-signal/40 bg-signal/10 px-3.5 py-2 text-xs font-semibold text-signal transition hover:border-signal hover:bg-signal/15">
          New investigation <ArrowUpRight size={14} />
        </Link>
      </div>
    </header>
  );
}
