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

export default function AccountView({ state }: { state: AccountState }) {
  const joined =
    state.status === "success" ? memberSince(state.user.created_at) : null;

  return (
    <main className="mx-auto w-full max-w-[1200px] px-4 py-10 sm:px-6">
      <PageHeader
        title="My Account"
        subtitle="Review the personal information on your account."
      />

      <section
        aria-labelledby="personal-information-heading"
        aria-busy={state.status === "loading"}
        className="mt-8 max-w-3xl rounded-xl border border-line bg-surface p-5 shadow-sm sm:p-8"
      >
        <h2
          id="personal-information-heading"
          className="text-xl font-semibold text-ink"
        >
          Personal Information
        </h2>

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

        {state.status === "success" && joined && (
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
    </main>
  );
}
