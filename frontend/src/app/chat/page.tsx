// src/app/chat/page.tsx

"use client";

import { useState } from "react";
import ConnectionForm from "@/components/ConnectionForm";
import UploadPanel from "@/components/UploadPanel";
import ChatWindow from "@/components/ChatWindow";

interface ActiveConnection {
  provider: string;
  apiKey: string;
  baseUrl: string;
  model: string;
}

export default function ChatPage() {
  const [connection, setConnection] = useState<ActiveConnection | null>(null);

  if (!connection) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-12 space-y-6">
        <h1 className="text-2xl font-bold">Connect to a model</h1>
        <p className="text-gray-700">
          Choose a provider and enter credentials. Nothing is stored on the
          server — your key lives in this browser tab only.
        </p>
        <ConnectionForm onConnected={setConnection} />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 grid md:grid-cols-[1fr_320px] gap-6">
      <div className="order-2 md:order-1">
        <ChatWindow connection={connection} />
      </div>
      <aside className="order-1 md:order-2 space-y-4">
        <div className="border rounded-lg p-4 bg-white text-sm">
          <div className="font-semibold mb-1">Connected</div>
          <div className="text-gray-600">
            {connection.provider} · {connection.model || "default"}
          </div>
          <button
            onClick={() => setConnection(null)}
            className="mt-2 text-xs underline text-gray-500"
          >
            Disconnect
          </button>
        </div>
        <UploadPanel />
      </aside>
    </div>
  );
}