"use client";
import { useEffect, useState } from "react";
export function QuantityInput({
  value,
  label,
  disabled,
  onCommit,
}: {
  value: number;
  label: string;
  disabled?: boolean;
  onCommit: (value: number) => void;
}) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);
  function commit() {
    const n = Number(draft);
    if (!Number.isInteger(n) || n < 1 || n > 50) {
      setDraft(String(value));
      return;
    }
    if (n !== value) onCommit(n);
  }
  return (
    <input
      type="number"
      min={1}
      max={50}
      step={1}
      aria-label={label}
      disabled={disabled}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          e.currentTarget.blur();
        }
      }}
    />
  );
}
