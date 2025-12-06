import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  console.log('Starting database seed with Prisma...');

  // Hash admin password
  const hashedPassword = await bcrypt.hash('Mi83xer#', 10);

  // Create or get admin user
  let user = await prisma.user.findUnique({
    where: { username: 'admin' },
  });

  if (user) {
    console.log('✓ Admin user already exists');
  } else {
    user = await prisma.user.create({
      data: {
        username: 'admin',
        password: hashedPassword,
      },
    });
    console.log('✓ Created admin user');
  }

  // Create or get zone
  let zone = await prisma.zone.findFirst({
    where: { userId: user.id },
  });

  if (zone) {
    console.log('✓ Zone already exists');
  } else {
    zone = await prisma.zone.create({
      data: {
        name: 'Gewächshaus 1',
        userId: user.id,
      },
    });
    console.log('✓ Created zone: Gewächshaus 1');
  }

  // Create lamp channels
  const lampChannels = [
    {
      name: 'Red',
      channel: 1,
      curve: [
        { time: '06:00', intensity: 0 },
        { time: '07:00', intensity: 30 },
        { time: '08:00', intensity: 80 },
        { time: '12:00', intensity: 100 },
        { time: '16:00', intensity: 80 },
        { time: '18:00', intensity: 30 },
        { time: '20:00', intensity: 0 },
      ],
    },
    {
      name: 'Blue',
      channel: 2,
      curve: [
        { time: '06:00', intensity: 0 },
        { time: '07:00', intensity: 25 },
        { time: '08:00', intensity: 70 },
        { time: '12:00', intensity: 90 },
        { time: '16:00', intensity: 70 },
        { time: '18:00', intensity: 25 },
        { time: '20:00', intensity: 0 },
      ],
    },
    {
      name: 'Warm White',
      channel: 3,
      curve: [
        { time: '06:00', intensity: 0 },
        { time: '07:00', intensity: 20 },
        { time: '08:00', intensity: 60 },
        { time: '12:00', intensity: 80 },
        { time: '16:00', intensity: 60 },
        { time: '18:00', intensity: 20 },
        { time: '20:00', intensity: 0 },
      ],
    },
    {
      name: 'Cool White',
      channel: 4,
      curve: [
        { time: '06:00', intensity: 0 },
        { time: '07:00', intensity: 15 },
        { time: '08:00', intensity: 50 },
        { time: '12:00', intensity: 70 },
        { time: '16:00', intensity: 50 },
        { time: '18:00', intensity: 15 },
        { time: '20:00', intensity: 0 },
      ],
    },
    {
      name: 'UV',
      channel: 5,
      curve: [
        { time: '10:00', intensity: 0 },
        { time: '11:00', intensity: 20 },
        { time: '14:00', intensity: 30 },
        { time: '15:00', intensity: 20 },
        { time: '16:00', intensity: 0 },
      ],
    },
  ];

  for (const lamp of lampChannels) {
    await prisma.lampChannel.upsert({
      where: {
        zoneId_channel: {
          zoneId: zone.id,
          channel: lamp.channel,
        },
      },
      update: {
        name: lamp.name,
        curve: lamp.curve,
      },
      create: {
        zoneId: zone.id,
        name: lamp.name,
        channel: lamp.channel,
        curve: lamp.curve,
      },
    });
    console.log(`✓ Lamp channel: ${lamp.name}`);
  }

  // Create sensors
  const sensorTypes = [
    { name: 'Ambient Temperature', type: 'temperature' },
    { name: 'Ambient Humidity', type: 'humidity' },
    { name: 'Soil Moisture', type: 'soilMoisture' },
    { name: 'Soil Temperature', type: 'soilTemp' },
    { name: 'Soil pH', type: 'soilPH' },
    { name: 'Soil EC', type: 'soilEC' },
    { name: 'Soil Nitrogen', type: 'soilN' },
    { name: 'Soil Phosphorus', type: 'soilP' },
    { name: 'Soil Potassium', type: 'soilK' },
  ];

  const sensors: Record<string, any> = {};

  for (const sensor of sensorTypes) {
    const s = await prisma.sensor.upsert({
      where: {
        zoneId_type: {
          zoneId: zone.id,
          type: sensor.type,
        },
      },
      update: {
        name: sensor.name,
      },
      create: {
        zoneId: zone.id,
        name: sensor.name,
        type: sensor.type,
      },
    });
    sensors[sensor.type] = s;
    console.log(`✓ Sensor: ${sensor.name}`);
  }

  // Generate sensor readings (last 24 hours, every 5 minutes)
  console.log('Generating sensor readings...');
  const now = new Date();
  const readings: any[] = [];

  for (let i = 287; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * 5 * 60 * 1000);

    const baseTemperature = 22 + Math.sin(i / 10) * 3;
    const baseHumidity = 65 + Math.sin(i / 8) * 10;

    readings.push(
      {
        sensorId: sensors.temperature.id,
        value: baseTemperature + Math.random() * 2 - 1,
        createdAt: timestamp,
      },
      {
        sensorId: sensors.humidity.id,
        value: baseHumidity + Math.random() * 5 - 2.5,
        createdAt: timestamp,
      },
      {
        sensorId: sensors.soilMoisture.id,
        value: 55 + Math.sin(i / 15) * 15 + Math.random() * 5,
        createdAt: timestamp,
      },
      {
        sensorId: sensors.soilTemp.id,
        value: 20 + Math.sin(i / 12) * 2 + Math.random() * 1,
        createdAt: timestamp,
      },
      {
        sensorId: sensors.soilPH.id,
        value: 6.5 + Math.random() * 0.5 - 0.25,
        createdAt: timestamp,
      },
      {
        sensorId: sensors.soilEC.id,
        value: 1.5 + Math.random() * 0.3 - 0.15,
        createdAt: timestamp,
      },
      {
        sensorId: sensors.soilN.id,
        value: Math.floor(180 + Math.random() * 40 - 20),
        createdAt: timestamp,
      },
      {
        sensorId: sensors.soilP.id,
        value: Math.floor(45 + Math.random() * 10 - 5),
        createdAt: timestamp,
      },
      {
        sensorId: sensors.soilK.id,
        value: Math.floor(220 + Math.random() * 30 - 15),
        createdAt: timestamp,
      }
    );
  }

  await prisma.sensorReading.createMany({
    data: readings,
  });
  console.log(`✓ Created ${readings.length} sensor readings`);

  // Create settings
  await prisma.settings.upsert({
    where: { zoneId: zone.id },
    update: {
      sensorInterval: 60,
      demoMode: true,
      language: 'de',
      theme: 'dark',
    },
    create: {
      zoneId: zone.id,
      sensorInterval: 60,
      demoMode: true,
      language: 'de',
      theme: 'dark',
    },
  });
  console.log('✓ Settings created');

  // Create alert configs
  const alertConfigs = [
    { sensorType: 'temperature', minValue: 18, maxValue: 28 },
    { sensorType: 'humidity', minValue: 40, maxValue: 80 },
    { sensorType: 'soilMoisture', minValue: 30, maxValue: 70 },
    { sensorType: 'soilPH', minValue: 6.0, maxValue: 7.0 },
    { sensorType: 'soilEC', minValue: 1.0, maxValue: 2.5 },
  ];

  for (const alert of alertConfigs) {
    await prisma.alertConfig.upsert({
      where: {
        zoneId_sensorType: {
          zoneId: zone.id,
          sensorType: alert.sensorType,
        },
      },
      update: {
        minValue: alert.minValue,
        maxValue: alert.maxValue,
      },
      create: {
        zoneId: zone.id,
        sensorType: alert.sensorType,
        minValue: alert.minValue,
        maxValue: alert.maxValue,
        emailAlert: true,
        pushAlert: true,
        enabled: true,
      },
    });
    console.log(`✓ Alert config: ${alert.sensorType}`);
  }

  // Create Pi connection
  const apiKey = 'demo_api_key_' + Math.random().toString(36).substring(2, 15);
  await prisma.piConnection.upsert({
    where: { apiKey: apiKey },
    update: {},
    create: {
      zoneId: zone.id,
      apiKey: apiKey,
      status: 'offline',
    },
  });
  console.log('✓ Pi connection created');
  console.log(`  API Key: ${apiKey}`);

  console.log('\n✅ Database seeding completed!');
  console.log('\nLogin credentials:');
  console.log('  Username: admin');
  console.log('  Password: Mi83xer#');
}

main()
  .catch((e) => {
    console.error('Error seeding database:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
