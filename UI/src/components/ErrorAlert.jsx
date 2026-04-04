export default function ErrorAlert({ error }) {
  if (!error) return null;

  return (
    <div className="rounded-2xl border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200">
      {error}
    </div>
  );
}
