
import React from 'react';
import { TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';

const LIKELIHOOD_CONFIG = {
  high:              { icon: TrendingUp,   cls: 'text-sage',   label: 'Favourable',    bg: 'bg-sage-light' },
  medium:            { icon: Minus,        cls: 'text-amber',  label: 'Mixed signals', bg: 'bg-amber-light' },
  low:               { icon: TrendingDown, cls: 'text-danger', label: 'Challenging',   bg: 'bg-danger-light' },
  insufficient_data: { icon: AlertTriangle,cls: 'text-mist',   label: 'Insufficient data', bg: 'bg-stone' },
};

export default function OutcomeCard({ prediction }) {
  if (!prediction) return null;
  const cfg = LIKELIHOOD_CONFIG[prediction.favorable_outcome_likelihood] || LIKELIHOOD_CONFIG.insufficient_data;

  return (
    <div className="card">
      {/* Likelihood indicator */}
      <div className={`flex items-center gap-2 p-3 rounded-btn ${cfg.bg} mb-4`}>
        <cfg.icon size={15} className={cfg.cls} />
        <div>
          <p className="text-xs font-semibold text-ink">{cfg.label}</p>
          <p className="text-[11px] text-mist capitalize">{prediction.confidence} confidence</p>
        </div>
      </div>

      <p className="text-xs text-mist leading-relaxed mb-3">{prediction.confidence_basis}</p>

      {prediction.key_factors?.length > 0 && (
        <FactorList title="Key factors" items={prediction.key_factors} cls="text-sage" />
      )}
      {prediction.risk_factors?.length > 0 && (
        <FactorList title="Risk factors" items={prediction.risk_factors} cls="text-danger" />
      )}

      {prediction.recommended_approach && (
        <div className="mt-3 pt-3 border-t border-stone">
          <p className="text-[11px] font-semibold text-mist mb-1">Recommended approach</p>
          <p className="text-xs text-ink leading-relaxed">{prediction.recommended_approach}</p>
        </div>
      )}

      <p className="text-[10px] text-stone-dark mt-3 pt-3 border-t border-stone leading-relaxed italic">
        {prediction.disclaimer}
      </p>
    </div>
  );
}

function FactorList({ title, items, cls }) {
  return (
    <div className="mb-3">
      <p className="text-[11px] font-semibold text-mist mb-1">{title}</p>
      <ul className="space-y-1">
        {items.map((f, i) => (
          <li key={i} className="flex items-start gap-1.5 text-xs">
            <span className={`${cls} mt-0.5`}>·</span>
            <span className="text-ink leading-snug">{f}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}