"use client";

const EMBLEM_BY_TEMPLATE: Record<string, string> = {
  zhou: "/emblems/zhou.svg",
  egypt: "/emblems/egypt.svg",
  sumer: "/emblems/sumer.svg",
  harappa: "/emblems/harappa.svg",
  babylon: "/emblems/babylon.svg",
  greece: "/emblems/greece.svg",
};

export function emblemSrc(templateId: string): string {
  return EMBLEM_BY_TEMPLATE[templateId] ?? "/emblems/placeholder.svg";
}

/** 西周鼎纹：与 public/emblems/zhou.svg 同源线描，内联避免 img 加载闪断。 */
function ZhouDingEmblem({ size }: { size: number }) {
  return (
    <svg
      className="civ-emblem"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M22 14 V8 H26 V14"
        stroke="#c5a55a"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M38 14 V8 H42 V14"
        stroke="#c5a55a"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <rect
        x="16"
        y="14"
        width="32"
        height="4"
        stroke="#c5a55a"
        strokeWidth="1.5"
      />
      <path
        d="M18 18 H46 L44 36 H20 Z"
        stroke="#c5a55a"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <circle cx="26" cy="25" r="2.4" stroke="#c5a55a" strokeWidth="1.2" />
      <circle cx="38" cy="25" r="2.4" stroke="#c5a55a" strokeWidth="1.2" />
      <path
        d="M30 24 L32 28 L34 24"
        stroke="#c5a55a"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path d="M24 30 H40" stroke="#c5a55a" strokeWidth="1" opacity="0.9" />
      <path d="M28 20 H36" stroke="#c5a55a" strokeWidth="1" opacity="0.75" />
      <path
        d="M22 36 L20 54"
        stroke="#c5a55a"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="M32 36 V56"
        stroke="#c5a55a"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="M42 36 L44 54"
        stroke="#c5a55a"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="M17 54 H23"
        stroke="#c5a55a"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M29 56 H35"
        stroke="#c5a55a"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M41 54 H47"
        stroke="#c5a55a"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function CivEmblem({
  templateId,
  civName,
  size = 56,
  className = "",
}: {
  templateId: string;
  civName?: string;
  size?: number;
  className?: string;
}) {
  if (templateId === "zhou") {
    return (
      <span
        className={className}
        role="img"
        aria-label={civName ? `${civName}徽记` : "文明徽记"}
      >
        <ZhouDingEmblem size={size} />
      </span>
    );
  }

  return (
    <img
      className={`civ-emblem ${className}`.trim()}
      src={emblemSrc(templateId)}
      alt={civName ? `${civName}徽记` : "文明徽记"}
      width={size}
      height={size}
      draggable={false}
    />
  );
}
