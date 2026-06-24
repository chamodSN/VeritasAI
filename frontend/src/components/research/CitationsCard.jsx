
import React from 'react';
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

const STATUS_CONFIG = {
  VALID:        { icon: CheckCircle2, cls: 'text-sage',   badge: 'badge-valid',   label: 'Valid' },
  INVALID:      { icon: XCircle,      cls: 'text-danger', badge: 'badge-invalid', label: 'Invalid' },
  NEEDS_REVIEW: { icon: AlertCircle,  cls: 'text-amber',  badge: 'badge-review',  label: 'Review' },
};

export default function CitationsCard({ data }) {
  if (!data) return null;
  const { total, valid, invalid, needs_review, citations } = data;

  return (
    <div className="space-y-3">
      {/* Summary row */}
      <div className="card flex items-center gap-6">
        <Stat label="Total" value={total} />
        <div className="w-px h-8 bg-stone" />
        <Stat label="Valid" value={valid} valueClass="text-sage" />
        <Stat label="Invalid" value={invalid} valueClass="text-danger" />
        <Stat label="Review" value={needs_review} valueClass="text-amber" />
      </div>

      {/* Individual citations */}
      <div className="space-y-2">
        {citations?.map((c, i) => {
          const cfg = STATUS_CONFIG[c.status] || STATUS_CONFIG.NEEDS_REVIEW;
          return (
            <div key={i} className="card">
              <div className="flex items-start gap-3">
                <cfg.icon size={15} className={`${cfg.cls} flex-shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-sm text-ink">{c.citation}</span>
                    <span className={cfg.badge}>{cfg.label}</span>
                    <span className="badge-neutral capitalize">{c.confidence} confidence</span>
                  </div>
                  {c.issues && c.issues !== 'None' && (
                    <p className="text-xs text-mist mt-1.5 leading-relaxed">
                      <span className="font-medium">Issues:</span> {c.issues}
                    </p>
                  )}
                  {c.recommendations && c.recommendations !== 'None needed.' && (
                    <p className="text-xs text-mist mt-1 leading-relaxed">
                      <span className="font-medium">Fix:</span> {c.recommendations}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Stat({ label, value, valueClass = 'text-ink' }) {
  return (
    <div className="text-center">
      <p className={`font-serif text-2xl font-semibold ${valueClass}`}>{value}</p>
      <p className="text-xs text-mist">{label}</p>
    </div>
  );
}