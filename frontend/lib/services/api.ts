export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type PageResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

/** Shared JSON fetch helper: builds on `fetch`, normalizes FastAPI error
 *  payloads (`{ detail }`) into a single message, and surfaces network
 *  failures (offline, DNS, CORS) as an ApiError instead of a raw throw. */
export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    const headers: Record<string, string> = {
      ...(init?.headers as Record<string, string> | undefined),
    };
    // JSON Content-Type on GET/HEAD forces a CORS preflight. Only send it
    // when there is a body (POST/PATCH/PUT).
    if (init?.body != null && headers["Content-Type"] == null) {
      headers["Content-Type"] = "application/json";
    }
    response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      ...init,
      headers,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(
      "Unable to reach the server. Check your connection and try again.",
      0,
    );
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: string | Array<{ msg?: string }>;
    } | null;
    const detail = payload?.detail;
    const message = Array.isArray(detail)
      ? detail
          .map((item) => item.msg)
          .filter(Boolean)
          .join(". ")
      : detail;
    throw new ApiError(
      message || `Request failed with status ${response.status}`,
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
