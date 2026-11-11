export default function Logo({ className = "brand-mark" }) {
  return (
    <svg className={className} viewBox="0 0 64 64" aria-hidden="true">
      <rect width="64" height="64" rx="14" fill="#1E5A43" />
      <path d="M14 46 L26 32 L34 38 L50 18" stroke="#D99A1E" strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="50" cy="18" r="4" fill="#EEF2EC" />
    </svg>
  );
}
