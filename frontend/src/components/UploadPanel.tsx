// src/components/UploadPanel.tsx

"use client";

import { useRef, useState } from "react";
import { uploadPdf } from "@/lib/api";
import type { UploadResult } from "@/lib/types";

export default function UploadPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
    setUploading(true);
    setResult(null);
    setError(null);
    try {
      const res = await uploadPdf(file);
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      <h3 className="font-semibold">Upload a PDF</h3>

      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        disabled={uploading}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
        className="block w-full text-sm"
      />

      {uploading && <div className="text-sm text-gray-600">Parsing…</div>}

      {error && (
        <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">
          {error}
        </div>
      )}

      {result && (
        <div className="text-sm text-green-800 bg-green-50 border border-green-200 rounded p-2">
          Ingested <span className="font-mono">{result.filename}</span> —{" "}
          {result.chunk_count} chunks, {result.image_count} images.
        </div>
      )}
    </div>
  );
}