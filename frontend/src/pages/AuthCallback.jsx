import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function AuthCallback() {
  const { checkAuth } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');

    if (token) {
      localStorage.setItem('veritasai_token', token);
      window.history.replaceState({}, '', '/auth/callback');
    }

    checkAuth().then(() => navigate('/app', { replace: true }));
  }, []);

  return (
    <div className="min-h-screen bg-parchment flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-sage border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-mist">Signing you in…</p>
      </div>
    </div>
  );
}