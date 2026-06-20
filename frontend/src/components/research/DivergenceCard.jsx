
import React, { useState } from 'react';
import { GitBranch, ChevronDown, ChevronUp } from 'lucide-react';

export default function DivergenceCard({ divergence }) {
  const [expanded, setExpanded] = useState(false);
  if (!divergence) return null;

  return (
    <div className="card mb-3 border-l-2 border-amber">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <GitBranch size={13} className="text-amber flex-shrink-0 mt-0.5" />
          <p className="text-xs font-medium text-ink leading-snug">{divergence.question}</p>
        </div>
        <button onClick={() => setExpanded(v => !v)} className="btn-ghost p-0.5">
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </button>
      </div>

      <div className="flex gap-2 mt-2 flex-wrap">
        <span className="badge-review capitalize">{divergence.split_type?.replace('_', ' ')}</span>
        {divergence.scotus_resolved && (
          <span className="badge-valid text-[10px]">SCOTUS resolved</span>
        )}
      </div>

      {expanded && (
        <div className="mt-3 space-y-2">
          {divergence.positions?.map((pos, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="font-mono text-mist w-24 flex-shrink-0">{pos.court}</span>
              <span className="text-ink leading-relaxed">{pos.ruling}</span>
            </div>
          ))}
          {divergence.strategic_implication && (
            <p className="text-xs text-mist mt-2 pt-2 border-t border-stone leading-relaxed">
              {divergence.strategic_implication}
            </p>
          )}
        </div>
      )}
    </div>
  );
}