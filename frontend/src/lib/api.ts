// src/lib/api.ts

import type {
  ConnectionResult,
  ProvidersResponse,
  UploadResult,
} from "./types";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export function getBackendUrl(): string {
  return BACKEND_URL;
}

export async function fetchProviders(): Promise<ProvidersResponse> {
  const res = await fetch(`${BACKEND_URL}/api/providers`);
  if (!res.ok) throw new Error(`Failed to fetch providers: ${res.status}`);
  return res.json();
}

export interface ConnectionTestPayload {
  provider: string;
  api_key?: string;
  base_url?: string;
  model?: string;
}

export async function testConnection(
  payload: ConnectionTestPayload
): Promise<ConnectionResult> {
  const res = await fetch(`${BACKEND_URL}/api/test-connection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Connection test failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function uploadPdf(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BACKEND_URL}/api/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Upload failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function exportChat(
  sessionId: string,
  format: "md" | "json" | "pdf"
): Promise<Blob> {
  const res = await fetch(`${BACKEND_URL}/api/export/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, format }),
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  return res.blob();
}

export interface SummaryExportPayload {
  session_id: string;
  format: "md" | "pdf";
  provider: string;
  api_key: string;
  base_url: string;
  model: string;
}

export async function exportSummary(
  payload: SummaryExportPayload
): Promise<Blob> {
  const res = await fetch(`${BACKEND_URL}/api/export/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Summary export failed: ${res.status}`);
  return res.blob();
}

export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}