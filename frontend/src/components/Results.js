export default function Results({ results }) {
  if (!results) return null;

  if (results.error) {
    return <div>Error: {results.error.message}</div>;
  }

  return (
    <div>
      <h2>Results</h2>
      <ul>
        {results.cases?.map(c => (
          <li key={c.id}>
            <strong>{c.title || "Untitled Case"}</strong> ({c.date})
            <br />
            {c.snippet || c.summary || "No snippet"}
            <br />
            <a href={c.url} target="_blank" rel="noreferrer">
              View
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}