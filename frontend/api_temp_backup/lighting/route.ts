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
    });

    if (!zone) {
      return NextResponse.json({ error: 'No zone found' }, { status: 404 });
    }

    const lamps = await prisma.lampChannel.findMany({
      where: { zoneId: zone.id },
      orderBy: { channel: 'asc' },
    });

    return NextResponse.json({ lamps });
  } catch (error) {
    console.error('Lighting API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function PUT(request: Request) {
  try {
    const session = await getSession();
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { lampId, curve } = body;

    if (!lampId || !curve || !Array.isArray(curve)) {
      return NextResponse.json(
        { error: 'Missing required fields: lampId, curve' },
        { status: 400 }
      );
    }

    // Verify lamp belongs to user's zone
    const zone = await prisma.zone.findFirst({
      where: { userId: session.id },
    });

    if (!zone) {
      return NextResponse.json({ error: 'No zone found' }, { status: 404 });
    }

    const lamp = await prisma.lampChannel.findFirst({
      where: {
        id: lampId,
        zoneId: zone.id,
      },
    });

    if (!lamp) {
      return NextResponse.json({ error: 'Lamp not found' }, { status: 404 });
    }

    // Update the lamp curve
    const updatedLamp = await prisma.lampChannel.update({
      where: { id: lampId },
      data: { curve: curve },
    });

    return NextResponse.json({
      success: true,
      lamp: updatedLamp,
    });
  } catch (error) {
    console.error('Lighting update error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
