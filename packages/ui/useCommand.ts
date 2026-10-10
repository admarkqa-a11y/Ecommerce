"use client";
import { useRef } from "react";
import { post } from "./api";
/** Preserve financial/stock command identity across uncertain network retries.
 * Closing and reopening the editor begins a new intentional operation.
 */
export function useCommand() {
  const keys = useRef(new Map<string, string>());
  return function command<T = any>(path: string, data: unknown): Promise<T> {
    const signature = path + JSON.stringify(data);
    if (!keys.current.has(signature))
      keys.current.set(signature, crypto.randomUUID());
    return post<T>(path, data, {
      "Idempotency-Key": keys.current.get(signature)!,
    });
  };
}
