// src/lib/types.ts

export type ProviderId =
  | "openai"
  | "anthropic"
  | "gemini"
  | "deepseek"
  | "ollama"
  | "gguf";

export interface ProviderInfo {
  id: ProviderId;
  label: string;
  requires_key: boolean;
  requires_url?: boolean;
}

export interface ProvidersResponse {
  cloud: ProviderInfo[];
  local: ProviderInfo[];
}

export interface ConnectionResult {
  success: boolean;
  message: string;
  provider: string;
  model: string;
}

export interface SourceCitation {
  id: string;
  source: string;
  heading: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
}

export interface UploadResult {
  status: string;
  filename: string;
  chunk_count: number;
  image_count: number;
  markdown_path?: string;
}

// SSE event payloads from the backend
export type SSEEvent =
  | { event: "session"; data: { session_id: string } }
  | { event: "status"; data: { phase: string } }
  | { event: "sources"; data: SourceCitation[] }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: { chunk_count: number } }
  | { event: "error"; data: { message: string } };