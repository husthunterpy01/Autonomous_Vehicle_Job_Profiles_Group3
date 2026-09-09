"use client";

import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";
import LoginShowcase from "@/app/login/login-showcase";

const MIN_PASSWORD_LENGTH = 8;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const REGISTRATION_UNAVAILABLE_MESSAGE =
  "Account registration is not available yet. Please try again after the registration service is enabled.";

type FieldErrors = {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
};

type FieldName = keyof FieldErrors;

function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.8}
      stroke="currentColor"
      aria-hidden="true"
    >
      {open ? (
        <>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2.25 12s3.75-7.5 9.75-7.5 9.75 7.5 9.75 7.5-3.75 7.5-9.75 7.5S2.25 12 2.25 12z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z"
          />
        </>
      ) : (
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 3l18 18M10.58 10.58a3 3 0 0 0 4.24 4.24M6.53 6.53C4.34 8 2.25 12 2.25 12s3.75 7.5 9.75 7.5c1.98 0 3.68-.53 5.09-1.35M9.88 4.83A9.7 9.7 0 0 1 12 4.5c6 0 9.75 7.5 9.75 7.5a17.4 17.4 0 0 1-2.7 3.85"
        />
      )}
    </svg>
  );
}

function validateForm(
  name: string,
  email: string,
  password: string,
  confirmPassword: string,
): FieldErrors {
  const errors: FieldErrors = {};
  const trimmedEmail = email.trim();

  if (!name.trim()) {
    errors.name = "Name is required.";
  }

  if (!trimmedEmail) {
    errors.email = "Email is required.";
  } else if (!EMAIL_PATTERN.test(trimmedEmail)) {
    errors.email = "Enter a valid email address.";
  }

  if (!password) {
    errors.password = "Password is required.";
  } else if (password.length < MIN_PASSWORD_LENGTH) {
    errors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }

  if (!confirmPassword) {
    errors.confirmPassword = "Confirm your password.";
  } else if (password !== confirmPassword) {
    errors.confirmPassword = "Passwords do not match.";
  }

  return errors;
}

export default function SignupClient() {
  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const confirmPasswordRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function clearError(field: FieldName) {
    setFieldErrors((currentErrors) => {
      if (!currentErrors[field]) return currentErrors;

      const nextErrors = { ...currentErrors };
      delete nextErrors[field];
      return nextErrors;
    });
    setFormError(null);
  }

  function focusFirstError(errors: FieldErrors) {
    if (errors.name) {
      nameRef.current?.focus();
    } else if (errors.email) {
      emailRef.current?.focus();
    } else if (errors.password) {
      passwordRef.current?.focus();
    } else if (errors.confirmPassword) {
      confirmPasswordRef.current?.focus();
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    setFormError(null);
    const errors = validateForm(name, email, password, confirmPassword);
    setFieldErrors(errors);

    if (Object.keys(errors).length > 0) {
      focusFirstError(errors);
      return;
    }

    setName(name.trim());
    setEmail(email.trim());
    setSubmitting(true);

    try {
      // The backend currently has no registration endpoint. Keep valid form
      // values in place and report the dependency instead of faking success.
      setFormError(REGISTRATION_UNAVAILABLE_MESSAGE);
    } finally {
      setSubmitting(false);
    }
  }

  const inputClassName =
    "w-full rounded-lg border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition-colors placeholder:text-ink-muted focus:border-primary focus:ring-2 focus:ring-primary/20";
  const passwordInputClassName = `${inputClassName} pr-12`;

  return (
    <main className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-2">
      <LoginShowcase />

      <div className="flex items-center justify-center bg-surface px-6 py-12 sm:px-8 sm:py-16">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-ink-secondary">
            Sign up to save jobs and personalize your search.
          </p>

          <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-5">
            {formError && (
              <p
                role="alert"
                className="rounded-lg bg-warning/10 px-4 py-2.5 text-sm font-medium text-warning"
              >
                {formError}
              </p>
            )}

            <div>
              <label
                htmlFor="signup-name"
                className="mb-1.5 block text-sm font-medium text-ink"
              >
                Name
              </label>
              <input
                ref={nameRef}
                id="signup-name"
                name="name"
                type="text"
                required
                autoComplete="name"
                value={name}
                onChange={(event) => {
                  setName(event.target.value);
                  clearError("name");
                }}
                aria-invalid={Boolean(fieldErrors.name)}
                aria-describedby={
                  fieldErrors.name ? "signup-name-error" : undefined
                }
                placeholder="Enter your name"
                className={`${inputClassName} ${
                  fieldErrors.name ? "border-warning" : "border-line"
                }`}
              />
              {fieldErrors.name && (
                <p
                  id="signup-name-error"
                  className="mt-1.5 text-sm text-warning"
                >
                  {fieldErrors.name}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="signup-email"
                className="mb-1.5 block text-sm font-medium text-ink"
              >
                Email Address
              </label>
              <input
                ref={emailRef}
                id="signup-email"
                name="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  clearError("email");
                }}
                aria-invalid={Boolean(fieldErrors.email)}
                aria-describedby={
                  fieldErrors.email ? "signup-email-error" : undefined
                }
                placeholder="Enter email address"
                className={`${inputClassName} ${
                  fieldErrors.email ? "border-warning" : "border-line"
                }`}
              />
              {fieldErrors.email && (
                <p
                  id="signup-email-error"
                  className="mt-1.5 text-sm text-warning"
                >
                  {fieldErrors.email}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="signup-password"
                className="mb-1.5 block text-sm font-medium text-ink"
              >
                Password
              </label>
              <div className="relative">
                <input
                  ref={passwordRef}
                  id="signup-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  required
                  minLength={MIN_PASSWORD_LENGTH}
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value);
                    clearError("password");
                    if (fieldErrors.confirmPassword) {
                      clearError("confirmPassword");
                    }
                  }}
                  aria-invalid={Boolean(fieldErrors.password)}
                  aria-describedby={
                    fieldErrors.password
                      ? "signup-password-requirements signup-password-error"
                      : "signup-password-requirements"
                  }
                  placeholder="Create a password"
                  className={`${passwordInputClassName} ${
                    fieldErrors.password ? "border-warning" : "border-line"
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-ink-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                >
                  <EyeIcon open={showPassword} />
                </button>
              </div>
              <p
                id="signup-password-requirements"
                className="mt-1.5 text-xs text-ink-muted"
              >
                Use at least {MIN_PASSWORD_LENGTH} characters.
              </p>
              {fieldErrors.password && (
                <p
                  id="signup-password-error"
                  className="mt-1.5 text-sm text-warning"
                >
                  {fieldErrors.password}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="signup-confirm-password"
                className="mb-1.5 block text-sm font-medium text-ink"
              >
                Confirm Password
              </label>
              <div className="relative">
                <input
                  ref={confirmPasswordRef}
                  id="signup-confirm-password"
                  name="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  minLength={MIN_PASSWORD_LENGTH}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) => {
                    setConfirmPassword(event.target.value);
                    clearError("confirmPassword");
                  }}
                  aria-invalid={Boolean(fieldErrors.confirmPassword)}
                  aria-describedby={
                    fieldErrors.confirmPassword
                      ? "signup-confirm-password-error"
                      : undefined
                  }
                  placeholder="Re-enter your password"
                  className={`${passwordInputClassName} ${
                    fieldErrors.confirmPassword
                      ? "border-warning"
                      : "border-line"
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword((visible) => !visible)}
                  aria-label={
                    showConfirmPassword
                      ? "Hide confirm password"
                      : "Show confirm password"
                  }
                  aria-pressed={showConfirmPassword}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-ink-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                >
                  <EyeIcon open={showConfirmPassword} />
                </button>
              </div>
              {fieldErrors.confirmPassword && (
                <p
                  id="signup-confirm-password-error"
                  className="mt-1.5 text-sm text-warning"
                >
                  {fieldErrors.confirmPassword}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={submitting}
              aria-busy={submitting}
              className="w-full rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:cursor-not-allowed disabled:opacity-70"
            >
              {submitting ? "Signing up..." : "Sign Up"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-ink-secondary">
            Already have an account?{" "}
            <Link
              href="/login"
              className="rounded-sm font-medium text-primary hover:text-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            >
              Log in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
