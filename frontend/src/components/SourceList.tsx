// src/components/SourceList.tsx

"use client";

import type { SourceCitation } from "@/lib/types";

interface Props {
  sources: SourceCitation[];
}

function basename(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1];
}

export default function SourceList({ sources }: Props) {
  if (!sources.length) return null;

  return (
    <div className="border rounded-lg p-3 bg-gray-50">
      <div className="text-xs font-semibold text-gray-600 mb-2">
        Sources ({sources.length})
      </div>
      <ul className="space-y-1">
        {sources.map((s, i) => (
          <li key={s.id} className="text-xs text-gray-700">
            <span className="inline-block w-5 text-gray-400">[{i + 1}]</span>
            <span className="font-mono">{basename(s.source)}</span>
            {s.heading && (
              <span className="text-gray-500"> — {s.heading}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}