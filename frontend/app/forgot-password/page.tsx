import Link from "next/link";

export default function ForgotPasswordPage() {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-sm flex-col justify-center px-6 py-16 text-center">
      <h1 className="text-2xl font-bold tracking-tight text-ink">
        Password recovery
      </h1>
      <p className="mt-3 text-sm text-ink-secondary">
        Password recovery isn&apos;t available yet — this page is a placeholder
        until the account system is built.
      </p>
      <Link
        href="/login"
        className="mt-8 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-hover"
      >
        Back to Login
      </Link>
    </div>
  );
}
