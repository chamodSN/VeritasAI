import React from 'react';

const StatusBadge = ({ status }) => {
  const map = {
    VALID: 'bg-green-100 text-green-800',
    INVALID: 'bg-red-100 text-red-800',
    NEEDS_REVIEW: 'bg-yellow-100 text-yellow-800'
  };
  const label = status || 'NEEDS_REVIEW';
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${map[label] || map.NEEDS_REVIEW}`}>{label}</span>;
};

const CitationsSection = ({ content }) => {
  if (!content) return null;

  let citationData = null;
  try {
    if (content.parsed_data) {
      citationData = content.parsed_data;
    } else {
      const rawData = content.raw_result || content.verification_details;
      if (rawData && typeof rawData === 'string') {
        const jsonMatch = rawData.match(/```json\n([\s\S]*?)\n```/);
        if (jsonMatch) {
          citationData = JSON.parse(jsonMatch[1]);
        } else {
          const jsonMatch2 = rawData.match(/\{[\s\S]*\}/);
          if (jsonMatch2) {
            citationData = JSON.parse(jsonMatch2[0]);
          }
        }
      }
    }
  } catch (e) {
    // ignore parse errors, fallback below
  }

  const { overall_verification_summary, individual_citation_analysis } = citationData || {};
  const citations = individual_citation_analysis || [];

  return (
    <div className="card">
      <h3 className="text-xl font-bold text-gray-900 mb-4">
        <i className="fas fa-quote-left mr-2 text-orange-600"></i>
        Citations
      </h3>

      {/* Remove compliance and other stats per requirements */}

      {citations.length > 0 ? (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {citations.map((citation, index) => (
            <div key={index} className="p-4 rounded-lg border bg-white">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h5 className="font-medium text-gray-900">{citation.citation}</h5>
                  <div className="flex items-center space-x-2 mt-1">
                    <StatusBadge status={citation.status} />
                    {citation.confidence_level && (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {citation.confidence_level} Confidence
                      </span>
                    )}
                    <button className="ml-2 text-yellow-700 hover:text-yellow-900 text-xs flex items-center">
                      <i className="fas fa-exclamation-triangle mr-1" />
                      Details
                    </button>
                  </div>
                </div>
              </div>

              {citation.issues && citation.issues !== 'None' && (
                <div className="mt-2 text-sm text-gray-700">
                  <span className="font-medium">Issues:</span> {citation.issues}
                </div>
              )}

              {citation.recommendations && citation.recommendations !== 'None needed.' && (
                <div className="mt-2 text-sm text-gray-700">
                  <span className="font-medium">Recommendations:</span> {citation.recommendations}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-gray-600">No parsed citation details available.</p>
      )}
    </div>
  );
};

export default CitationsSection;


