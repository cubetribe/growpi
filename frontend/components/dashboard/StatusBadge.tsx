'use client';

interface StatusBadgeProps {
  status: 'online' | 'offline' | 'demo';
  label: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const getStyles = () => {
    switch (status) {
      case 'online':
        return 'bg-green-500/20 border-green-500/40 text-green-400';
      case 'offline':
        return 'bg-red-500/20 border-red-500/40 text-red-400';
      case 'demo':
        return 'bg-blue-500/20 border-blue-500/40 text-blue-400';
    }
  };

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border ${getStyles()}`}>
      <div className={`w-2 h-2 rounded-full ${status === 'online' ? 'bg-green-500 animate-pulse' : status === 'demo' ? 'bg-blue-500 animate-pulse' : 'bg-red-500'}`} />
      <span className="text-sm font-medium">{label}</span>
    </div>
  );
}
