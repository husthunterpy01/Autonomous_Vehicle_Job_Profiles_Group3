import { API_BASE_URL } from "./api";

const AUTH_URL = `${API_BASE_URL}/api/v1/auth`;

export type AuthUser = {
  user_id: string;
  email: string;
  username: string;
  full_name: string;
  created_at: string;
};

export type AuthResponse = {
  user: AuthUser;
  token_type: "bearer";
  expires_in: number;
};

export type SignUpPayload = {
  email: string;
  username: string;
  full_name: string;
  password: string;
};

export class AuthApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${AUTH_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

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
    throw new AuthApiError(
      message || "Authentication request failed",
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function signUp(payload: SignUpPayload): Promise<AuthResponse> {
  return authRequest<AuthResponse>("/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function signIn(
  identifier: string,
  password: string,
  rememberMe: boolean,
): Promise<AuthResponse> {
  return authRequest<AuthResponse>("/login", {
    method: "POST",
    body: JSON.stringify({
      identifier,
      password,
      remember_me: rememberMe,
    }),
  });
}

export function getCurrentUser(): Promise<AuthUser> {
  return authRequest<AuthUser>("/me");
}

export function signOut(): Promise<void> {
  return authRequest<void>("/logout", { method: "POST" });
}
