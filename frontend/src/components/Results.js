import React from "react";

export default function Results({ results }) {
  if (!results) return null;

  if (results.error) {
    return <div className="text-red-500">Error: {results.error.message}</div>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800">Results</h2>
      {results.cases?.length === 0 ? (
        <p className="text-gray-600">No cases found.</p>
      ) : (
        <ul className="space-y-2">
          {results.cases?.map((caseItem) => (
            <li key={caseItem.case_id} className="bg-gray-50 p-3 rounded border">
              <strong className="text-gray-900">
                {caseItem.title || caseItem.summary?.case || "Unknown Case"}
              </strong>
              <br />
              <span className="text-sm text-gray-600">
                Court: {caseItem.court || caseItem.summary?.court || "Unknown"} |{" "}
                Date: {caseItem.date || caseItem.related_precedents?.[0]?.date || "Unknown"}
              </span>
              <br />
              <p className="text-sm text-gray-700">
                {caseItem.summary?.issue || "No summary available"}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}