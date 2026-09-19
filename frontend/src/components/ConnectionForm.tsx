// src/components/ConnectionForm.tsx

"use client";

import { useEffect, useState } from "react";
import { fetchProviders, testConnection } from "@/lib/api";
import type {
  ConnectionResult,
  ProviderId,
  ProvidersResponse,
} from "@/lib/types";

interface Props {
  onConnected: (result: {
    provider: ProviderId;
    apiKey: string;
    baseUrl: string;
    model: string;
  }) => void;
}

export default function ConnectionForm({ onConnected }: Props) {
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [provider, setProvider] = useState<ProviderId>("openai");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ConnectionResult | null>(null);

  // Load provider list from backend once
  useEffect(() => {
    fetchProviders()
      .then(setProviders)
      .catch((e) => setResult({ success: false, message: String(e), provider: "", model: "" }));
  }, []);

  const selected = providers
    ? [...providers.cloud, ...providers.local].find((p) => p.id === provider)
    : null;

  async function handleTest() {
    setTesting(true);
    setResult(null);
    try {
      const res = await testConnection({
        provider,
        api_key: apiKey,
        base_url: baseUrl,
        model,
      });
      setResult(res);
      if (res.success) {
        onConnected({ provider, apiKey, baseUrl, model });
      }
    } catch (e) {
      setResult({
        success: false,
        message: `Failed to connect, wrong API (${String(e)})`,
        provider,
        model,
      });
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="border rounded-lg p-6 bg-white space-y-4">
      <h2 className="font-semibold text-lg">Connect to a model</h2>

      <div className="space-y-3">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Provider</label>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as ProviderId)}
            className="w-full border rounded px-3 py-2"
          >
            {providers?.cloud.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
            {providers?.local.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        {selected?.requires_key && (
          <div>
            <label className="block text-sm text-gray-600 mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full border rounded px-3 py-2 font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              Your key is sent only to the backend on your behalf and never stored.
            </p>
          </div>
        )}

        {selected?.requires_url && (
          <div>
            <label className="block text-sm text-gray-600 mb-1">
              Server URL
            </label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={
                provider === "ollama"
                  ? "http://localhost:11434"
                  : "http://localhost:8080"
              }
              className="w-full border rounded px-3 py-2 font-mono text-sm"
            />
          </div>
        )}

        <div>
          <label className="block text-sm text-gray-600 mb-1">
            Model (optional)
          </label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="Leave blank to use provider default"
            className="w-full border rounded px-3 py-2 font-mono text-sm"
          />
        </div>
      </div>

      <button
        onClick={handleTest}
        disabled={testing}
        className="w-full px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
      >
        {testing ? "Testing..." : "Test connection"}
      </button>

      {result && (
        <div
          className={`text-sm p-3 rounded ${
            result.success
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {result.message}
        </div>
      )}
    </div>
  );
}