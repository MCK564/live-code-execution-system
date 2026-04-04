export default function CodeEditorPanel({ sourceCode, onChange }) {
  return (
    <textarea
      value={sourceCode}
      onChange={(event) => onChange(event.target.value)}
      spellCheck={false}
      className="h-[420px] w-full resize-y rounded-2xl border border-slate-700 bg-slate-950 p-4 font-mono text-sm leading-relaxed text-slate-100 outline-none ring-amber-400 transition focus:ring-2"
      placeholder="Write your code here"
    />
  );
}
