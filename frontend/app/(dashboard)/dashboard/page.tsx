'use client';

import { useEffect, useState } from 'react';
import { Thermometer, Droplets, Sprout, Zap, Lightbulb, Activity, AlertTriangle } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useLanguage } from '@/contexts/LanguageContext';
import { Badge } from '@/components/ui/badge';

interface SensorData {
  temperature: number;
  humidity: number;
  soilMoisture: number;
  soilEC: number;
  soilN: number;
  soilP: number;
  soilK: number;
}

interface LampStatus {
  name: string;
  intensity: number;
}

export default function DashboardPage() {
  const { t } = useLanguage();
  const [sensorData, setSensorData] = useState<SensorData>({
    temperature: 0,
    humidity: 0,
    soilMoisture: 0,
    soilEC: 0,
    soilN: 0,
    soilP: 0,
    soilK: 0,
  });
  const [lampStatus, setLampStatus] = useState<LampStatus[]>([]);
  const [piStatus, setPiStatus] = useState<'online' | 'offline' | 'demo'>('demo');
  const [demoMode, setDemoMode] = useState(true);
  const [lastReading, setLastReading] = useState<Date | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch('/api/dashboard');
      if (response.ok) {
        const data = await response.json();
        setSensorData(data.sensors);
        setLampStatus(data.lamps);
        setPiStatus(data.piStatus);
        setDemoMode(data.demoMode);
        setLastReading(new Date(data.lastReading));
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

  // Prevent hydration mismatch
  if (!mounted) {
    return <div className="text-gray-400">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold glow-text">{t.dashboard.title}</h1>
          <p className="text-gray-400 mt-2">
            {t.dashboard.lastReading}: {lastReading ? lastReading.toLocaleTimeString() : '--:--:--'}
          </p>
        </div>
        <div className="flex gap-2">
          <StatusBadge
            status={piStatus}
            label={
              piStatus === 'online'
                ? t.dashboard.online
                : piStatus === 'demo'
                ? t.dashboard.demoMode
                : t.dashboard.offline
            }
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title={t.dashboard.temperature}
          value={sensorData.temperature.toFixed(1)}
          unit="°C"
          icon={Thermometer}
          trend="stable"
        />
        <StatCard
          title={t.dashboard.humidity}
          value={sensorData.humidity.toFixed(0)}
          unit="%"
          icon={Droplets}
          trend="stable"
        />
        <StatCard
          title={t.dashboard.soilMoisture}
          value={sensorData.soilMoisture.toFixed(0)}
          unit="%"
          icon={Sprout}
          trend="stable"
        />
        <StatCard
          title={t.dashboard.soilEC}
          value={sensorData.soilEC.toFixed(2)}
          unit="mS/cm"
          icon={Zap}
          trend="stable"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="glow-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-400">
              <Lightbulb className="w-5 h-5" />
              {t.dashboard.lampStatus}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {lampStatus.map((lamp, index) => (
                <div key={index} className="flex items-center justify-between">
                  <span className="text-gray-300">{lamp.name}</span>
                  <div className="flex items-center gap-3">
                    <div className="w-32 h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all duration-300"
                        style={{ width: `${lamp.intensity}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-400 w-12 text-right">
                      {lamp.intensity}%
                    </span>
                  </div>
                </div>
              ))}
              {lampStatus.length === 0 && (
                <p className="text-gray-500 text-center py-4">No lamps configured</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="glow-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-400">
              <Activity className="w-5 h-5" />
              {t.dashboard.soilNPK}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 rounded-lg bg-green-500/5 border border-green-500/10">
                <p className="text-sm text-gray-400 mb-2">N</p>
                <p className="text-2xl font-bold text-white">{sensorData.soilN}</p>
                <Badge className="mt-2 bg-green-500/20 text-green-400 border-green-500/30">
                  {t.sensors.soilN.split(' ')[0]}
                </Badge>
              </div>
              <div className="text-center p-4 rounded-lg bg-blue-500/5 border border-blue-500/10">
                <p className="text-sm text-gray-400 mb-2">P</p>
                <p className="text-2xl font-bold text-white">{sensorData.soilP}</p>
                <Badge className="mt-2 bg-blue-500/20 text-blue-400 border-blue-500/30">
                  {t.sensors.soilP.split(' ')[0]}
                </Badge>
              </div>
              <div className="text-center p-4 rounded-lg bg-purple-500/5 border border-purple-500/10">
                <p className="text-sm text-gray-400 mb-2">K</p>
                <p className="text-2xl font-bold text-white">{sensorData.soilK}</p>
                <Badge className="mt-2 bg-purple-500/20 text-purple-400 border-purple-500/30">
                  {t.sensors.soilK.split(' ')[0]}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="glow-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-yellow-400">
            <AlertTriangle className="w-5 h-5" />
            {t.dashboard.activeAlerts}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500 text-center py-4">{t.dashboard.noAlerts}</p>
        </CardContent>
      </Card>
    </div>
  );
}
