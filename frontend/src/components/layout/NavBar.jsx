// src/components/layout/NavBar.jsx
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LogOut, User } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export default function NavBar() {
  const { user, login, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <header className="h-14 bg-white border-b border-stone flex items-center px-6 flex-shrink-0 z-30">
      {/* Logo */}
      <Link to={user ? '/app' : '/'} className="flex items-center gap-2.5 flex-shrink-0">
        <ScalesIcon className="w-6 h-6 text-sage" />
        <span className="font-serif text-xl font-semibold text-ink tracking-tight">VeritasAI</span>
      </Link>

      <div className="flex-1" />

      {/* Right side */}
      {user ? (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            {user.picture ? (
              <img src={user.picture} alt="" className="w-7 h-7 rounded-full object-cover ring-1 ring-stone" />
            ) : (
              <div className="w-7 h-7 rounded-full bg-sage-light flex items-center justify-center">
                <User size={14} className="text-sage" />
              </div>
            )}
            <span className="text-sm font-medium text-ink hidden sm:block">{user.name}</span>
          </div>
          <button onClick={handleLogout} className="btn-ghost text-mist">
            <LogOut size={14} />
            <span className="hidden sm:block">Sign out</span>
          </button>
        </div>
      ) : (
        <button onClick={login} className="btn-primary">
          Sign in with Google
        </button>
      )}
    </header>
  );
}

function ScalesIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M12 3v18M5 8l7-5 7 5M5 8l3 7H2l3-7zM19 8l3 7h-6l3-7zM3 21h18" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}