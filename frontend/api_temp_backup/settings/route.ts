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
    });

    if (settings) {
      // Map camelCase to snake_case for frontend compatibility
      return NextResponse.json({
        demo_mode: settings.demoMode,
        sensor_interval: settings.sensorInterval,
        language: settings.language,
        theme: settings.theme,
      });
    }

    return NextResponse.json({
      demo_mode: true,
      sensor_interval: 60,
      language: 'de',
      theme: 'dark',
    });
  } catch (error) {
    console.error('Settings API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();

    const zone = await prisma.zone.findFirst({
      where: { userId: session.id },
      select: { id: true },
    });

    if (!zone) {
      return NextResponse.json({ error: 'No zone found' }, { status: 404 });
    }

    // Map snake_case to camelCase for Prisma
    const mappedData: {
      demoMode?: boolean;
      sensorInterval?: number;
      language?: string;
      theme?: string;
    } = {};
    if ('demo_mode' in body) mappedData.demoMode = body.demo_mode;
    if ('sensor_interval' in body) mappedData.sensorInterval = body.sensor_interval;
    if ('language' in body) mappedData.language = body.language;
    if ('theme' in body) mappedData.theme = body.theme;

    await prisma.settings.upsert({
      where: { zoneId: zone.id },
      update: mappedData,
      create: {
        zoneId: zone.id,
        ...mappedData,
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Settings update error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
