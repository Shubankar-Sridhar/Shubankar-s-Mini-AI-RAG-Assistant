// src/app/providers/page.tsx

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Supported LLM Providers",
  description:
    "Configure OpenAI, Anthropic Claude, Google Gemini, DeepSeek, Ollama, or a local GGUF model as your knowledge assistant backend.",
};

interface ProviderDoc {
  id: string;
  label: string;
  baseUrl: string;
  modelExample: string;
  notes: string;
}

const PROVIDERS: ProviderDoc[] = [
  {
    id: "openai",
    label: "OpenAI",
    baseUrl: "https://api.openai.com/v1",
    modelExample: "gpt-4o-mini",
    notes: "Requires an API key from platform.openai.com.",
  },
  {
    id: "anthropic",
    label: "Anthropic Claude",
    baseUrl: "https://api.anthropic.com/v1",
    modelExample: "claude-3-5-sonnet-20241022",
    notes: "Uses Anthropic's OpenAI-compatible endpoint.",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
    modelExample: "gemini-1.5-flash",
    notes: "Uses Google's OpenAI compatibility layer.",
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    baseUrl: "https://api.deepseek.com/v1",
    modelExample: "deepseek-chat",
    notes: "OpenAI-compatible API.",
  },
  {
    id: "ollama",
    label: "Ollama (local)",
    baseUrl: "http://localhost:11434/v1",
    modelExample: "llama3.2",
    notes:
      "Runs on your machine. Enter the URL of your Ollama server. No API key needed.",
  },
  {
    id: "gguf",
    label: "GGUF via llama.cpp (local)",
    baseUrl: "http://localhost:8080/v1",
    modelExample: "local-model",
    notes:
      "Start llama-server with your GGUF file, then point this app to its URL.",
  },
];

export default function ProvidersPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-4">Supported Providers</h1>
      <p className="text-gray-700 mb-8">
        All providers are accessed through their OpenAI-compatible
        <code className="mx-1 px-1 bg-gray-100 rounded">/v1/chat/completions</code>
        endpoint. Cloud providers require an API key. Local providers require
        only the URL of your running server.
      </p>

      <div className="space-y-4">
        {PROVIDERS.map((p) => (
          <div key={p.id} className="border rounded-lg p-4 bg-white">
            <h2 className="font-semibold text-lg">{p.label}</h2>
            <dl className="mt-2 text-sm grid grid-cols-[120px_1fr] gap-x-4 gap-y-1">
              <dt className="text-gray-500">Base URL</dt>
              <dd className="font-mono">{p.baseUrl}</dd>
              <dt className="text-gray-500">Example model</dt>
              <dd className="font-mono">{p.modelExample}</dd>
              <dt className="text-gray-500">Notes</dt>
              <dd>{p.notes}</dd>
            </dl>
          </div>
        ))}
      </div>
    </div>
  );
}