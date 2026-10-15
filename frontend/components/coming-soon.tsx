"use client";

interface ComingSoonProps {
  title: string;
  description: string;
  prompt: string;
  features: string[];
}

export function ComingSoon({ title, description, prompt, features }: ComingSoonProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="w-14 h-14 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center text-2xl mb-4">
        🚧
      </div>
      <h2 className="text-xl font-bold text-white mb-2">{title}</h2>
      <p className="text-slate-400 text-sm max-w-sm mb-6">{description}</p>
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-xs font-mono text-violet-400 mb-6">
        Coming in {prompt}
      </div>
      <div className="text-left bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5 max-w-sm w-full">
        <p className="text-xs text-slate-500 mb-3 font-medium uppercase tracking-wider">What you'll get</p>
        <ul className="space-y-2">
          {features.map((f) => (
            <li key={f} className="flex items-start gap-2 text-xs text-slate-400">
              <span className="text-violet-400 mt-0.5">→</span>
              {f}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
