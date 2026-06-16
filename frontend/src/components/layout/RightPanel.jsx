// src/components/layout/RightPanel.jsx
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Gavel, GitBranch, TrendingUp } from 'lucide-react';
import JudgeCard from '../research/JudgeCard';
import DivergenceCard from '../research/DivergenceCard';
import OutcomeCard from '../research/OutcomeCard';

export default function RightPanel({ result, onClose }) {
  const hasJudges = result?.judge_profiles?.length > 0;
  const hasDivergence = result?.divergences?.length > 0;
  const hasOutcome = !!result?.outcome_prediction;
  const hasContent = hasJudges || hasDivergence || hasOutcome;

  return (
    <AnimatePresence>
      {hasContent && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
          className="flex-shrink-0 bg-white border-l border-stone overflow-hidden"
        >
          <div className="w-right-panel flex flex-col h-full">
            <div className="p-4 border-b border-stone flex items-center justify-between">
              <span className="text-sm font-medium text-ink">Intelligence</span>
              <button onClick={onClose} className="btn-ghost p-1">
                <X size={14} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {hasJudges && (
                <section>
                  <div className="flex items-center gap-2 mb-3">
                    <Gavel size={13} className="text-sage" />
                    <h3 className="text-xs font-semibold text-mist uppercase tracking-wide">Judge Profiles</h3>
                  </div>
                  {result.judge_profiles.map((p, i) => (
                    <JudgeCard key={i} profile={p} />
                  ))}
                </section>
              )}

              {hasDivergence && (
                <section>
                  <div className="flex items-center gap-2 mb-3">
                    <GitBranch size={13} className="text-amber" />
                    <h3 className="text-xs font-semibold text-mist uppercase tracking-wide">Circuit Splits</h3>
                  </div>
                  {result.divergences.map((d, i) => (
                    <DivergenceCard key={i} divergence={d} />
                  ))}
                </section>
              )}

              {hasOutcome && (
                <section>
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp size={13} className="text-sage" />
                    <h3 className="text-xs font-semibold text-mist uppercase tracking-wide">Outcome Analysis</h3>
                  </div>
                  <OutcomeCard prediction={result.outcome_prediction} />
                </section>
              )}
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}