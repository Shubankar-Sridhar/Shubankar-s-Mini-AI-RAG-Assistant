// src/components/ExportButtons.tsx

"use client";

import { useState } from "react";
import { exportChat, triggerDownload } from "@/lib/api";

interface Props {
  sessionId: string;
}

export default function ExportButtons({ sessionId }: Props) {
  const [busy, setBusy] = useState<string | null>(null);

  async function handleExport(format: "md" | "json" | "pdf") {
    setBusy(format);
    try {
      const blob = await exportChat(sessionId, format);
      triggerDownload(blob, `chat_${sessionId}.${format}`);
    } catch (e) {
      alert(String(e));
    } finally {
      setBusy(null);
    }
  }

  if (!sessionId) return null;

  return (
    <div className="flex gap-2">
      <button
        onClick={() => handleExport("md")}
        disabled={busy !== null}
        className="text-xs px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50"
      >
        {busy === "md" ? "…" : "Export MD"}
      </button>
      <button
        onClick={() => handleExport("json")}
        disabled={busy !== null}
        className="text-xs px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50"
      >
        {busy === "json" ? "…" : "Export JSON"}
      </button>
      <button
        onClick={() => handleExport("pdf")}
        disabled={busy !== null}
        className="text-xs px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50"
      >
        {busy === "pdf" ? "…" : "Export PDF"}
      </button>
    </div>
  );
}