'use client';

import { useEffect, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend 
} from 'recharts';
import { Loader2, AlertCircle } from 'lucide-react';

export default function HistoryPage() {
  const { t } = useLanguage();
  const [range, setRange] = useState<'24h' | '7d' | '30d'>('24h');
  const [sensorData, setSensorData] = useState<any>(null);
  const [lampData, setLampData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [range]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch Sensor Data
      // We fetch temperature and humidity separately to structure them for the chart
      const tempRes = await fetch(`/api/logs/sensors?type=temperature&hours=${getHours(range)}&limit=1000`);
      const humRes = await fetch(`/api/logs/sensors?type=humidity&hours=${getHours(range)}&limit=1000`);
      
      // Fetch Lamp Data (Channel 1-4)
      const lampRes = await Promise.all([1, 2, 3, 4].map(ch => 
        fetch(`/api/logs/lamps?channel=${ch}&hours=${getHours(range)}&limit=1000`).then(r => r.json())
      ));

      if (tempRes.ok && humRes.ok) {
        const tempData = await tempRes.json();
        const humData = await humRes.json();
        
        // Process Sensor Data: Merge timestamps
        // This is a simplified merge, assuming roughly synced data or using one as base
        // For a perfect chart, we'd align timestamps, but for MVP we'll just map the temperature array
        // and try to find matching humidity, or just display them as is.
        // Better approach for Recharts: Two separate charts or one chart with dual axis if timestamps align.
        // Let's format data for separate charts for clarity.
        
        setSensorData({
          temperature: tempData.readings?.map((r: any) => ({
            time: new Date(r.created_at).getTime(),
            value: r.value,
            formattedTime: new Date(r.created_at).toLocaleString()
          })),
          humidity: humData.readings?.map((r: any) => ({
            time: new Date(r.created_at).getTime(),
            value: r.value,
            formattedTime: new Date(r.created_at).toLocaleString()
          }))
        });
      }

      // Process Lamp Data
      const processedLamps = lampRes.map((data: any, index) => ({
        channel: index + 1,
        data: data.logs?.map((l: any) => ({
          time: new Date(l.created_at).getTime(),
          value: l.intensity,
          formattedTime: new Date(l.created_at).toLocaleString()
        }))
      }));
      setLampData(processedLamps);

    } catch (err) {
      console.error("Failed to fetch history:", err);
      setError("Failed to load history data. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const getHours = (r: string) => {
    switch(r) {
      case '24h': return 24;
      case '7d': return 168;
      case '30d': return 720;
      default: return 24;
    }
  };

  const formatXAxis = (tickItem: number) => {
    const date = new Date(tickItem);
    if (range === '24h') return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-black/90 border border-green-500/30 p-3 rounded-lg shadow-xl backdrop-blur-md">
          <p className="text-gray-300 text-xs mb-2">{new Date(label).toLocaleString()}</p>
          {payload.map((p: any, index: number) => (
            <p key={index} style={{ color: p.color }} className="text-sm font-bold">
              {p.name}: {p.value}{p.unit}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-8 p-6 pb-20">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">
            History Explorer
          </h1>
          <p className="text-gray-400 mt-1">Analyze environmental and lighting trends</p>
        </div>
        
        <Tabs value={range} onValueChange={(v) => setRange(v as any)} className="w-full md:w-auto">
          <TabsList className="grid w-full grid-cols-3 bg-black/40 border border-green-500/20">
            <TabsTrigger value="24h">24 Hours</TabsTrigger>
            <TabsTrigger value="7d">7 Days</TabsTrigger>
            <TabsTrigger value="30d">30 Days</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="h-96 flex flex-col items-center justify-center text-green-500/50 gap-4">
          <Loader2 className="w-12 h-12 animate-spin" />
          <p>Loading historical data...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8">
          
          {/* Environment Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Temperature */}
            <Card className="bg-black/40 border-green-500/20 backdrop-blur-sm overflow-hidden">
              <CardHeader>
                <CardTitle className="text-green-400 flex items-center gap-2">
                  Temperature History
                </CardTitle>
              </CardHeader>
              <CardContent className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sensorData?.temperature}>
                    <defs>
                      <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                    <XAxis 
                      dataKey="time" 
                      tickFormatter={formatXAxis} 
                      stroke="#666" 
                      tick={{fill: '#888', fontSize: 12}}
                      minTickGap={30}
                    />
                    <YAxis stroke="#666" tick={{fill: '#888', fontSize: 12}} domain={['auto', 'auto']} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#22c55e" 
                      fillOpacity={1} 
                      fill="url(#colorTemp)" 
                      name="Temperature"
                      unit="°C"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Humidity */}
            <Card className="bg-black/40 border-blue-500/20 backdrop-blur-sm overflow-hidden">
              <CardHeader>
                <CardTitle className="text-blue-400 flex items-center gap-2">
                  Humidity History
                </CardTitle>
              </CardHeader>
              <CardContent className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={sensorData?.humidity}>
                    <defs>
                      <linearGradient id="colorHum" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                    <XAxis 
                      dataKey="time" 
                      tickFormatter={formatXAxis} 
                      stroke="#666" 
                      tick={{fill: '#888', fontSize: 12}}
                      minTickGap={30}
                    />
                    <YAxis stroke="#666" tick={{fill: '#888', fontSize: 12}} domain={[0, 100]} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#3b82f6" 
                      fillOpacity={1} 
                      fill="url(#colorHum)" 
                      name="Humidity"
                      unit="%"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Lamp Chart */}
          <Card className="bg-black/40 border-yellow-500/20 backdrop-blur-sm overflow-hidden">
            <CardHeader>
              <CardTitle className="text-yellow-400">Lighting Cycles</CardTitle>
            </CardHeader>
            <CardContent className="h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                  <XAxis 
                    dataKey="time" 
                    type="number" 
                    domain={['dataMin', 'dataMax']} 
                    tickFormatter={formatXAxis} 
                    stroke="#666"
                    allowDuplicatedCategory={false}
                    tick={{fill: '#888', fontSize: 12}}
                  />
                  <YAxis stroke="#666" tick={{fill: '#888', fontSize: 12}} domain={[0, 100]} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  
                  {lampData && (
                    <>
                      <Line data={lampData[0].data} type="monotone" dataKey="value" name="Far Red" stroke="#ff4444" dot={false} strokeWidth={2} unit="%" />
                      <Line data={lampData[1].data} type="monotone" dataKey="value" name="Warm White" stroke="#ffbb44" dot={false} strokeWidth={2} unit="%" />
                      <Line data={lampData[2].data} type="monotone" dataKey="value" name="Cool White" stroke="#88ddff" dot={false} strokeWidth={2} unit="%" />
                      <Line data={lampData[3].data} type="monotone" dataKey="value" name="UV" stroke="#cc66ff" dot={false} strokeWidth={2} unit="%" />
                    </>
                  )}
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

        </div>
      )}
    </div>
  );
}
