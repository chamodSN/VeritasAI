import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DOMPurify from 'dompurify';

const ResultSection = ({ title, icon, iconColor, content }) => {
  const [collapsed, setCollapsed] = useState(false);
  if (!content) return null;

  // Format content based on its type
  const formatContent = (content) => {
    if (typeof content === 'string') {
      return content;
    } else if (Array.isArray(content)) {
      // Format array as a numbered list
      return content.map((item, index) => `${index + 1}. ${item}`).join('\n\n');
    } else if (typeof content === 'object') {
      return JSON.stringify(content, null, 2);
    }
    return String(content);
  };

  const safeContent = formatContent(content);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-gray-900">
          <i className={`fas ${icon} mr-2 ${iconColor}`}></i>
          {title}
        </h3>
        <button onClick={() => setCollapsed(!collapsed)} className="text-sm text-gray-600 hover:text-gray-800">
          {collapsed ? (
            <>
              <i className="fas fa-chevron-down mr-1"></i>Expand
            </>
          ) : (
            <>
              <i className="fas fa-chevron-up mr-1"></i>Collapse
            </>
          )}
        </button>
      </div>

      {!collapsed && (
        <div className="prose max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {safeContent}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
};

export default ResultSection;


