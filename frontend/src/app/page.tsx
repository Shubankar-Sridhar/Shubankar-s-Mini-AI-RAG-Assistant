// src/app/page.tsx

import Link from "next/link";

export default function HomePage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-16">
      <section className="text-center mb-16">
        <h1 className="text-4xl font-bold mb-4">
          Ask your PDFs anything
        </h1>
        <p className="text-lg text-gray-700 mb-8 max-w-2xl mx-auto">
          Upload documents, get grounded answers with citations. Hybrid
          retrieval combines semantic search with keyword precision. Bring
          your own API key, or run entirely on your own machine with Ollama
          or a GGUF model.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            href="/chat"
            className="px-6 py-3 bg-black text-white rounded-lg hover:bg-gray-800"
          >
            Start Chatting
          </Link>
          <Link
            href="/providers"
            className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-100"
          >
            Supported Providers
          </Link>
        </div>
      </section>

      <section className="grid md:grid-cols-3 gap-6">
        <Feature
          title="Hybrid Retrieval"
          description="BM25 keyword search fused with dense vector search using Reciprocal Rank Fusion. Higher recall than either alone."
        />
        <Feature
          title="Structured PDF Parsing"
          description="Preserves headings, tables, and images. Deterministic output means every parse of the same PDF produces the same chunks."
        />
        <Feature
          title="Bring Your Own Model"
          description="Cloud (OpenAI, Claude, Gemini, DeepSeek) or local (Ollama, GGUF via llama.cpp). Your keys never leave your browser."
        />
      </section>
    </div>
  );
}

function Feature({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 border rounded-lg bg-white">
      <h2 className="font-semibold text-lg mb-2">{title}</h2>
      <p className="text-sm text-gray-700">{description}</p>
    </div>
  );
}