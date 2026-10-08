/* My Account form rules; mirrors backend/app/schemas/auth.py, which has the
   final say. */

export const MIN_PASSWORD_LENGTH = 12;
export const PASSWORD_REQUIREMENTS =
  "Use at least 12 characters with uppercase, lowercase, number, and special character.";
export const USERNAME_REQUIREMENTS =
  "Username must be 3–50 characters and use only letters, numbers, underscores, periods, or hyphens.";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const USERNAME_PATTERN = /^[A-Za-z0-9_.-]{3,50}$/;
const PHONE_PATTERN = /^\+?[0-9 ()-]{7,32}$/;

export type ProfileValues = {
  full_name: string;
  username: string;
  email: string;
  phone: string;
  address: string;
};

export type ProfileSource = {
  full_name?: string | null;
  username?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
};

/** PATCH /auth/me body; null clears phone or address. */
export type ProfileUpdate = {
  full_name?: string;
  username?: string;
  email?: string;
  phone?: string | null;
  address?: string | null;
  current_password?: string;
};

export type ProfileErrors = Partial<
  Record<keyof ProfileValues | "current_password", string>
>;

export type PasswordErrors = {
  current_password?: string;
  new_password?: string;
  confirm_password?: string;
};

const collapse = (value: string | null | undefined) =>
  (value ?? "").split(/\s+/).filter(Boolean).join(" ");

export function profileValuesFrom(user: ProfileSource): ProfileValues {
  return {
    full_name: user.full_name ?? "",
    username: user.username ?? "",
    email: user.email ?? "",
    phone: user.phone ?? "",
    address: user.address ?? "",
  };
}

// Compared lower-cased and trimmed, like the backend.
export function emailChanged(user: ProfileSource, values: ProfileValues) {
  return (
    values.email.trim().toLowerCase() !==
    (user.email ?? "").trim().toLowerCase()
  );
}

export function validatePassword(password: string): string | undefined {
  if (password.length < MIN_PASSWORD_LENGTH) {
    return `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (
    !/[a-z]/.test(password) ||
    !/[A-Z]/.test(password) ||
    !/\d/.test(password) ||
    !/[^A-Za-z0-9]/.test(password)
  ) {
    return PASSWORD_REQUIREMENTS;
  }
  return undefined;
}

export function validateProfile(
  user: ProfileSource,
  values: ProfileValues,
  currentPassword: string,
): ProfileErrors {
  const errors: ProfileErrors = {};
  const name = collapse(values.full_name);
  const username = values.username.trim();
  const email = values.email.trim();
  const phone = collapse(values.phone);

  if (!name) errors.full_name = "Full name is required.";
  else if (name.length > 120) errors.full_name = "Use 120 characters or fewer.";

  if (!username) errors.username = "Username is required.";
  else if (!USERNAME_PATTERN.test(username))
    errors.username = USERNAME_REQUIREMENTS;

  if (!email) errors.email = "Email is required.";
  else if (!EMAIL_PATTERN.test(email))
    errors.email = "Enter a valid email address.";

  if (phone && !PHONE_PATTERN.test(phone))
    errors.phone = "Enter a valid phone number, for example +61 412 345 678.";

  if (collapse(values.address).length > 500)
    errors.address = "Use 500 characters or fewer.";

  if (!errors.email && emailChanged(user, values) && !currentPassword) {
    errors.current_password =
      "Enter your current password to change your email.";
  }
  return errors;
}

/** Only the changed fields, or null; current_password only with an email change. */
export function buildProfileUpdate(
  user: ProfileSource,
  values: ProfileValues,
  currentPassword: string,
): ProfileUpdate | null {
  const update: ProfileUpdate = {};

  const name = collapse(values.full_name);
  if (name !== collapse(user.full_name)) update.full_name = name;

  const username = values.username.trim();
  if (username.toLowerCase() !== (user.username ?? "").trim().toLowerCase())
    update.username = username;

  if (emailChanged(user, values)) {
    update.email = values.email.trim();
    update.current_password = currentPassword;
  }

  const phone = collapse(values.phone);
  if (phone !== collapse(user.phone)) update.phone = phone || null;

  const address = collapse(values.address);
  if (address !== collapse(user.address)) update.address = address || null;

  return Object.keys(update).length > 0 ? update : null;
}

export function validatePasswordChange(
  currentPassword: string,
  newPassword: string,
  confirmPassword: string,
): PasswordErrors {
  const errors: PasswordErrors = {};
  if (!currentPassword)
    errors.current_password = "Enter your current password.";

  const strength = validatePassword(newPassword);
  if (strength) errors.new_password = strength;
  else if (newPassword === currentPassword)
    errors.new_password = "Choose a password different from the current one.";

  if (!confirmPassword) errors.confirm_password = "Confirm your new password.";
  else if (confirmPassword !== newPassword)
    errors.confirm_password = "The passwords do not match.";
  return errors;
}
