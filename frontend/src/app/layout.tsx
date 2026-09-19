// src/app/layout.tsx

import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Shubankar's Mini AI RAG Assistant",
    template: "%s | Shubankar's Mini AI RAG Assistant",
  },
  description:
    "Upload PDFs and ask questions. Hybrid RAG retrieval with support for OpenAI, Claude, Gemini, DeepSeek, Ollama, and local GGUF models.",
  keywords: [
    "RAG",
    "retrieval augmented generation",
    "PDF question answering",
    "AI knowledge assistant",
    "local LLM",
    "Ollama",
  ],
  authors: [{ name: "Shubankar's Mini AI RAG Assistant" }],
  openGraph: {
    title: "Shubankar's Mini AI RAG Assistant",
    description:
      "Hybrid RAG over your own PDFs. Bring your own API key or use a local model.",
    type: "website",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-gray-50 text-gray-900">
        <header className="border-b bg-white sticky top-0 z-10">
          <nav className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6">
            <Link href="/" className="font-semibold text-lg">
              Shubankar's Mini AI RAG Assistant
            </Link>
            <div className="flex gap-4 text-sm text-gray-700">
              <Link href="/chat" className="hover:text-black">
                Chat
              </Link>
              <Link href="/providers" className="hover:text-black">
                Providers
              </Link>
            </div>
          </nav>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t bg-white text-center text-xs text-gray-500 py-4">
          Answers are grounded in uploaded documents. Bring your own API key.
        </footer>
      </body>
    </html>
  );
}