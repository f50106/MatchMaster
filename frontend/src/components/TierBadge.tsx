const tierColors: Record<string, string> = {
  A: 'bg-[#4285F4]',
  B: 'bg-[#34A853]',
  C: 'bg-[#FBBC04]',
  D: 'bg-[#FF6D01]',
  F: 'bg-[#EA4335]',
};

const tierTextColors: Record<string, string> = {
  A: 'text-white',
  B: 'text-white',
  C: 'text-gray-900',
  D: 'text-white',
  F: 'text-white',
};

interface Props {
  tier: string;
  score?: number;
  size?: 'sm' | 'lg';
  showScore?: boolean;
}

export default function TierBadge({ tier, score, size = 'sm', showScore = true }: Props) {
  const bg = tierColors[tier] ?? 'bg-gray-400';
  const textColor = tierTextColors[tier] ?? 'text-white';

  if (!showScore || score == null) {
    const pillSize = size === 'lg' ? 'w-10 h-10 text-2xl' : 'w-7 h-7 text-sm';
    return (
      <span className={`inline-flex items-center justify-center rounded-full font-bold ${bg} ${textColor} ${pillSize}`}>
        {tier}
      </span>
    );
  }

  const sizeClass = size === 'lg' ? 'text-2xl px-4 py-2' : 'text-sm px-2 py-0.5';
  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-bold ${bg} ${textColor} ${sizeClass}`}>
      {tier}
      <span className={`font-normal ${tier === 'C' ? 'text-gray-700' : 'text-white/80'}`}>{score.toFixed(1)}</span>
    </span>
  );
}
