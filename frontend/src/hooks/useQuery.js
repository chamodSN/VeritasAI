// src/hooks/useQuery.js
import { useState, useCallback } from 'react';
import { apiClient } from '../lib/api';

export function useQuery() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [agentStatus, setAgentStatus] = useState(null); // pipeline state
  const [error, setError] = useState(null);
  const [jobId, setJobId] = useState(null);

  const submitQuery = useCallback(async (query) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setAgentStatus('fetching');

    try {
      const res = await apiClient.post('/api/query', { query });
      const data = res.data;

      // Async job pattern: poll for result
      if (data.status === 'pending' && data.job_id) {
        setJobId(data.job_id);
        await pollJobResult(data.job_id, setAgentStatus, setResult);
      } else if (data.status === 'completed') {
        // Cache hit — instant result
        setAgentStatus('completed');
        setResult(data.result);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Analysis failed. Please try again.');
      setAgentStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const submitPDF = useCallback(async (file) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setAgentStatus('fetching');

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await apiClient.post('/api/pdf/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setAgentStatus('completed');
      setResult(res.data.analysis);
    } catch (err) {
      setError(err.response?.data?.detail || 'PDF analysis failed.');
      setAgentStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, agentStatus, error, submitQuery, submitPDF };
}

// Agent stage progression for the pipeline visualiser
const AGENT_STAGES = [
  'fetching',       // fetch_cases
  'judging',        // judge_intelligence
  'summarising',    // summarize
  'extracting',     // extract_issues
  'arguing',        // generate_arguments
  'detecting',      // divergence
  'predicting',     // outcome_predictor
  'citing',         // verify_citations
  'analysing',      // analytics
  'completed',
];

async function pollJobResult(jobId, setAgentStatus, setResult) {
  let stageIdx = 0;

  // Advance the visualiser stage every ~3s while polling
  const stageInterval = setInterval(() => {
    stageIdx = Math.min(stageIdx + 1, AGENT_STAGES.length - 2);
    setAgentStatus(AGENT_STAGES[stageIdx]);
  }, 3000);

  try {
    for (let attempt = 0; attempt < 40; attempt++) {
      await new Promise(r => setTimeout(r, 2000));
      const res = await apiClient.get(`/api/query/status/${jobId}`);
      const { status, result } = res.data;

      if (status === 'completed' && result) {
        clearInterval(stageInterval);
        setAgentStatus('completed');
        setResult(result);
        return;
      }
      if (status === 'failed') {
        clearInterval(stageInterval);
        throw new Error('Analysis job failed');
      }
    }
    throw new Error('Analysis timed out. Please try again.');
  } finally {
    clearInterval(stageInterval);
  }
}