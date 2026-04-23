"use client";

import { useState, useRef, useEffect } from "react";

interface DropdownOption {
  value: string;
  label: string;
}

interface DropdownProps {
  value: string;
  options: DropdownOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function Dropdown({
  value,
  options,
  onChange,
  placeholder = "—",
  disabled = false,
  className = "",
}: DropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const selected = options.find((o) => o.value === value);
  const display = selected?.label ?? placeholder;

  return (
    <div ref={ref} className={`relative inline-block font-mono ${className}`}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => !disabled && setOpen((o) => !o)}
        className={`bg-transparent outline-none cursor-pointer text-[#B1ADA1] ${disabled ? "text-[#3d3d3a] cursor-default" : ""}`}
      >
        {display}
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1 z-50 border border-[#3d3d3a] bg-[#1f1e1d] min-w-max text-left">
          {options.map((opt) => (
            <div
              key={opt.value}
              onClick={() => { onChange(opt.value); setOpen(false); }}
              className={`px-3 py-1 cursor-pointer transition-colors ${
                opt.value === value
                  ? "bg-[#d97757] text-[#141413]"
                  : "text-[#f4f3ee] hover:bg-[#2a2927]"
              }`}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
