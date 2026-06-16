// src/components/layout/Sidebar.jsx
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, ChevronRight, RotateCcw, FileText } from 'lucide-react';
import { apiClient } from '../../lib/api';
import { useAuth } from '../../hooks/useAuth';

export default function Sidebar({ onSelectQuery, activeQuery, collapsed, onToggle }) {
  const { user } = useAuth();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) fetchHistory();
  }, [user]);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await apiClient.get('/api/user/history');
      setHistory(res.data.queries || []);
    } catch { /* silently fail */ }
    finally { setLoading(false); }
  };

  return (
    <aside
      className={`
        flex flex-col bg-white border-r border-stone flex-shrink-0
        transition-all duration-300 ease-smooth
        ${collapsed ? 'w-0 overflow-hidden' : 'w-sidebar'}
      `}
    >
      <div className="p-4 border-b border-stone flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-mist" />
          <span className="text-sm font-medium text-ink">History</span>
        </div>
        <button onClick={fetchHistory} disabled={loading} className="btn-ghost p-1">
          <RotateCcw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {history.length === 0 && !loading && (
          <div className="px-4 py-8 text-center">
            <FileText size={24} className="text-stone-dark mx-auto mb-2" />
            <p className="text-xs text-mist">Your past queries will appear here.</p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {history.map((item, i) => (
            <motion.button
              key={item.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              onClick={() => onSelectQuery(item.query)}
              className={`w-full text-left ${activeQuery === item.query ? 'sidebar-item-active' : 'sidebar-item'}`}
            >
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-ink truncate">{item.query}</p>
                <p className="text-xs text-mist mt-0.5">
                  {new Date(item.timestamp).toLocaleDateString()} · {item.cases_analyzed} cases
                </p>
              </div>
              <ChevronRight size={12} className="text-stone-dark flex-shrink-0 mt-0.5" />
            </motion.button>
          ))}
        </AnimatePresence>
      </div>
    </aside>
  );
}