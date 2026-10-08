"use client";

import { useState, type FormEvent } from "react";
import {
  buildProfileUpdate,
  emailChanged,
  profileValuesFrom,
  validateProfile,
  type ProfileErrors,
  type ProfileValues,
} from "@/lib/account-validation";
import {
  AuthApiError,
  updateProfile,
  type AuthUser,
} from "@/lib/services/auth";
import TextField from "./text-field";

export default function ProfileForm({
  user,
  onSaved,
  onCancel,
}: {
  user: AuthUser;
  onSaved: (user: AuthUser) => void;
  onCancel: () => void;
}) {
  const [values, setValues] = useState<ProfileValues>(() =>
    profileValuesFrom(user),
  );
  const [currentPassword, setCurrentPassword] = useState("");
  const [errors, setErrors] = useState<ProfileErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const needsPassword = emailChanged(user, values);

  const set = (field: keyof ProfileValues) => (value: string) =>
    setValues((current) => ({ ...current, [field]: value }));

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);

    const found = validateProfile(user, values, currentPassword);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    const update = buildProfileUpdate(user, values, currentPassword);
    if (!update) {
      setFormError("You haven't changed anything.");
      return;
    }

    setSubmitting(true);
    try {
      onSaved(await updateProfile(update));
    } catch (error) {
      setSubmitting(false);
      if (
        error instanceof AuthApiError &&
        error.status === 400 &&
        update.email
      ) {
        setErrors({ current_password: error.message });
      } else {
        setFormError(
          error instanceof AuthApiError
            ? error.message
            : "Unable to save your changes. Please try again.",
        );
      }
    }
  }

  return (
    <form
      aria-label="Edit personal information"
      onSubmit={handleSubmit}
      noValidate
      className="mt-6 space-y-5"
    >
      {formError && (
        <p
          role="alert"
          className="rounded-lg bg-warning/10 px-4 py-2.5 text-sm font-medium text-warning"
        >
          {formError}
        </p>
      )}

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <TextField
          id="profile-full-name"
          label="Full name"
          required
          autoComplete="name"
          value={values.full_name}
          onChange={set("full_name")}
          error={errors.full_name}
        />
        <TextField
          id="profile-username"
          label="Username"
          required
          autoComplete="username"
          value={values.username}
          onChange={set("username")}
          error={errors.username}
        />
        <TextField
          id="profile-email"
          label="Email"
          type="email"
          required
          autoComplete="email"
          value={values.email}
          onChange={set("email")}
          error={errors.email}
        />
        <TextField
          id="profile-phone"
          label="Phone"
          type="tel"
          autoComplete="tel"
          value={values.phone}
          onChange={set("phone")}
          error={errors.phone}
          hint="Optional. Leave empty to remove it."
        />
      </div>

      <TextField
        id="profile-address"
        label="Address"
        autoComplete="street-address"
        value={values.address}
        onChange={set("address")}
        error={errors.address}
        hint="Optional. Leave empty to remove it."
      />

      {needsPassword && (
        <TextField
          id="profile-current-password"
          label="Current password"
          type="password"
          required
          autoComplete="current-password"
          value={currentPassword}
          onChange={setCurrentPassword}
          error={errors.current_password}
          hint="Needed to change your email."
        />
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={submitting}
          aria-busy={submitting}
          className="rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-70"
        >
          {submitting ? "Saving..." : "Save changes"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={submitting}
          className="rounded-lg border border-line bg-surface px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:border-primary disabled:opacity-70"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
