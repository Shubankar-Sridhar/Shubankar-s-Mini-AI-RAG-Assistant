// src/components/ChatWindow.tsx

"use client";

import { useEffect, useRef, useState } from "react";
import { getBackendUrl } from "@/lib/api";
import type { ChatMessage, SourceCitation } from "@/lib/types";
import MessageBubble from "./MessageBubble";
import SourceList from "./SourceList";
import ExportButtons from "./ExportButtons";

interface ConnectionState {
  provider: string;
  apiKey: string;
  baseUrl: string;
  model: string;
}

interface Props {
  connection: ConnectionState;
}

export default function ChatWindow({ connection }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<SourceCitation[]>([]);
  const [sessionId, setSessionId] = useState<string>("");
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState<string>("");

  const eventSourceRef = useRef<EventSource | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, streaming]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  function handleSend() {
    const query = input.trim();
    if (!query || streaming) return;

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setInput("");
    setSources([]);
    setStreaming(true);
    setStatus("connecting");

    const params = new URLSearchParams({
      query,
      provider: connection.provider,
      api_key: connection.apiKey,
      base_url: connection.baseUrl,
      model: connection.model,
    });
    if (sessionId) params.set("session_id", sessionId);

    const url = `${getBackendUrl()}/api/chat/stream?${params.toString()}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    // Assistant message buffer — appended token by token
    let assistantBuffer = "";

    es.addEventListener("session", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setSessionId(data.session_id);
    });

    es.addEventListener("status", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setStatus(data.phase);
    });

    es.addEventListener("sources", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      setSources(data);
    });

    es.addEventListener("token", (e) => {
      const data = JSON.parse((e as MessageEvent).data);
      assistantBuffer += data.text;

      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "assistant") {
          // Update the trailing assistant message in place
          const copy = prev.slice(0, -1);
          copy.push({ role: "assistant", content: assistantBuffer });
          return copy;
        }
        return [...prev, { role: "assistant", content: assistantBuffer }];
      });
    });

    es.addEventListener("done", () => {
      setStreaming(false);
      setStatus("");
      es.close();
      eventSourceRef.current = null;
    });

    es.addEventListener("error", (e) => {
      // SSE errors come through here, including transport errors
      try {
        const data = JSON.parse((e as MessageEvent).data);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${data.message}` },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Error: connection failed" },
        ]);
      }
      setStreaming(false);
      setStatus("");
      es.close();
      eventSourceRef.current = null;
    });
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs text-gray-500">
          {connection.provider} · {connection.model || "default"} ·{" "}
          {status ? status : streaming ? "streaming" : "idle"}
        </div>
        <ExportButtons sessionId={sessionId} />
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto border rounded-lg p-4 bg-gray-50 space-y-4"
      >
        {messages.length === 0 && (
          <div className="text-center text-gray-400 py-12">
            Ask a question about your uploaded documents.
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            message={m}
            streaming={
              streaming &&
              i === messages.length - 1 &&
              m.role === "assistant"
            }
          />
        ))}
        {sources.length > 0 && <SourceList sources={sources} />}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          disabled={streaming}
          className="flex-1 border rounded-lg px-4 py-2 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="px-6 py-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
        >
          {streaming ? "Streaming…" : "Send"}
        </button>
      </form>
    </div>
  );
}