export default function CompanyLogo({
  text,
  size = "h-10 w-10",
}: {
  text: string;
  size?: string;
}) {
  return (
    <span
      className={`flex ${size} shrink-0 items-center justify-center rounded-lg bg-ink/10 font-bold text-ink`}
    >
      {text}
    </span>
  );
}
