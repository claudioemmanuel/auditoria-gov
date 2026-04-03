import { clsx } from "clsx";

type LogoSize = "sm" | "md" | "lg";

const sizeMap: Record<LogoSize, number> = {
  sm: 28,
  md: 32,
  lg: 40,
};

interface OpenWatchLogoMarkProps {
  size?: LogoSize;
  className?: string;
}

export function OpenWatchLogoMark({ size = "md", className }: OpenWatchLogoMarkProps) {
  const px = sizeMap[size];

  return (
    <span
      className={clsx("inline-flex items-center justify-center rounded-xl ow-brand-mark", className)}
      style={{ width: px, height: px }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 64 64" width={px} height={px} fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="27" cy="27" r="19" stroke="var(--color-text)" strokeWidth="3.5" opacity="0.95" />
        <circle cx="27" cy="27" r="15.5" stroke="var(--color-brand)" strokeWidth="2.5" opacity="0.9" />

        <path
          d="M18 22.5L22 18.5H28L31 15L34 17L33 21H39L44 23L47 28L44 34L40 35L37 39H31L27 45L24 40L21 39L18 34L14 31L15 26L18 22.5Z"
          stroke="var(--color-text)"
          strokeWidth="2.2"
          strokeLinejoin="round"
          fill="var(--color-brand-dim)"
          fillOpacity="0.9"
        />

        <path
          d="M22 28C24 25.5 27 24 30 24C34.2 24 38.2 26.4 40.8 30"
          stroke="var(--color-brand-light)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeDasharray="1.5 3"
          opacity="0.95"
        />
        <path
          d="M21 34.2C24 32 28 31 31.8 31C34.8 31 37.8 31.6 40.6 33.2"
          stroke="var(--color-brand-light)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeDasharray="1.5 3"
          opacity="0.9"
        />

        {[
          { x: 22, y: 30 },
          { x: 31, y: 23.5 },
          { x: 39, y: 31.5 },
        ].map((node) => (
          <g key={`${node.x}-${node.y}`}>
            <circle cx={node.x} cy={node.y} r="2.2" fill="var(--color-brand-light)" />
            <path d={`M ${node.x - 3.8} ${node.y - 5.2} q 3.8 -3.2 7.6 0`} stroke="var(--color-text)" strokeWidth="1.5" strokeLinecap="round" opacity="0.9" />
            <path d={`M ${node.x - 2.3} ${node.y - 2.8} q 2.3 -1.8 4.6 0`} stroke="var(--color-text)" strokeWidth="1.3" strokeLinecap="round" opacity="0.9" />
          </g>
        ))}

        <path d="M41 41L54 54" stroke="var(--color-text)" strokeWidth="4.5" strokeLinecap="round" />
        <path d="M44 44L56 56" stroke="var(--color-brand)" strokeWidth="2.5" strokeLinecap="round" opacity="0.95" />
      </svg>
    </span>
  );
}

interface OpenWatchLogoProps {
  size?: LogoSize;
  className?: string;
  showWordmark?: boolean;
}

export function OpenWatchLogo({ size = "md", className, showWordmark = true }: OpenWatchLogoProps) {
  return (
    <span className={clsx("inline-flex items-center gap-2.5", className)}>
      <OpenWatchLogoMark size={size} />
      {showWordmark && <span className="ow-sidebar-wordmark">OpenWatch</span>}
    </span>
  );
}
