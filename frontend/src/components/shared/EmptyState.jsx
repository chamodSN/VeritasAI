// src/components/shared/EmptyState.jsx
import React from 'react';
import { Scale } from 'lucide-react';

const SAMPLE_QUERIES = [
  'Fourth amendment search and seizure automobile exception',
  'Employment discrimination disparate impact Title VII',
  'Contract breach anticipatory repudiation damages',
  'First amendment compelled speech commercial context',
  'Patent obviousness secondary considerations',
  'Criminal procedure Brady material disclosure',
];

export default function EmptyState({ onSampleQuery }) {
  return (
    <div className="text-center py-8">
      <Scale size={32} className="text-stone-dark mx-auto mb-4" strokeWidth={1.2} />
      <h2 className="font-serif text-xl text-ink mb-1">Start your research</h2>
      <p className="text-sm text-mist mb-8 max-w-sm mx-auto leading-relaxed">
        Enter a legal question above. VeritasAI will fetch live case law, extract issues,
        build arguments, and verify every citation.
      </p>

      <p className="text-xs font-semibold text-mist uppercase tracking-wide mb-3">Try an example</p>
      <div className="flex flex-wrap gap-2 justify-center max-w-xl mx-auto">
        {SAMPLE_QUERIES.map(q => (
          <button
            key={q}
            onClick={() => onSampleQuery(q)}
            className="text-xs px-3 py-1.5 bg-white border border-stone rounded-full
                       text-mist hover:text-ink hover:border-sage hover:bg-sage-light
                       transition-colors duration-150"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}