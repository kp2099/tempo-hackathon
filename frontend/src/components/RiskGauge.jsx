/**
 * Circular risk gauge component.
 * Visually shows risk level with color-coded arc.
 */
export default function RiskGauge({ score = 0, size = 100 }) {
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = score * circumference;

  const getColor = (s) => {
    if (s < 0.3) return { stroke: '#10b981', text: 'text-green-400', label: 'LOW' };
    if (s < 0.7) return { stroke: '#f59e0b', text: 'text-yellow-400', label: 'MED' };
    return { stroke: '#ef4444', text: 'text-red-400', label: 'HIGH' };
  };

  const config = getColor(score);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#334155"
          strokeWidth="6"
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={config.stroke}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          style={{ transition: 'stroke-dashoffset 0.5s ease' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-lg font-bold ${config.text}`}>
          {(score * 100).toFixed(0)}%
        </span>
        <span className={`text-[9px] font-medium ${config.text} opacity-80`}>
          {config.label}
        </span>
      </div>
    </div>
  );
}

