import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Scale, CheckCircle2, Gavel, GitBranch, TrendingUp, FileSearch } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const DIFFERENTIATORS = [
  {
    icon: FileSearch,
    title: 'Live case law',
    desc: 'Results from CourtListener — 8M+ opinions. Cases filed this week. Not training data from two years ago.',
  },
  {
    icon: Gavel,
    title: 'Judge intelligence',
    desc: 'Appointment history, political affiliation, practice area tendencies — for the specific judge on your case.',
  },
  {
    icon: GitBranch,
    title: 'Circuit splits detected',
    desc: 'Automatically identifies when circuits disagree, names the split, and explains the strategic implication.',
  },
  {
    icon: CheckCircle2,
    title: 'Citations that exist',
    desc: 'Every citation cross-checked against CourtListener\'s database. Hallucinated references flagged before you see them.',
  },
  {
    icon: TrendingUp,
    title: 'Outcome analysis',
    desc: 'Win/loss signal derived from the actual retrieved cases — grounded, transparent, not a black box.',
  },
  {
    icon: Scale,
    title: 'Research memory',
    desc: 'Sessions persist. Return to a research thread weeks later. VeritasAI knows what you\'ve already found.',
  },
];

export default function LandingPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-parchment">
      {/* Nav */}
      <header className="h-14 border-b border-stone bg-parchment/80 backdrop-blur-sm sticky top-0 z-20 flex items-center px-6">
        <div className="flex items-center gap-2.5">
          <ScalesIcon className="w-5 h-5 text-sage" />
          <span className="font-serif text-lg font-semibold text-ink">VeritasAI</span>
        </div>
        <div className="flex-1" />
        {user ? (
          <button onClick={() => navigate('/app')} className="btn-primary text-sm">
            Open workspace
          </button>
        ) : (
          <button onClick={login} className="btn-primary text-sm">
            Sign in with Google
          </button>
        )}
      </header>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-24 pb-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        >
          {/* Animated scales */}
          <motion.div
            className="flex justify-center mb-8"
            animate={{ rotate: [0, 2, 0, -2, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          >
            <ScalesIcon className="w-14 h-14 text-sage" />
          </motion.div>

          <h1 className="font-serif text-display text-ink leading-tight">
            Legal research that<br />
            <em className="not-italic text-sage">knows what it's citing.</em>
          </h1>

          <p className="mt-5 text-base text-mist max-w-xl mx-auto leading-relaxed">
            Six AI agents run in sequence: fetch live case law, extract issues,
            build arguments, detect circuit splits, verify every citation,
            and profile the judge on your case.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <button onClick={user ? () => navigate('/app') : login} className="btn-primary text-base px-6 py-3">
              {user ? 'Open workspace' : 'Get started — it\'s free'}
            </button>
          </div>
        </motion.div>
      </section>

      {/* Why not ChatGPT */}
      <section className="max-w-5xl mx-auto px-6 pb-24">
        <p className="text-xs font-sans font-semibold text-mist uppercase tracking-widest text-center mb-10">
          What ChatGPT and Claude cannot do
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {DIFFERENTIATORS.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.07, duration: 0.3 }}
              className="card group"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-btn bg-sage-light flex items-center justify-center flex-shrink-0 group-hover:bg-sage transition-colors duration-150">
                  <item.icon size={15} className="text-sage group-hover:text-white transition-colors duration-150" />
                </div>
                <h3 className="font-sans font-semibold text-sm text-ink">{item.title}</h3>
              </div>
              <p className="text-sm text-mist leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-stone py-6 text-center">
        <p className="text-xs text-mist">
          VeritasAI · For research purposes only · Not legal advice
        </p>
      </footer>
    </div>
  );
}

function ScalesIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 3v18M5 8l7-5 7 5M5 8l3 7H2l3-7zM19 8l3 7h-6l3-7zM3 21h18" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}