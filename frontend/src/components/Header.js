import React from 'react';

const Header = () => {
  return (
    <header className="bg-legal-dark text-white shadow-legal-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-6">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-legal-blue to-accent-gold rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Veritas AI</h1>
                <p className="text-sm text-gray-300">Multi-Agent Legal Research System</p>
              </div>
            </div>
          </div>
          
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#search" className="text-gray-300 hover:text-white transition-colors duration-200">
              Search
            </a>
            <a href="#about" className="text-gray-300 hover:text-white transition-colors duration-200">
              About
            </a>
            <a href="#docs" className="text-gray-300 hover:text-white transition-colors duration-200">
              Documentation
            </a>
          </nav>

          <div className="flex items-center space-x-4">
            <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-300">
              <div className="w-2 h-2 bg-success-green rounded-full"></div>
              <span>System Online</span>
            </div>
            <button className="bg-legal-blue hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors duration-200">
              Get Started
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
