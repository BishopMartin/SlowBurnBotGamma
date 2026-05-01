const INPUT_CLS =
  "bg-transparent text-[#f4f3ee] placeholder-[#9A968B] outline-none font-mono min-w-0";

export function BracketInput({
  label = "",
  value,
  onChange,
  width = "20ch",
  placeholder = "----",
  type = "text",
  autoComplete,
}: {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  width?: string;
  placeholder?: string;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <span className="inline-flex items-center gap-0 pr-5">
      {label && <span className="text-[#9A968B]">{label}: </span>}
      <span className="text-[#f4f3ee]">[</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        style={{ width, paddingLeft: "1ch", paddingRight: "1ch", boxSizing: "content-box" }}
        className={INPUT_CLS}
      />
      <span className="text-[#f4f3ee]">]</span>
    </span>
  );
}
