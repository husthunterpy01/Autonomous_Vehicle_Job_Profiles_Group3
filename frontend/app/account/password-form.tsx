"use client";

import { useState, type FormEvent } from "react";
import {
  PASSWORD_REQUIREMENTS,
  validatePasswordChange,
  type PasswordErrors,
} from "@/lib/account-validation";
import { AuthApiError, changePassword } from "@/lib/services/auth";
import TextField from "./text-field";

export default function PasswordForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<PasswordErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    setDone(false);

    const found = validatePasswordChange(current, next, confirm);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      await changePassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      setDone(true);
    } catch (error) {
      if (error instanceof AuthApiError && error.status === 400) {
        // "Current password is incorrect" or "New password must be different".
        setErrors(
          error.message.startsWith("Current")
            ? { current_password: error.message }
            : { new_password: error.message },
        );
      } else {
        setFormError(
          error instanceof AuthApiError
            ? error.message
            : "Unable to change your password. Please try again.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section
      aria-labelledby="change-password-heading"
      className="mt-8 max-w-3xl rounded-xl border border-line bg-surface p-5 shadow-sm sm:p-8"
    >
      <h2
        id="change-password-heading"
        className="text-xl font-semibold text-ink"
      >
        Change password
      </h2>

      {done && (
        <p
          role="status"
          className="mt-4 rounded-lg bg-emerald-50 px-4 py-2.5 text-sm font-medium text-emerald-800"
        >
          Your password has been updated.
        </p>
      )}

      <form
        aria-labelledby="change-password-heading"
        onSubmit={handleSubmit}
        noValidate
        className="mt-6 space-y-5"
      >
        {formError && (
          <p
            role="alert"
            className="rounded-lg bg-amber-50 px-4 py-2.5 text-sm font-medium text-amber-800"
          >
            {formError}
          </p>
        )}
        <TextField
          id="password-current"
          label="Current password"
          type="password"
          required
          autoComplete="current-password"
          value={current}
          onChange={setCurrent}
          error={errors.current_password}
        />
        <TextField
          id="password-new"
          label="New password"
          type="password"
          required
          autoComplete="new-password"
          value={next}
          onChange={setNext}
          error={errors.new_password}
          hint={PASSWORD_REQUIREMENTS}
        />
        <TextField
          id="password-confirm"
          label="Confirm new password"
          type="password"
          required
          autoComplete="new-password"
          value={confirm}
          onChange={setConfirm}
          error={errors.confirm_password}
        />
        <button
          type="submit"
          disabled={submitting}
          aria-busy={submitting}
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-70"
        >
          {submitting ? "Updating..." : "Update password"}
        </button>
      </form>
    </section>
  );
}
