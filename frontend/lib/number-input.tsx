"use client";

interface NumberInputProps {
  value: number | null | undefined;
  onChange: (value: number) => void;
  placeholder?: string;
  maxLength?: number;
  max?: number;
  className?: string;
}

function parseNum(v: string): number {
  const n = parseInt(v.replace(/[^0-9]/g, ""), 10);
  return isNaN(n) ? 0 : n;
}

export function NumberInput({
  value,
  onChange,
  placeholder = "0",
  maxLength = 2,
  max = 99,
  className = "",
}: NumberInputProps) {
  return (
    <input
      type="text"
      inputMode="numeric"
      value={value != null && value > 0 ? String(value) : ""}
      onChange={(e) => {
        const n = parseNum(e.target.value);
        if (n <= max) onChange(n);
      }}
      placeholder={placeholder}
      maxLength={maxLength}
      style={{ width: `${maxLength}ch`, paddingLeft: "1ch", paddingRight: "1ch", boxSizing: "content-box" }}
      className={`bg-transparent text-[#f4f3ee] outline-none font-mono placeholder-[#9A968B] text-center ${className}`}
    />
  );
}
