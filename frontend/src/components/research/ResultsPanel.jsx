
import React, { useRef } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { BookOpen, List, Quote, Scale, ExternalLink, Gavel } from 'lucide-react';
import CitationsCard from './CitationsCard';
import ExportMenu from '../shared/ExportMenu';

const TABS = [
  { id: 'summary',   label: 'Summary',           icon: BookOpen },
  { id: 'issues',    label: 'Issues & Arguments', icon: List },
  { id: 'citations', label: 'Citations',          icon: Quote },
  { id: 'cases',     label: 'Cases',              icon: Scale },
];

export default function ResultsPanel({ result, onOpenIntelligence }) {
  const contentRef = useRef(null);

  const hasIntelligence = result.judge_profiles?.length > 0
    || result.divergences?.length > 0
    || result.outcome_prediction;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      {/* Meta bar */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-4">
          <span className="text-xs text-mist">
            {result.cases_analyzed} cases · {result.processing_time_seconds}s
          </span>
          {result.prior_context && (
            <span className="badge bg-sage-light text-sage-dark text-[11px]">
              Builds on prior research
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasIntelligence && (
            <button onClick={onOpenIntelligence} className="btn-secondary text-xs gap-1.5">
              <Gavel size={12} />
              Intelligence panel
            </button>
          )}
          <ExportMenu contentRef={contentRef} result={result} />
        </div>
      </div>

      {/* Tabs */}
      <Tabs.Root defaultValue="summary">
        <Tabs.List className="flex border-b border-stone mb-4 bg-white rounded-t-card overflow-hidden">
          {TABS.map(tab => (
            <Tabs.Trigger
              key={tab.id}
              value={tab.id}
              className="
                flex items-center gap-1.5 px-4 py-3 text-sm font-medium text-mist
                border-b-2 border-transparent
                hover:text-ink hover:bg-stone transition-colors duration-150
                data-[state=active]:border-sage data-[state=active]:text-sage data-[state=active]:bg-white
                flex-1 justify-center
              "
            >
              <tab.icon size={13} />
              <span className="hidden sm:block">{tab.label}</span>
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        <div ref={contentRef}>
          <Tabs.Content value="summary">
            <div className="card prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.summary}</ReactMarkdown>
            </div>
          </Tabs.Content>

          <Tabs.Content value="issues">
            <div className="space-y-4">
              {result.issues?.length > 0 && (
                <div className="card">
                  <h3 className="section-title mb-3">Legal Issues</h3>
                  <ol className="space-y-2">
                    {result.issues.map((issue, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-sm">
                        <span className="font-mono text-xs text-mist mt-0.5 w-5 flex-shrink-0">
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <span className="text-ink leading-relaxed">{issue}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              {result.arguments && (
                <div className="card prose prose-sm max-w-none">
                  <h3 className="section-title mb-3">Arguments</h3>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.arguments}</ReactMarkdown>
                </div>
              )}
            </div>
          </Tabs.Content>

          <Tabs.Content value="citations">
            <CitationsCard data={result.citation_verification} />
          </Tabs.Content>

          <Tabs.Content value="cases">
            <div className="space-y-3">
              {result.source_cases?.map((c, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="card group"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-serif text-base font-semibold text-ink leading-snug">{c.case_name}</h4>
                      <div className="flex flex-wrap items-center gap-2 mt-1">
                        <span className="font-mono text-[11px] text-mist">{c.court}</span>
                        <span className="text-stone-dark">·</span>
                        <span className="font-mono text-[11px] text-mist">{c.date_filed}</span>
                        {c.docket_number && (
                          <>
                            <span className="text-stone-dark">·</span>
                            <span className="font-mono text-[11px] text-mist">{c.docket_number}</span>
                          </>
                        )}
                      </div>
                      {c.excerpt && (
                        <p className="text-sm text-mist mt-2 leading-relaxed line-clamp-3">{c.excerpt}</p>
                      )}
                    </div>
                    {c.url && (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-ghost flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </Tabs.Content>
        </div>
      </Tabs.Root>
    </motion.div>
  );
}