/** Subtle contour motif — fixed behind content. */
export function TopoBackground() {
  return (
    <svg
      className="pointer-events-none fixed inset-0 -z-10 h-full w-full text-[var(--accent)] opacity-[0.14]"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 1600 600"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden
    >
      <defs>
        <linearGradient id="topoGlow" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.5" />
          <stop offset="55%" stopColor="currentColor" stopOpacity="0.12" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#topoGlow)" opacity="0.35" />
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth="0.35"
        vectorEffect="non-scaling-stroke"
      >
        <path d="M0,180 Q180,120 360,160 T720,140 T1080,180 T1440,120" />
        <path d="M0,220 Q200,260 400,200 T800,240 T1200,200 T1600,260" />
        <path d="M0,320 Q240,280 480,340 T960,300 T1440,360 T1920,300" />
        <path d="M0,420 Q160,480 320,400 T640,440 T960,380 T1280,420" />
        <path d="M-80,520 Q200,460 480,520 T1040,480 T1520,540" />
        <path d="M0,80 Q300,40 600,100 T1200,60 T1800,100" />
      </g>
    </svg>
  );
}
