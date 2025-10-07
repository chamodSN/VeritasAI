import React from 'react';
import Header from './components/Header';
import Footer from './components/Footer';
import QueryParser from "./components/QueryParser";

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <QueryParser />
      </main>
      <Footer />
    </div>
  );
}

export default App;