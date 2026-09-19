// src/components/MessageBubble.tsx

"use client";

import type { ChatMessage } from "@/lib/types";

interface Props {
  message: ChatMessage;
  streaming?: boolean;
}

export default function MessageBubble({ message, streaming }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] px-4 py-2 rounded-2xl whitespace-pre-wrap break-words ${
          isUser
            ? "bg-black text-white rounded-br-sm"
            : "bg-white border text-gray-900 rounded-bl-sm"
        }`}
      >
        <div className={streaming ? "streaming-caret" : ""}>
          {message.content || (streaming ? "" : "…")}
        </div>
      </div>
    </div>
  );
}