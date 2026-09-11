"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { AuthApiError, signUp } from "@/lib/services/auth";

type FieldErrors = Partial<
  Record<
    "fullName" | "username" | "email" | "password" | "confirmPassword",
    string
  >
>;

const PASSWORD_REQUIREMENTS =
  "Use at least 12 characters with uppercase, lowercase, number, and special character.";

function passwordIsStrong(password: string) {
  return (
    password.length >= 12 &&
    /[a-z]/.test(password) &&
    /[A-Z]/.test(password) &&
    /\d/.test(password) &&
    /[^A-Za-z0-9]/.test(password)
  );
}

export default function SignUpClient() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const errors: FieldErrors = {};
    if (!fullName.trim()) errors.fullName = "Full name is required";
    if (!username.trim()) errors.username = "Username is required";
    if (!email.trim()) errors.email = "Email is required";
    if (!passwordIsStrong(password)) errors.password = PASSWORD_REQUIREMENTS;
    if (password !== confirmPassword) {
      errors.confirmPassword = "Passwords do not match";
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setSubmitting(true);
    try {
      await signUp({
        email,
        username,
        full_name: fullName,
        password,
      });
      window.dispatchEvent(new Event("auth-changed"));
      router.push("/");
    } catch (error) {
      setSubmitting(false);
      setFormError(
        error instanceof AuthApiError
          ? error.message
          : "Unable to create your account. Please try again.",
      );
    }
  }

  return (
    <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-background px-6 py-16">
      <div className="w-full max-w-lg rounded-2xl border border-line bg-surface p-8 shadow-sm">
        <div className="text-center">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-sm font-bold text-white">
            AV
          </span>
          <h1 className="mt-5 text-2xl font-bold tracking-tight text-ink">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-ink-secondary">
            Save AV jobs and build your personalized opportunity list.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-5">
          {formError && (
            <p
              role="alert"
              className="rounded-lg bg-warning/10 px-4 py-2.5 text-sm font-medium text-warning"
            >
              {formError}
            </p>
          )}

          <div className="grid gap-5 sm:grid-cols-2">
            <Field
              id="fullName"
              label="Full Name"
              value={fullName}
              onChange={setFullName}
              autoComplete="name"
              error={fieldErrors.fullName}
            />
            <Field
              id="username"
              label="Username"
              value={username}
              onChange={setUsername}
              autoComplete="username"
              error={fieldErrors.username}
            />
          </div>

          <Field
            id="email"
            label="Email Address"
            type="email"
            value={email}
            onChange={setEmail}
            autoComplete="email"
            error={fieldErrors.email}
          />

          <Field
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            autoComplete="new-password"
            error={fieldErrors.password}
            help={!fieldErrors.password ? PASSWORD_REQUIREMENTS : undefined}
          />

          <Field
            id="confirmPassword"
            label="Confirm Password"
            type="password"
            value={confirmPassword}
            onChange={setConfirmPassword}
            autoComplete="new-password"
            error={fieldErrors.confirmPassword}
          />

          <button
            type="submit"
            disabled={submitting}
            aria-busy={submitting}
            className="w-full rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-70"
          >
            {submitting ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-secondary">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary hover:text-primary-hover"
          >
            Log In
          </Link>
        </p>
      </div>
    </main>
  );
}

function Field({
  id,
  label,
  type = "text",
  value,
  onChange,
  autoComplete,
  error,
  help,
}: {
  id: string;
  label: string;
  type?: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: string;
  error?: string;
  help?: string;
}) {
  const message = error || help;
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        aria-invalid={Boolean(error)}
        aria-describedby={message ? `${id}-message` : undefined}
        className="w-full rounded-lg border border-line bg-surface px-4 py-2.5 text-sm text-ink outline-none placeholder:text-ink-muted focus:border-primary"
      />
      {message && (
        <p
          id={`${id}-message`}
          className={`mt-1.5 text-xs ${error ? "text-warning" : "text-ink-muted"}`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
