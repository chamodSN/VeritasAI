import { useState } from "react";
import QueryForm from "./components/QueryForm";
import Results from "./components/Results";

function App() {
  const [results, setResults] = useState(null);

  return (
    <div>
      <h1>Legal Case Finder</h1>
      <QueryForm onResults={setResults} />
      <Results results={results} />
    </div>
  );
}

export default App;