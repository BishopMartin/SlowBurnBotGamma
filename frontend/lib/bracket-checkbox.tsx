import { Bracket } from "@/lib/bracket";

export function BracketCheckbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <span className="inline-flex items-center gap-1">
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className="group cursor-pointer transition-colors"
      >
        <Bracket
          className={
            checked
              ? "text-status-ok group-hover:text-status-bad"
              : "text-[#9A968B] group-hover:text-status-ok"
          }
        >
          {checked ? "x" : " "}
        </Bracket>
      </button>
      <span className="text-[#9A968B]">{label}</span>
    </span>
  );
}
