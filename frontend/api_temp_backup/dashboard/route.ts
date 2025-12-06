import { NextResponse } from 'next/server';
import { getSession } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const zone = await prisma.zone.findFirst({
      where: { userId: session.id },
      select: { id: true },
    });

    if (!zone) {
      return NextResponse.json({ error: 'No zone found' }, { status: 404 });
    }

    const settings = await prisma.settings.findUnique({
      where: { zoneId: zone.id },
      select: { demoMode: true },
    });

    const sensors = await prisma.sensor.findMany({
      where: { zoneId: zone.id },
      select: { id: true, type: true },
    });

    const sensorData: Record<string, number> = {
      temperature: 0,
      humidity: 0,
      soilMoisture: 0,
      soilEC: 0,
      soilN: 0,
      soilP: 0,
      soilK: 0,
    };

    if (sensors) {
      for (const sensor of sensors) {
        const reading = await prisma.sensorReading.findFirst({
          where: { sensorId: sensor.id },
          select: { value: true, createdAt: true },
          orderBy: { createdAt: 'desc' },
        });

        if (reading) {
          sensorData[sensor.type] = reading.value;
        }
      }
    }

    const lamps = await prisma.lampChannel.findMany({
      where: { zoneId: zone.id },
      select: { name: true, curve: true },
      orderBy: { channel: 'asc' },
    });

    const now = new Date();
    const currentTime = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

    const lampStatus = (lamps || []).map((lamp) => {
      const curve = lamp.curve as Array<{ time: string; intensity: number }>;
      let intensity = 0;

      if (curve && curve.length > 0) {
        const sortedCurve = [...curve].sort((a, b) => a.time.localeCompare(b.time));

        for (let i = 0; i < sortedCurve.length; i++) {
          if (currentTime >= sortedCurve[i].time) {
            intensity = sortedCurve[i].intensity;
          } else {
            break;
          }
        }
      }

      return {
        name: lamp.name,
        intensity,
      };
    });

    const piConnection = await prisma.piConnection.findFirst({
      where: { zoneId: zone.id },
      select: { status: true, lastHeartbeat: true },
    });

    let piStatus: 'online' | 'offline' | 'demo' = 'offline';
    if (settings?.demoMode) {
      piStatus = 'demo';
    } else if (piConnection?.status === 'online') {
      piStatus = 'online';
    }

    const lastReading = sensors && sensors.length > 0
      ? (await prisma.sensorReading.findFirst({
          where: { sensorId: sensors[0].id },
          select: { createdAt: true },
          orderBy: { createdAt: 'desc' },
        }))?.createdAt.toISOString() || new Date().toISOString()
      : new Date().toISOString();

    return NextResponse.json({
      sensors: sensorData,
      lamps: lampStatus,
      piStatus,
      demoMode: settings?.demoMode || false,
      lastReading,
    });
  } catch (error) {
    console.error('Dashboard API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
