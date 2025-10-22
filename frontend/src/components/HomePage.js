import React from 'react';
import { motion } from 'framer-motion';

const services = [
  { icon: 'fa-gavel', title: 'Issue Extraction Agent', desc: 'Identifies legal issues precisely from queries and documents.' },
  { icon: 'fa-comments', title: 'Argument Agent', desc: 'Builds structured arguments with supporting authorities.' },
  { icon: 'fa-quote-left', title: 'Citation Agent', desc: 'Validates citations and flags questionable references.' },
  { icon: 'fa-balance-scale', title: 'Analytics Agent', desc: 'Discovers patterns across case law and jurisdictions.' }
];

const HomePage = ({ user, isAuthenticated }) => {
  return (
    <div className="">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24">
          <div className="grid md:grid-cols-2 gap-10 items-center">
            <div>
              {isAuthenticated && user && (
                <div className="flex items-center gap-3 mb-6">
                  {user.picture && (
                    <img 
                      src={user.picture} 
                      alt="User avatar" 
                      className="w-12 h-12 rounded-full object-cover"
                    />
                  )}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      Welcome back, {user.name}!
                    </h3>
                    <p className="text-sm text-gray-600">Ready to continue your legal research?</p>
                  </div>
                </div>
              )}
              <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 leading-tight">
                Legal Research, Verified by Multi‑Agent AI
              </h1>
              <p className="mt-4 text-gray-600 text-lg">
                Summaries, issues, arguments, and citation verification — streamlined for lawyers, firms, and students.
              </p>
              <div className="mt-6 flex gap-3">
                <a href="/app" className="btn-primary"><i className="fas fa-rocket mr-2"></i>Launch App</a>
                <a href="/pricing" className="btn-secondary">View Pricing</a>
              </div>
            </div>
            <div className="relative">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="card">
                <div className="grid grid-cols-1 gap-4">
                  {services.map((s, i) => (
                    <motion.div key={s.title} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 + i * 0.1 }} className="flex items-start">
                      <i className={`fas ${s.icon} text-primary-600 text-xl mr-3`}></i>
                      <div>
                        <h3 className="font-semibold text-gray-900">{s.title}</h3>
                        <p className="text-gray-600 text-sm">{s.desc}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Plans */}
      <section className="bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h2 className="text-3xl font-bold text-center mb-12 text-gray-900">Pricing Plans List</h2>
          
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Free Plan */}
            <div className="bg-black rounded-xl p-8 text-white">
              <div className="text-center mb-6">
                <div className="text-3xl font-bold mb-2">$0 / month</div>
                <div className="text-2xl font-bold text-green-400 mb-4 border-b border-gray-600 pb-2">Free</div>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Basic Case Finder (limited searches: 20/month)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>View case summaries (short previews)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Ads / watermark on exports</span>
                </div>
              </div>
            </div>

            {/* Student Plan */}
            <div className="bg-black rounded-xl p-8 text-white">
              <div className="text-center mb-6">
                <div className="text-3xl font-bold mb-2">$9 / month or $90 / year</div>
                <div className="text-2xl font-bold text-red-400 mb-4 border-b border-gray-600 pb-2">Student</div>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Case Finder + IR Agent (200 searches/month)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Basic Summarization Agent (short summaries)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Basic Citation Agent (limited references)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Export to PDF (watermarked)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Email support</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto mt-8">
            {/* Lawyer Plan */}
            <div className="bg-black rounded-xl p-8 text-white">
              <div className="text-center mb-6">
                <div className="text-3xl font-bold mb-2">$49 / month or $490 / year</div>
                <div className="text-2xl font-bold text-blue-400 mb-4 border-b border-gray-600 pb-2">Lawyer</div>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Unlimited Case Finder & IR Agent</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Advanced Summarization Agent (detailed + legal context)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Verified Citation Agent</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Precedent Agent (similar case suggestions)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Unlimited exports (PDF/DOCX)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Priority support</span>
                </div>
              </div>
            </div>

            {/* Law Firm Plan */}
            <div className="bg-black rounded-xl p-8 text-white">
              <div className="text-center mb-6">
                <div className="text-3xl font-bold mb-2">Custom pricing (starting $199 / month, team of 5)</div>
                <div className="text-2xl font-bold text-purple-400 mb-4 border-b border-gray-600 pb-2">Law Firm</div>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Everything in Lawyer plan</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Team dashboards & collaboration</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Bulk document processing</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Multi-jurisdiction citation checks</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Full API & integrations (case mgmt systems, SharePoint, etc.)</span>
                </div>
                <div className="flex items-center">
                  <i className="fas fa-star text-yellow-400 mr-3"></i>
                  <span>Dedicated account manager</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Data Sources */}
      <section className="bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-6">Data Sources</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="bg-white p-6 rounded-lg shadow-sm">
                <i className="fas fa-database text-3xl text-blue-600 mb-4"></i>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">CourtListener API</h3>
                <p className="text-gray-600 text-sm">Federal court cases and opinions from PACER</p>
              </div>
            </div>
            <div className="text-center">
              <div className="bg-white p-6 rounded-lg shadow-sm">
                <i className="fas fa-balance-scale text-3xl text-green-600 mb-4"></i>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Legal Databases</h3>
                <p className="text-gray-600 text-sm">Verified legal precedents and case law</p>
              </div>
            </div>
            <div className="text-center">
              <div className="bg-white p-6 rounded-lg shadow-sm">
                <i className="fas fa-shield-alt text-3xl text-purple-600 mb-4"></i>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Citation Verification</h3>
                <p className="text-gray-600 text-sm">AI-powered validation with confidence scoring</p>
              </div>
            </div>
          </div>
          <p className="text-center text-gray-600 max-w-3xl mx-auto mt-8">
            We leverage publicly available court data and reputable legal sources. Citations are validated and flagged when uncertain.
          </p>
        </div>
      </section>
    </div>
  );
};

export default HomePage;


