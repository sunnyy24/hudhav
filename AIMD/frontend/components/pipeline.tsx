import { ArrowDown, CheckCircle2, CircleDashed } from "lucide-react";

const stages = ["Upload", "Forensic analysis", "ML detection", "Ensemble", "Explainable verdict"];

export function Pipeline() {
  return (
    <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center sm:gap-0">
      {stages.map((stage, index) => (
        <div className="flex flex-1 items-center sm:flex-col sm:items-stretch" key={stage}>
          <div className="flex items-center gap-3 sm:justify-center sm:gap-2">
            {index === 0 ? <CheckCircle2 className="text-signal" size={17} /> : <CircleDashed className="text-slate-500" size={17} />}
            <span className="text-xs font-semibold text-slate-300">{stage}</span>
          </div>
          {index < stages.length - 1 && <ArrowDown className="ml-[5px] mt-1 text-slate-600 sm:hidden" size={14} />}
          {index < stages.length - 1 && <span className="mx-3 hidden h-px flex-1 bg-line sm:block" />}
        </div>
      ))}
    </div>
  );
}
