import { NextResponse } from 'next/server';
import { getSession } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { action } = body;

    if (!action || !['all_on', 'all_off'].includes(action)) {
      return NextResponse.json(
        { error: 'Invalid action. Must be "all_on" or "all_off"' },
        { status: 400 }
      );
    }

    const zone = await prisma.zone.findFirst({
      where: { userId: session.id },
    });

    if (!zone) {
      return NextResponse.json({ error: 'No zone found' }, { status: 404 });
    }

    // Get all lamps for the user's zone
    const lamps = await prisma.lampChannel.findMany({
      where: { zoneId: zone.id },
    });

    if (lamps.length === 0) {
      return NextResponse.json(
        { error: 'No lamps found' },
        { status: 404 }
      );
    }

    // Determine the target intensity
    const targetIntensity = action === 'all_on' ? 100 : 0;

    // Update all lamps with a single curve point at current time
    const currentTime = new Date();
    const timeString = `${String(currentTime.getHours()).padStart(2, '0')}:${String(currentTime.getMinutes()).padStart(2, '0')}`;

    // Update all lamps' curves
    const updatePromises = lamps.map((lamp) => {
      const newCurve = [
        {
          time: timeString,
          intensity: targetIntensity,
        },
      ];

      return prisma.lampChannel.update({
        where: { id: lamp.id },
        data: {
          curve: newCurve,
        },
      });
    });

    await Promise.all(updatePromises);

    return NextResponse.json({
      success: true,
      action,
      lampsUpdated: lamps.length,
      intensity: targetIntensity,
    });
  } catch (error) {
    console.error('Lighting override API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
