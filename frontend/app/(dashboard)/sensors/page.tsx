'use client';

import { useEffect, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface SensorReading {
  timestamp: string;
  value: number;
}

const sensorTypes = [
  { type: 'temperature', label: 'Temperature', unit: '°C' },
  { type: 'humidity', label: 'Humidity', unit: '%' },
  { type: 'soilMoisture', label: 'Soil Moisture', unit: '%' },
  { type: 'soilTemp', label: 'Soil Temperature', unit: '°C' },
  { type: 'soilPH', label: 'Soil pH', unit: 'pH' },
  { type: 'soilEC', label: 'Soil EC', unit: 'mS/cm' },
  { type: 'soilN', label: 'Nitrogen (N)', unit: 'ppm' },
  { type: 'soilP', label: 'Phosphorus (P)', unit: 'ppm' },
  { type: 'soilK', label: 'Potassium (K)', unit: 'ppm' },
];

export default function SensorsPage() {
  const { t } = useLanguage();
  const [range, setRange] = useState<'1h' | '24h' | '7d'>('24h');
  const [sensorData, setSensorData] = useState<Record<string, SensorReading[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSensorData();
  }, [range]);

  const fetchSensorData = async () => {
    try {
      const response = await fetch(`/api/readings?range=${range}`);
      if (response.ok) {
        const data = await response.json();
        setSensorData(data);
      }
    } catch (error) {
      console.error('Failed to fetch sensor data:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-bold glow-text">{t.sensors.title}</h1>
        <Tabs value={range} onValueChange={(v) => setRange(v as any)}>
          <TabsList>
            <TabsTrigger value="1h">{t.sensors['1h']}</TabsTrigger>
            <TabsTrigger value="24h">{t.sensors['24h']}</TabsTrigger>
            <TabsTrigger value="7d">{t.sensors['7d']}</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {sensorTypes.map((sensor) => (
          <Card key={sensor.type} className="glow-card">
            <CardHeader>
              <CardTitle className="text-green-400 text-lg">
                {sensor.label} ({sensor.unit})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  {t.common.loading}
                </div>
              ) : sensorData[sensor.type] && sensorData[sensor.type].length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={sensorData[sensor.type]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis
                      dataKey="timestamp"
                      stroke="#6b7280"
                      tick={{ fill: '#9ca3af' }}
                      tickFormatter={(time) => new Date(time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    />
                    <YAxis stroke="#6b7280" tick={{ fill: '#9ca3af' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#111827',
                        border: '1px solid rgba(34, 197, 94, 0.2)',
                        borderRadius: '8px',
                      }}
                      labelStyle={{ color: '#9ca3af' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#22c55e"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  {t.sensors.noData}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
