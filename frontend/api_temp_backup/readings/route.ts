import { NextResponse } from 'next/server';
import { getSession } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const range = searchParams.get('range') || '24h';

    // Get user's zone
    const zone = await prisma.zone.findFirst({
      where: { userId: session.id },
    });

    if (!zone) {
      return NextResponse.json({ error: 'No zone found' }, { status: 404 });
    }

    // Calculate time range
    const rangeMinutes: Record<string, number> = {
      '1h': 60,
      '24h': 1440,
      '7d': 10080,
      '30d': 43200,
    };

    const minutes = rangeMinutes[range] || 1440;
    const since = new Date(Date.now() - minutes * 60 * 1000);

    // Get all sensors for this zone
    const sensors = await prisma.sensor.findMany({
      where: { zoneId: zone.id },
      select: { id: true, type: true },
    });

    const sensorData: Record<string, Array<{ timestamp: string; value: number }>> = {};

    // Fetch readings for each sensor
    for (const sensor of sensors) {
      const readings = await prisma.sensorReading.findMany({
        where: {
          sensorId: sensor.id,
          createdAt: { gte: since },
        },
        select: {
          value: true,
          createdAt: true,
        },
        orderBy: { createdAt: 'asc' },
      });

      sensorData[sensor.type] = readings.map((r) => ({
        timestamp: r.createdAt.toISOString(),
        value: r.value,
      }));
    }

    return NextResponse.json(sensorData);
  } catch (error) {
    console.error('Readings API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
