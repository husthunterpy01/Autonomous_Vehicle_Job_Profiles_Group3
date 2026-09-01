/**
 * Mock auth — FE-8 is UI-only for now, there's no backend User model or
 * login endpoint yet (per Martin, backend logic gets assigned separately).
 * Swap this out for a real API call once that exists; the shape of
 * LoginResult is the contract the real call should match.
 */

export type LoginResult = { ok: true; token: string } | { ok: false };

const MOCK_ACCOUNT = {
  email: "demo@avjobfinder.com",
  password: "password123",
};

export function mockLogin(
  email: string,
  password: string,
): Promise<LoginResult> {
  return new Promise((resolve) => {
    setTimeout(() => {
      if (email === MOCK_ACCOUNT.email && password === MOCK_ACCOUNT.password) {
        resolve({ ok: true, token: "mock-token" });
      } else {
        resolve({ ok: false });
      }
    }, 900);
  });
}
