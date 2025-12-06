'use client';

import { useEffect, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Lightbulb, Save, RotateCcw, Power, PowerOff, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

interface CurvePoint {
  time: string;
  intensity: number;
}

interface LampChannel {
  id: string;
  name: string;
  channel: number;
  curve: CurvePoint[];
}

export default function LightingPage() {
  const { t } = useLanguage();
  const [lamps, setLamps] = useState<LampChannel[]>([]);
  const [editedLamps, setEditedLamps] = useState<LampChannel[]>([]);
  const [activeLamp, setActiveLamp] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchLamps();
  }, []);

  const fetchLamps = async () => {
    try {
      const response = await fetch('/api/lighting');
      if (response.ok) {
        const data = await response.json();
        setLamps(data.lamps);
        setEditedLamps(JSON.parse(JSON.stringify(data.lamps))); // Deep copy
        if (data.lamps.length > 0) {
          setActiveLamp(data.lamps[0].id);
        }
      }
    } catch (error) {
      console.error('Failed to fetch lamps:', error);
      toast.error(t.common.error || 'Failed to load lamps');
    } finally {
      setLoading(false);
    }
  };

  const handleCurvePointChange = (lampId: string, pointIndex: number, field: 'time' | 'intensity', value: string | number) => {
    setEditedLamps(prev => prev.map(lamp => {
      if (lamp.id === lampId) {
        const newCurve = [...lamp.curve];
        if (field === 'time') {
          newCurve[pointIndex].time = value as string;
        } else {
          const intensity = Math.max(0, Math.min(100, Number(value)));
          newCurve[pointIndex].intensity = intensity;
        }
        return { ...lamp, curve: newCurve };
      }
      return lamp;
    }));
  };

  const handleAddPoint = (lampId: string) => {
    setEditedLamps(prev => prev.map(lamp => {
      if (lamp.id === lampId) {
        const lastPoint = lamp.curve[lamp.curve.length - 1];
        const newPoint: CurvePoint = {
          time: lastPoint?.time || '12:00',
          intensity: 50
        };
        return { ...lamp, curve: [...lamp.curve, newPoint] };
      }
      return lamp;
    }));
  };

  const handleRemovePoint = (lampId: string, pointIndex: number) => {
    setEditedLamps(prev => prev.map(lamp => {
      if (lamp.id === lampId && lamp.curve.length > 1) {
        const newCurve = lamp.curve.filter((_, index) => index !== pointIndex);
        return { ...lamp, curve: newCurve };
      }
      return lamp;
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const currentLamp = editedLamps.find(l => l.id === activeLamp);
      if (!currentLamp) return;

      const response = await fetch('/api/lighting', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lampId: currentLamp.id,
          curve: currentLamp.curve
        }),
      });

      if (response.ok) {
        toast.success(t.lighting.save + '!');
        await fetchLamps(); // Reload to sync with server
      } else {
        toast.error(t.common.error || 'Failed to save');
      }
    } catch (error) {
      console.error('Failed to save curve:', error);
      toast.error(t.common.error || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    const originalLamp = lamps.find(l => l.id === activeLamp);
    if (originalLamp) {
      setEditedLamps(prev => prev.map(lamp =>
        lamp.id === activeLamp
          ? JSON.parse(JSON.stringify(originalLamp))
          : lamp
      ));
      toast.success(t.lighting.reset + '!');
    }
  };

  const handleAllOn = async () => {
    try {
      const response = await fetch('/api/lighting/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'all_on' }),
      });

      if (response.ok) {
        toast.success(t.lighting.allOn + '!');
        fetchLamps();
      } else {
        toast.error(t.common.error);
      }
    } catch (error) {
      console.error('Failed to turn on lamps:', error);
      toast.error(t.common.error);
    }
  };

  const handleAllOff = async () => {
    try {
      const response = await fetch('/api/lighting/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'all_off' }),
      });

      if (response.ok) {
        toast.success(t.lighting.allOff + '!');
        fetchLamps();
      } else {
        toast.error(t.common.error);
      }
    } catch (error) {
      console.error('Failed to turn off lamps:', error);
      toast.error(t.common.error);
    }
  };

  const currentLamp = editedLamps.find((l) => l.id === activeLamp);

  if (loading) {
    return <div className="text-gray-400">{t.common.loading || 'Loading...'}</div>;
  }

  if (lamps.length === 0) {
    return (
      <div className="space-y-6">
        <h1 className="text-4xl font-bold glow-text">{t.lighting.title}</h1>
        <Card className="glow-card">
          <CardContent className="py-8">
            <p className="text-gray-500 text-center">{t.lighting.noLamps || 'No lamps configured'}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-bold glow-text">{t.lighting.title}</h1>
        <div className="flex gap-2">
          <Button onClick={handleAllOn} className="bg-green-600 hover:bg-green-700">
            <Power className="w-4 h-4 mr-2" />
            {t.lighting.allOn}
          </Button>
          <Button onClick={handleAllOff} variant="outline" className="border-red-500/20 text-red-400 hover:bg-red-500/10">
            <PowerOff className="w-4 h-4 mr-2" />
            {t.lighting.allOff}
          </Button>
        </div>
      </div>

      <Card className="glow-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-400">
            <Lightbulb className="w-5 h-5" />
            {t.lighting.curveEditor}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeLamp} onValueChange={setActiveLamp}>
            <TabsList className="mb-6">
              {editedLamps.map((lamp) => (
                <TabsTrigger key={lamp.id} value={lamp.id}>
                  {lamp.name}
                </TabsTrigger>
              ))}
            </TabsList>

            {editedLamps.map((lamp) => (
              <TabsContent key={lamp.id} value={lamp.id}>
                <div className="space-y-6">
                  <div className="bg-black/40 rounded-lg p-6 border border-green-500/20">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-medium text-gray-400">
                        {t.lighting.time} / {t.lighting.intensity}
                      </h3>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-green-500/20"
                        onClick={() => handleAddPoint(lamp.id)}
                      >
                        <Plus className="w-4 h-4 mr-1" />
                        {t.lighting.addPoint || 'Add Point'}
                      </Button>
                    </div>
                    <div className="space-y-2">
                      {lamp.curve.map((point, index) => (
                        <div key={index} className="flex items-center gap-4">
                          <Input
                            type="time"
                            value={point.time}
                            onChange={(e) => handleCurvePointChange(lamp.id, index, 'time', e.target.value)}
                            className="w-32 bg-black/50 border-green-500/20"
                          />
                          <Input
                            type="number"
                            value={point.intensity}
                            min="0"
                            max="100"
                            onChange={(e) => handleCurvePointChange(lamp.id, index, 'intensity', e.target.value)}
                            className="w-24 bg-black/50 border-green-500/20"
                          />
                          <span className="text-gray-400">%</span>
                          <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-green-500 to-green-400 transition-all"
                              style={{ width: `${point.intensity}%` }}
                            />
                          </div>
                          {lamp.curve.length > 1 && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                              onClick={() => handleRemovePoint(lamp.id, index)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      onClick={handleSave}
                      className="bg-green-600 hover:bg-green-700"
                      disabled={saving}
                    >
                      <Save className="w-4 h-4 mr-2" />
                      {saving ? (t.common.saving || 'Saving...') : t.lighting.save}
                    </Button>
                    <Button
                      variant="outline"
                      className="border-green-500/20"
                      onClick={handleReset}
                      disabled={saving}
                    >
                      <RotateCcw className="w-4 h-4 mr-2" />
                      {t.lighting.reset}
                    </Button>
                  </div>
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
