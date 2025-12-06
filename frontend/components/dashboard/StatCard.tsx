'use client';

import { LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon: LucideIcon;
  trend?: 'up' | 'down' | 'stable';
  className?: string;
}

export function StatCard({ title, value, unit, icon: Icon, trend, className = '' }: StatCardProps) {
  const getTrendColor = () => {
    if (!trend) return '';
    return trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : 'text-gray-400';
  };

  const getTrendSymbol = () => {
    if (!trend) return '';
    return trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→';
  };

  return (
    <Card className={`glow-card glow-card-hover overflow-hidden ${className}`}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm text-gray-400">{title}</p>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white">
                {value}
              </span>
              {unit && (
                <span className="text-lg text-gray-400">{unit}</span>
              )}
              {trend && (
                <span className={`text-lg ${getTrendColor()}`}>
                  {getTrendSymbol()}
                </span>
              )}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
            <Icon className="w-6 h-6 text-green-500" />
          </div>
        </div>
        <div className="mt-4 h-1 bg-gradient-to-r from-green-500/20 to-transparent rounded-full" />
      </CardContent>
    </Card>
  );
}
