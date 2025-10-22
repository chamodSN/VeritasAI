import React from 'react';
import { Link } from 'react-router-dom';

const NavBar = ({ onLogin, onLogout, isAuthenticated, user }) => {
  return (
    <header className="bg-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <i className="fas fa-balance-scale text-3xl text-primary-600"></i>
            </div>
            <div className="ml-4">
              <Link to="/" className="text-3xl font-bold text-gray-900">VeritasAI</Link>
              <p className="text-sm text-gray-600">Legal Multi-Agent Research System</p>
            </div>
          </div>
          <nav className="hidden md:flex items-center space-x-6">
            {/* Navigation links removed as requested */}
          </nav>
            <div className="flex items-center space-x-3">
              {isAuthenticated ? (
                <>
                  <div className="flex items-center space-x-2">
                    {user?.picture && (
                      <img src={user.picture} alt="avatar" className="w-8 h-8 rounded-full object-cover" />
                    )}
                    <span className="text-sm text-gray-700 hidden sm:block">{user?.name}</span>
                  </div>
                  <button onClick={onLogout} className="text-sm bg-red-600 text-white px-3 py-2 rounded hover:bg-red-700 transition-colors">
                    <i className="fas fa-sign-out-alt mr-1"></i>
                    Logout
                  </button>
                </>
              ) : (
                <button onClick={onLogin} className="text-sm bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 flex items-center transition-colors">
                  <i className="fas fa-user mr-2"></i>
                  Login / Sign up
                </button>
              )}
            </div>
        </div>
      </div>
    </header>
  );
};

export default NavBar;


