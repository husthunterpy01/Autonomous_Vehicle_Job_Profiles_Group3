import type { ReactNode } from "react";
import PageHeader from "@/components/ui/PageHeader";
import type { AuthUser } from "@/lib/services/auth";

export type AccountState =
  | { status: "loading" }
  | { status: "success"; user: AuthUser }
  | { status: "error" };

function displayText(value: unknown): string {
  return typeof value === "string" && value.trim()
    ? value.trim()
    : "Not provided";
}

function memberSince(value: unknown): { label: string; dateTime?: string } {
  if (typeof value !== "string" || !value.trim()) {
    return { label: "Not provided" };
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { label: "Not provided" };
  }

  return {
    label: new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      timeZone: "UTC",
    }).format(date),
    dateTime: date.toISOString(),
  };
}

export default function AccountView({
  state,
  onEdit,
  editor,
  notice,
  children,
}: {
  state: AccountState;
  /** Shows the Edit button. */
  onEdit?: () => void;
  /** Replaces the read-only details while the profile is being edited. */
  editor?: ReactNode;
  /** A confirmation shown above the details, such as "Saved". */
  notice?: string | null;
  /** Extra sections below the personal information. */
  children?: ReactNode;
}) {
  const joined =
    state.status === "success" ? memberSince(state.user.created_at) : null;

  return (
    <main className="mx-auto w-full max-w-[1200px] px-4 py-10 sm:px-6">
      <PageHeader
        title="My Account"
        subtitle="Review and update the personal information on your account."
      />

      <section
        aria-labelledby="personal-information-heading"
        aria-busy={state.status === "loading"}
        className="mt-8 max-w-3xl rounded-xl border border-line bg-surface p-5 shadow-sm sm:p-8"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2
            id="personal-information-heading"
            className="text-xl font-semibold text-ink"
          >
            Personal Information
          </h2>
          {state.status === "success" && onEdit && !editor && (
            <button
              type="button"
              onClick={onEdit}
              className="rounded-lg border border-line bg-surface px-4 py-2 text-sm font-medium text-ink transition-colors hover:border-primary"
            >
              Edit information
            </button>
          )}
        </div>

        {notice && (
          <p
            role="status"
            className="mt-4 rounded-lg bg-success/10 px-4 py-2.5 text-sm font-medium text-success"
          >
            {notice}
          </p>
        )}

        {state.status === "loading" && (
          <p role="status" className="mt-6 text-sm text-ink-secondary">
            Loading your information…
          </p>
        )}

        {state.status === "error" && (
          <p role="alert" className="mt-6 text-sm text-ink-secondary">
            Unable to load your information
          </p>
        )}

        {state.status === "success" && editor}

        {state.status === "success" && joined && !editor && (
          <dl className="mt-6 grid grid-cols-1 gap-x-8 sm:grid-cols-2">
            <div className="min-w-0 border-t border-line py-4">
              <dt className="text-sm font-medium text-ink-secondary">
                Full name
              </dt>
              <dd className="mt-1 break-all text-base text-ink">
                {displayText(state.user.full_name)}
              </dd>
            </div>
            <div className="min-w-0 border-t border-line py-4">
              <dt className="text-sm font-medium text-ink-secondary">
                Username
              </dt>
              <dd className="mt-1 break-all text-base text-ink">
                {displayText(state.user.username)}
              </dd>
            </div>
            <div className="min-w-0 border-t border-line py-4">
              <dt className="text-sm font-medium text-ink-secondary">Email</dt>
              <dd className="mt-1 break-all text-base text-ink">
                {displayText(state.user.email)}
              </dd>
            </div>
            <div className="min-w-0 border-t border-line py-4">
              <dt className="text-sm font-medium text-ink-secondary">Phone</dt>
              <dd className="mt-1 break-all text-base text-ink">
                {displayText(state.user.phone)}
              </dd>
            </div>
            <div className="min-w-0 border-t border-line py-4">
              <dt className="text-sm font-medium text-ink-secondary">
                Address
              </dt>
              <dd className="mt-1 break-words text-base text-ink">
                {displayText(state.user.address)}
              </dd>
            </div>
            <div className="min-w-0 border-t border-line py-4">
              <dt className="text-sm font-medium text-ink-secondary">
                Member since
              </dt>
              <dd className="mt-1 text-base text-ink">
                {joined.dateTime ? (
                  <time dateTime={joined.dateTime}>{joined.label}</time>
                ) : (
                  joined.label
                )}
              </dd>
            </div>
          </dl>
        )}
      </section>

      {state.status === "success" && children}
    </main>
  );
}
