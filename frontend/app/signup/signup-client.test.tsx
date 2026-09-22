import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import SignUpClient from "./signup-client";

const { signUpMock, pushMock } = vi.hoisted(() => ({
  signUpMock: vi.fn(),
  pushMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) => <a href={href}>{children}</a>,
}));

vi.mock("@/app/login/login-showcase", () => ({
  default: () => null,
}));

vi.mock("@/lib/services/auth", () => ({
  signUp: signUpMock,
  AuthApiError: class AuthApiError extends Error {},
}));

const validFields = {
  Name: "Avery Chen",
  Username: "avery.chen",
  "Email Address": "avery@example.com",
  Password: "SecurePassword!123",
  "Confirm Password": "SecurePassword!123",
};

function submitForm(overrides: Partial<typeof validFields> = {}) {
  const { container } = render(<SignUpClient />);
  for (const [label, value] of Object.entries({
    ...validFields,
    ...overrides,
  })) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  const form = container.querySelector("form");
  expect(form).not.toBeNull();
  expect(fireEvent.submit(form!)).toBe(false);
}

function expectFieldError(label: string, message: string, id: string) {
  const input = screen.getByLabelText(label);
  const error = document.getElementById(id);
  expect(error?.textContent).toBe(message);
  expect(error?.getAttribute("role")).toBe("alert");
  expect(input.getAttribute("aria-invalid")).toBe("true");
  expect(input.getAttribute("aria-describedby")?.split(" ")).toContain(id);
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("sign-up form validation", () => {
  it.each([
    ["Name", "Name is required.", "signup-name-error"],
    ["Username", "Username is required.", "signup-username-error"],
    ["Email Address", "Email is required.", "signup-email-error"],
    ["Password", "Password is required.", "signup-password-error"],
    [
      "Confirm Password",
      "Confirm your password.",
      "signup-confirm-password-error",
    ],
  ])("prevents submission when %s is empty", (label, message, id) => {
    submitForm({ [label]: "" });

    expectFieldError(label, message, id);
    expect(signUpMock).not.toHaveBeenCalled();
  });

  it("rejects an invalid email address", () => {
    submitForm({ "Email Address": "not-an-email" });

    expectFieldError(
      "Email Address",
      "Enter a valid email address.",
      "signup-email-error",
    );
    expect(signUpMock).not.toHaveBeenCalled();
  });

  it.each([
    ["a username shorter than 3 characters", "ab"],
    ["a username longer than 50 characters", "a".repeat(51)],
    ["a username containing spaces", "avery chen"],
    ["a username containing unsupported special characters", "avery@chen"],
  ])("rejects %s", (_description, username) => {
    submitForm({ Username: username });

    expectFieldError(
      "Username",
      "Username must be 3–50 characters and use only letters, numbers, underscores, periods, or hyphens.",
      "signup-username-error",
    );
    expect(signUpMock).not.toHaveBeenCalled();
  });

  it("rejects a password shorter than the existing 12 character minimum", () => {
    submitForm({ Password: "Shortpass1!", "Confirm Password": "Shortpass1!" });

    expectFieldError(
      "Password",
      "Password must be at least 12 characters.",
      "signup-password-error",
    );
    expect(
      screen.getByLabelText("Password").getAttribute("aria-describedby"),
    ).toContain("signup-password-requirements");
    expect(
      document
        .getElementById("signup-password-requirements")
        ?.getAttribute("role"),
    ).toBeNull();
    expect(signUpMock).not.toHaveBeenCalled();
  });

  it("announces the existing password complexity rule only once", () => {
    submitForm({
      Password: "longpassword123",
      "Confirm Password": "longpassword123",
    });

    expectFieldError(
      "Password",
      "Use at least 12 characters with uppercase, lowercase, number, and special character.",
      "signup-password-error",
    );
    expect(
      screen.getByLabelText("Password").getAttribute("aria-describedby"),
    ).toBe("signup-password-error");
    expect(signUpMock).not.toHaveBeenCalled();
  });

  it("rejects mismatched passwords", () => {
    submitForm({ "Confirm Password": "DifferentPassword!123" });

    expectFieldError(
      "Confirm Password",
      "Passwords do not match.",
      "signup-confirm-password-error",
    );
    expect(signUpMock).not.toHaveBeenCalled();
  });

  it("clears a field error and its accessibility attributes when corrected", () => {
    submitForm({ "Email Address": "bad-email" });
    expectFieldError(
      "Email Address",
      "Enter a valid email address.",
      "signup-email-error",
    );

    const email = screen.getByLabelText("Email Address");
    fireEvent.change(email, { target: { value: "avery@example.com" } });

    expect(document.getElementById("signup-email-error")).toBeNull();
    expect(email.getAttribute("aria-invalid")).toBe("false");
    expect(email.getAttribute("aria-describedby")).toBeNull();
    expect(signUpMock).not.toHaveBeenCalled();
  });

  it("calls the registration boundary for a valid form", async () => {
    signUpMock.mockResolvedValueOnce({});
    submitForm();

    await waitFor(() => {
      expect(signUpMock).toHaveBeenCalledWith({
        full_name: "Avery Chen",
        username: "avery.chen",
        email: "avery@example.com",
        password: "SecurePassword!123",
      });
      expect(pushMock).toHaveBeenCalledWith("/");
    });
  });

  it.each([
    ["letters and numbers", "Avery123"],
    ["underscores, periods, and hyphens", "avery_chen.test-user"],
    ["exactly 3 characters", "abc"],
    ["exactly 50 characters", "a".repeat(50)],
  ])("accepts a valid username with %s", async (_description, username) => {
    signUpMock.mockResolvedValueOnce({});
    submitForm({ Username: username });

    await waitFor(() => {
      expect(signUpMock).toHaveBeenCalledWith(
        expect.objectContaining({ username }),
      );
    });
  });
});
