// Small typed client for the Luphina API. Requests go to /api/*, which
// next.config.ts forwards to the backend.

import { type MessageKey, translateNow } from "./i18n";

const TOKEN_KEY = "luphina.token";
// Sign-ins saved before the rename to Luphina still work until the next sign-in or sign-out
const LEGACY_TOKEN_KEY = "autoflow.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function getToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY) ?? window.localStorage.getItem(LEGACY_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(LEGACY_TOKEN_KEY);
  } catch {
    // Storage unavailable (private mode): the session lasts for this page only
  }
}

// FastAPI's built-in messages say nothing useful to a shop owner
const GENERIC_DETAILS = new Set([
  "Not Found",
  "Not authenticated",
  "Forbidden",
  "Unauthorized",
  "Method Not Allowed",
  "Internal Server Error",
  "Request Entity Too Large",
]);

const STATUS_MESSAGES: Record<number, MessageKey> = {
  401: "err.401",
  403: "err.403",
  404: "err.404",
  413: "err.413",
  429: "err.429",
};

function fieldName(location: unknown): string {
  // ["body", "steps", 0, "name"] -> "steps 1 name"
  if (!Array.isArray(location)) return "";
  return location
    .filter((part) => part !== "body" && part !== "query" && part !== "path")
    .map((part) => (typeof part === "number" ? String(part + 1) : String(part).replaceAll("_", " ")))
    .join(" ");
}

/** A message a non-technical person can act on. */
function describe(status: number, detail: unknown): string {
  if (status >= 500) return translateNow("err.500");
  if (typeof detail === "string" && detail && !GENERIC_DETAILS.has(detail)) return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors
    return detail
      .map((item) => {
        if (typeof item !== "object" || !item || !("msg" in item)) return String(item);
        const where = fieldName((item as { loc?: unknown }).loc);
        const message = String(item.msg).replace(/^Value error, /, "");
        return where ? `${where}: ${message}` : message;
      })
      .join("; ");
  }
  const key = STATUS_MESSAGES[status];
  return translateNow(key ?? "err.generic");
}

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; headers?: Record<string, string> } = {},
): Promise<T> {
  const headers: Record<string, string> = { ...options.headers };
  const token = getToken();

  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: options.method ?? (options.body !== undefined ? "POST" : "GET"),
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, translateNow("err.network"));
  }

  if (response.status === 204) return undefined as T;

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, describe(response.status, (data as { detail?: unknown }).detail));
  }

  return data as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return translateNow("err.network");
  if (error instanceof Error) return error.message;
  return translateNow("err.generic");
}
