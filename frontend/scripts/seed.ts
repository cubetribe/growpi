import { createClient } from '@supabase/supabase-js';
import bcrypt from 'bcryptjs';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

const supabase = createClient(supabaseUrl, supabaseKey);

async function main() {
  console.log('Starting database seed...');

  const hashedPassword = await bcrypt.hash('Mi83xer#', 10);

  const { data: existingUser } = await supabase
    .from('users')
    .select('id')
    .eq('username', 'admin')
    .maybeSingle();

  let userId: string;

  if (existingUser) {
    console.log('Admin user already exists');
    userId = existingUser.id;
  } else {
    const { data: user, error: userError } = await supabase
      .from('users')
      .insert({
        username: 'admin',
        password: hashedPassword,
      })
      .select('id')
      .single();

    if (userError || !user) {
      console.error('Error creating user:', userError);
      return;
    }

    userId = user.id;
    console.log('Created admin user');
  }

  const { data: existingZone } = await supabase
    .from('zones')
    .select('id')
    .eq('user_id', userId)
    .maybeSingle();

  let zoneId: string;

  if (existingZone) {
    console.log('Zone already exists');
    zoneId = existingZone.id;
  } else {
    const { data: zone, error: zoneError } = await supabase
      .from('zones')
      .insert({
        name: 'Gewächshaus 1',
        user_id: userId,
      })
      .select('id')
      .single();

    if (zoneError || !zone) {
      console.error('Error creating zone:', zoneError);
      return;
    }

    zoneId = zone.id;
    console.log('Created zone');
  }

  const lampChannels = [
    { name: 'Red', channel: 1, curve: [
      { time: '06:00', intensity: 0 },
      { time: '07:00', intensity: 30 },
      { time: '08:00', intensity: 80 },
      { time: '12:00', intensity: 100 },
      { time: '16:00', intensity: 80 },
      { time: '18:00', intensity: 30 },
      { time: '20:00', intensity: 0 },
    ]},
    { name: 'Blue', channel: 2, curve: [
      { time: '06:00', intensity: 0 },
      { time: '07:00', intensity: 25 },
      { time: '08:00', intensity: 70 },
      { time: '12:00', intensity: 90 },
      { time: '16:00', intensity: 70 },
      { time: '18:00', intensity: 25 },
      { time: '20:00', intensity: 0 },
    ]},
    { name: 'Warm White', channel: 3, curve: [
      { time: '06:00', intensity: 0 },
      { time: '07:00', intensity: 20 },
      { time: '08:00', intensity: 60 },
      { time: '12:00', intensity: 80 },
      { time: '16:00', intensity: 60 },
      { time: '18:00', intensity: 20 },
      { time: '20:00', intensity: 0 },
    ]},
    { name: 'Cool White', channel: 4, curve: [
      { time: '06:00', intensity: 0 },
      { time: '07:00', intensity: 15 },
      { time: '08:00', intensity: 50 },
      { time: '12:00', intensity: 70 },
      { time: '16:00', intensity: 50 },
      { time: '18:00', intensity: 15 },
      { time: '20:00', intensity: 0 },
    ]},
    { name: 'UV', channel: 5, curve: [
      { time: '10:00', intensity: 0 },
      { time: '11:00', intensity: 20 },
      { time: '14:00', intensity: 30 },
      { time: '15:00', intensity: 20 },
      { time: '16:00', intensity: 0 },
    ]},
  ];

  for (const lamp of lampChannels) {
    const { error } = await supabase
      .from('lamp_channels')
      .upsert(
        {
          zone_id: zoneId,
          name: lamp.name,
          channel: lamp.channel,
          curve: lamp.curve,
        },
        {
          onConflict: 'zone_id,channel',
          ignoreDuplicates: false,
        }
      );

    if (error) {
      console.error(`Error creating lamp ${lamp.name}:`, error);
    } else {
      console.log(`Created lamp: ${lamp.name}`);
    }
  }

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

  const sensorIds: Record<string, string> = {};

  for (const sensor of sensorTypes) {
    const { data, error } = await supabase
      .from('sensors')
      .upsert(
        {
          zone_id: zoneId,
          name: sensor.name,
          type: sensor.type,
        },
        {
          onConflict: 'zone_id,type',
          ignoreDuplicates: false,
        }
      )
      .select('id')
      .single();

    if (error) {
      console.error(`Error creating sensor ${sensor.name}:`, error);
    } else if (data) {
      sensorIds[sensor.type] = data.id;
      console.log(`Created sensor: ${sensor.name}`);
    }
  }

  console.log('Generating sensor readings...');
  const now = new Date();
  const readings = [];

  for (let i = 287; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * 5 * 60 * 1000);

    const baseTemperature = 22 + Math.sin(i / 10) * 3;
    const baseHumidity = 65 + Math.sin(i / 8) * 10;

    readings.push(
      { sensor_id: sensorIds.temperature, value: baseTemperature + Math.random() * 2 - 1, created_at: timestamp.toISOString() },
      { sensor_id: sensorIds.humidity, value: baseHumidity + Math.random() * 5 - 2.5, created_at: timestamp.toISOString() },
      { sensor_id: sensorIds.soilMoisture, value: 55 + Math.sin(i / 15) * 15 + Math.random() * 5, created_at: timestamp.toISOString() },
      { sensor_id: sensorIds.soilTemp, value: 20 + Math.sin(i / 12) * 2 + Math.random() * 1, created_at: timestamp.toISOString() },
      { sensor_id: sensorIds.soilPH, value: 6.5 + Math.random() * 0.5 - 0.25, created_at: timestamp.toISOString() },
      { sensor_id: sensorIds.soilEC, value: 1.5 + Math.random() * 0.3 - 0.15, created_at: timestamp.toISOString() },
      { sensor_id: sensorIds.soilN, value: Math.floor(180 + Math.random() * 40 - 20), created_at: timestamp.toISOString() },
      { sensor_id: sensorIds.soilP, value: Math.floor(45 + Math.random() * 10 - 5), created_at: timestamp.toISOString() },
      { sensor_id: sensorIds.soilK, value: Math.floor(220 + Math.random() * 30 - 15), created_at: timestamp.toISOString() }
    );
  }

  const { error: readingsError } = await supabase
    .from('sensor_readings')
    .insert(readings);

  if (readingsError) {
    console.error('Error creating sensor readings:', readingsError);
  } else {
    console.log(`Created ${readings.length} sensor readings`);
  }

  const { error: settingsError } = await supabase
    .from('settings')
    .upsert(
      {
        zone_id: zoneId,
        sensor_interval: 60,
        demo_mode: true,
        language: 'de',
        theme: 'dark',
      },
      {
        onConflict: 'zone_id',
        ignoreDuplicates: false,
      }
    );

  if (settingsError) {
    console.error('Error creating settings:', settingsError);
  } else {
    console.log('Created settings');
  }

  const alertConfigs = [
    { sensor_type: 'temperature', min_value: 18, max_value: 28 },
    { sensor_type: 'humidity', min_value: 40, max_value: 80 },
    { sensor_type: 'soilMoisture', min_value: 30, max_value: 70 },
    { sensor_type: 'soilPH', min_value: 6.0, max_value: 7.0 },
    { sensor_type: 'soilEC', min_value: 1.0, max_value: 2.5 },
  ];

  for (const alert of alertConfigs) {
    const { error } = await supabase
      .from('alert_configs')
      .insert({
        zone_id: zoneId,
        sensor_type: alert.sensor_type,
        min_value: alert.min_value,
        max_value: alert.max_value,
        email_alert: true,
        push_alert: true,
        enabled: true,
      });

    if (error && error.code !== '23505') {
      console.error(`Error creating alert config for ${alert.sensor_type}:`, error);
    } else {
      console.log(`Created alert config: ${alert.sensor_type}`);
    }
  }

  const apiKey = 'demo_api_key_' + Math.random().toString(36).substring(2, 15);
  const { error: piError } = await supabase
    .from('pi_connections')
    .insert({
      zone_id: zoneId,
      api_key: apiKey,
      status: 'offline',
      last_heartbeat: null,
    });

  if (piError && piError.code !== '23505') {
    console.error('Error creating Pi connection:', piError);
  } else {
    console.log('Created Pi connection');
    console.log('API Key:', apiKey);
  }

  console.log('✅ Database seeding completed!');
  console.log('Login credentials:');
  console.log('  Username: admin');
  console.log('  Password: Mi83xer#');
}

main().catch(console.error);
