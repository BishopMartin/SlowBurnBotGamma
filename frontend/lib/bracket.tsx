/**
 * Renders [<value>] with brackets always in the base text color
 * and only the inner value taking the provided className for color.
 */
export function Bracket({
  children,
  className = "text-base05",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className="text-base05">
      [<span className={className}>{children}</span>]
    </span>
  );
}
