
import React from 'react';
import { motion } from 'framer-motion';
import {
  Database, Gavel, FileText, MessageSquare,
  GitBranch, CheckCircle2, BarChart2, Shield
} from 'lucide-react';

const STAGES = [
  { id: 'fetching',    label: 'Fetching cases',    icon: Database },
  { id: 'judging',     label: 'Judge profiles',    icon: Gavel },
  { id: 'summarising', label: 'Summarising',       icon: FileText },
  { id: 'extracting',  label: 'Issues',            icon: MessageSquare },
  { id: 'arguing',     label: 'Arguments',         icon: MessageSquare },
  { id: 'detecting',   label: 'Circuit splits',    icon: GitBranch },
  { id: 'predicting',  label: 'Outcome',           icon: BarChart2 },
  { id: 'citing',      label: 'Citations',         icon: CheckCircle2 },
  { id: 'analysing',   label: 'Analytics',         icon: BarChart2 },
];

const STAGE_ORDER = STAGES.map(s => s.id);

export default function AgentPipeline({ currentStage }) {
  const currentIdx = STAGE_ORDER.indexOf(currentStage);

  return (
    <div className="card overflow-x-auto">
      <p className="text-xs font-semibold text-mist uppercase tracking-wide mb-4">
        Running analysis pipeline
      </p>

      <div className="flex items-center gap-0 min-w-max">
        {STAGES.map((stage, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          const pending = i > currentIdx;

          return (
            <React.Fragment key={stage.id}>
              <div className="flex flex-col items-center gap-1.5 min-w-[72px]">
                {/* Node */}
                <motion.div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center
                    transition-colors duration-300
                    ${done    ? 'bg-sage text-white' : ''}
                    ${active  ? 'bg-sage-light ring-2 ring-sage text-sage' : ''}
                    ${pending ? 'bg-stone text-stone-dark' : ''}
                  `}
                  animate={active ? { scale: [1, 1.08, 1] } : {}}
                  transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
                >
                  {done
                    ? <CheckCircle2 size={14} />
                    : <stage.icon size={13} />
                  }
                </motion.div>

                {/* Label */}
                <span className={`text-[10px] text-center leading-tight ${
                  active ? 'text-sage font-semibold' :
                  done   ? 'text-mist' :
                           'text-stone-dark'
                }`}>
                  {stage.label}
                </span>
              </div>

              {/* Connector */}
              {i < STAGES.length - 1 && (
                <div className="flex-1 h-px mx-1 relative min-w-[16px]">
                  <div className="absolute inset-0 bg-stone" />
                  {done && (
                    <motion.div
                      className="absolute inset-0 bg-sage"
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      style={{ transformOrigin: 'left' }}
                      transition={{ duration: 0.3 }}
                    />
                  )}
                  {active && (
                    <motion.div
                      className="absolute inset-0 bg-sage"
                      animate={{ scaleX: [0, 1] }}
                      style={{ transformOrigin: 'left' }}
                      transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
                    />
                  )}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}