/**
 * Brand mark — a precise geometric monogram.
 * A square frame with an inscribed Q-stem. Renders cleanly at any size.
 * No flourishes, no SVG illustration.
 */
export function Mark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <rect
        x="2.5"
        y="2.5"
        width="19"
        height="19"
        rx="3"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <circle
        cx="10"
        cy="12"
        r="3.5"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <path
        d="M12.2 14.4L15 17.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}
