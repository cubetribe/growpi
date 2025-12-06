/*
  # Grow-Pi Greenhouse Control System Schema

  This migration creates the complete database schema for the Grow-Pi greenhouse management platform.

  ## New Tables
  
  1. **users**
     - `id` (uuid, primary key)
     - `username` (text, unique)
     - `password` (text, hashed)
     - `created_at` (timestamptz)
     - Stores user authentication credentials

  2. **zones**
     - `id` (uuid, primary key)
     - `name` (text)
     - `user_id` (uuid, foreign key to users)
     - `created_at` (timestamptz)
     - Represents individual greenhouses or growing zones

  3. **lamp_channels**
     - `id` (uuid, primary key)
     - `zone_id` (uuid, foreign key to zones)
     - `name` (text) - e.g., "Red", "Blue", "Warm White"
     - `channel` (integer) - 1-5
     - `curve` (jsonb) - Array of { time: "HH:MM", intensity: 0-100 }
     - `updated_at` (timestamptz)
     - Controls individual lighting channels

  4. **sensors**
     - `id` (uuid, primary key)
     - `zone_id` (uuid, foreign key to zones)
     - `name` (text)
     - `type` (text) - temperature, humidity, soilMoisture, etc.
     - Defines sensor configurations

  5. **sensor_readings**
     - `id` (uuid, primary key)
     - `sensor_id` (uuid, foreign key to sensors)
     - `value` (float)
     - `created_at` (timestamptz)
     - Stores time-series sensor data

  6. **alert_configs**
     - `id` (uuid, primary key)
     - `zone_id` (uuid, foreign key to zones)
     - `sensor_type` (text)
     - `min_value` (float, nullable)
     - `max_value` (float, nullable)
     - `email_alert` (boolean)
     - `push_alert` (boolean)
     - `enabled` (boolean)
     - Alert threshold configurations

  7. **settings**
     - `id` (uuid, primary key)
     - `zone_id` (uuid, unique, foreign key to zones)
     - `sensor_interval` (integer) - seconds between readings
     - `demo_mode` (boolean)
     - `language` (text) - "de" or "en"
     - `theme` (text) - "dark" or "light"
     - Per-zone settings

  8. **pi_connections**
     - `id` (uuid, primary key)
     - `zone_id` (uuid, foreign key to zones)
     - `api_key` (text, unique)
     - `last_heartbeat` (timestamptz)
     - `status` (text)
     - Raspberry Pi connection management

  ## Security
  
  - Enable RLS on all tables
  - Policies restrict access to authenticated users' own data
  - API key authentication for Raspberry Pi endpoints
*/

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username text UNIQUE NOT NULL,
  password text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Create zones table
CREATE TABLE IF NOT EXISTS zones (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now()
);

-- Create lamp_channels table
CREATE TABLE IF NOT EXISTS lamp_channels (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id uuid NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
  name text NOT NULL,
  channel integer NOT NULL CHECK (channel >= 1 AND channel <= 5),
  curve jsonb NOT NULL DEFAULT '[]'::jsonb,
  updated_at timestamptz DEFAULT now()
);

-- Create sensors table
CREATE TABLE IF NOT EXISTS sensors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id uuid NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
  name text NOT NULL,
  type text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Create sensor_readings table with index for performance
CREATE TABLE IF NOT EXISTS sensor_readings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sensor_id uuid NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
  value double precision NOT NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_id_created_at 
  ON sensor_readings(sensor_id, created_at DESC);

-- Create alert_configs table
CREATE TABLE IF NOT EXISTS alert_configs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id uuid NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
  sensor_type text NOT NULL,
  min_value double precision,
  max_value double precision,
  email_alert boolean DEFAULT true,
  push_alert boolean DEFAULT true,
  enabled boolean DEFAULT true
);

-- Create settings table
CREATE TABLE IF NOT EXISTS settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id uuid UNIQUE NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
  sensor_interval integer DEFAULT 60 CHECK (sensor_interval >= 5 AND sensor_interval <= 3600),
  demo_mode boolean DEFAULT true,
  language text DEFAULT 'de' CHECK (language IN ('de', 'en')),
  theme text DEFAULT 'dark' CHECK (theme IN ('dark', 'light'))
);

-- Create pi_connections table
CREATE TABLE IF NOT EXISTS pi_connections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id uuid NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
  api_key text UNIQUE NOT NULL,
  last_heartbeat timestamptz,
  status text DEFAULT 'offline',
  created_at timestamptz DEFAULT now()
);

-- Enable Row Level Security on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE lamp_channels ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensors ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensor_readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE pi_connections ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Users can view own profile"
  ON users FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- RLS Policies for zones table
CREATE POLICY "Users can view own zones"
  ON zones FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can insert own zones"
  ON zones FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own zones"
  ON zones FOR UPDATE
  TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own zones"
  ON zones FOR DELETE
  TO authenticated
  USING (user_id = auth.uid());

-- RLS Policies for lamp_channels table
CREATE POLICY "Users can view lamps in own zones"
  ON lamp_channels FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = lamp_channels.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert lamps in own zones"
  ON lamp_channels FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = lamp_channels.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update lamps in own zones"
  ON lamp_channels FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = lamp_channels.zone_id
      AND zones.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = lamp_channels.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete lamps in own zones"
  ON lamp_channels FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = lamp_channels.zone_id
      AND zones.user_id = auth.uid()
    )
  );

-- RLS Policies for sensors table
CREATE POLICY "Users can view sensors in own zones"
  ON sensors FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = sensors.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert sensors in own zones"
  ON sensors FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = sensors.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update sensors in own zones"
  ON sensors FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = sensors.zone_id
      AND zones.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = sensors.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete sensors in own zones"
  ON sensors FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = sensors.zone_id
      AND zones.user_id = auth.uid()
    )
  );

-- RLS Policies for sensor_readings table
CREATE POLICY "Users can view readings from own zones"
  ON sensor_readings FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM sensors
      JOIN zones ON zones.id = sensors.zone_id
      WHERE sensors.id = sensor_readings.sensor_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert readings in own zones"
  ON sensor_readings FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM sensors
      JOIN zones ON zones.id = sensors.zone_id
      WHERE sensors.id = sensor_readings.sensor_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete readings from own zones"
  ON sensor_readings FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM sensors
      JOIN zones ON zones.id = sensors.zone_id
      WHERE sensors.id = sensor_readings.sensor_id
      AND zones.user_id = auth.uid()
    )
  );

-- RLS Policies for alert_configs table
CREATE POLICY "Users can view alerts in own zones"
  ON alert_configs FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = alert_configs.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert alerts in own zones"
  ON alert_configs FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = alert_configs.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update alerts in own zones"
  ON alert_configs FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = alert_configs.zone_id
      AND zones.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = alert_configs.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete alerts in own zones"
  ON alert_configs FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = alert_configs.zone_id
      AND zones.user_id = auth.uid()
    )
  );

-- RLS Policies for settings table
CREATE POLICY "Users can view settings for own zones"
  ON settings FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = settings.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert settings for own zones"
  ON settings FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = settings.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update settings for own zones"
  ON settings FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = settings.zone_id
      AND zones.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = settings.zone_id
      AND zones.user_id = auth.uid()
    )
  );

-- RLS Policies for pi_connections table
CREATE POLICY "Users can view pi connections for own zones"
  ON pi_connections FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = pi_connections.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can insert pi connections for own zones"
  ON pi_connections FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = pi_connections.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can update pi connections for own zones"
  ON pi_connections FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = pi_connections.zone_id
      AND zones.user_id = auth.uid()
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = pi_connections.zone_id
      AND zones.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can delete pi connections for own zones"
  ON pi_connections FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM zones
      WHERE zones.id = pi_connections.zone_id
      AND zones.user_id = auth.uid()
    )
  );