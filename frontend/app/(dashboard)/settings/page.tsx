'use client';

import { useEffect, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Settings as SettingsIcon, Save, Moon, Sun } from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
  const { t, language, setLanguage } = useLanguage();
  const [demoMode, setDemoMode] = useState(true);
  const [sensorInterval, setSensorInterval] = useState(60);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    // Apply theme to document
    if (theme === 'light') {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    } else {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    }
  }, [theme]);

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/settings');
      if (response.ok) {
        const data = await response.json();
        setDemoMode(data.demo_mode);
        setSensorInterval(data.sensor_interval);
        setTheme(data.theme || 'dark');
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    // Validate sensor interval
    if (sensorInterval < 5 || sensorInterval > 3600) {
      toast.error(t.common.intervalError);
      return;
    }

    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          demo_mode: demoMode,
          sensor_interval: sensorInterval,
          language,
          theme,
        }),
      });

      if (response.ok) {
        toast.success(t.settings.saved);
      } else {
        toast.error(t.common.error);
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast.error(t.common.error);
    }
  };

  if (loading) {
    return <div className="text-gray-400">{t.common.loading}</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-4xl font-bold glow-text">{t.settings.title}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="glow-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-400">
              <SettingsIcon className="w-5 h-5" />
              {t.settings.general}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <Label htmlFor="language" className="text-gray-300">
                {t.settings.language}
              </Label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as any)}
                className="bg-black/50 border border-green-500/20 rounded px-3 py-2 text-white"
              >
                <option value="de">Deutsch</option>
                <option value="en">English</option>
              </select>
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="demo-mode" className="text-gray-300">
                {t.settings.demoMode}
              </Label>
              <Switch
                id="demo-mode"
                checked={demoMode}
                onCheckedChange={setDemoMode}
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="theme" className="text-gray-300 flex items-center gap-2">
                {theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                Theme
              </Label>
              <Switch
                id="theme"
                checked={theme === 'light'}
                onCheckedChange={(checked) => setTheme(checked ? 'light' : 'dark')}
              />
            </div>
          </CardContent>
        </Card>

        <Card className="glow-card">
          <CardHeader>
            <CardTitle className="text-green-400">
              {t.settings.sensorConfig}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="interval" className="text-gray-300">
                {t.settings.readingInterval}
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="interval"
                  type="number"
                  min="5"
                  max="3600"
                  value={sensorInterval}
                  onChange={(e) => setSensorInterval(Number(e.target.value))}
                  className="bg-black/50 border-green-500/20"
                />
                <span className="text-gray-400">{t.settings.seconds}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave} className="bg-green-600 hover:bg-green-700">
          <Save className="w-4 h-4 mr-2" />
          {t.settings.save}
        </Button>
      </div>
    </div>
  );
}
