-- Seed script for Grow-Pi

-- Create admin user (password: Mi83xer#, hashed with bcrypt)
INSERT INTO users (username, password)
VALUES ('admin', '$2b$10$mSy.ZrlHSZcOBVTCxx.bAesJGyBBUjxqPupsJsC5oM8zHcX4uWxx2')
ON CONFLICT (username) DO NOTHING;

-- Get user ID for subsequent inserts
DO $$
DECLARE
  user_uuid UUID;
  zone_uuid UUID;
  temp_sensor_id UUID;
  humidity_sensor_id UUID;
  soil_moisture_sensor_id UUID;
  soil_temp_sensor_id UUID;
  soil_ph_sensor_id UUID;
  soil_ec_sensor_id UUID;
  soil_n_sensor_id UUID;
  soil_p_sensor_id UUID;
  soil_k_sensor_id UUID;
BEGIN
  -- Get or create user
  SELECT id INTO user_uuid FROM users WHERE username = 'admin';

  -- Create zone
  INSERT INTO zones (name, user_id)
  VALUES ('Gewächshaus 1', user_uuid)
  ON CONFLICT DO NOTHING
  RETURNING id INTO zone_uuid;

  IF zone_uuid IS NULL THEN
    SELECT id INTO zone_uuid FROM zones WHERE user_id = user_uuid LIMIT 1;
  END IF;

  -- Create lamp channels with curves
  INSERT INTO lamp_channels (zone_id, name, channel, curve) VALUES
    (zone_uuid, 'Red', 1, '[{"time":"06:00","intensity":0},{"time":"07:00","intensity":30},{"time":"08:00","intensity":80},{"time":"12:00","intensity":100},{"time":"16:00","intensity":80},{"time":"18:00","intensity":30},{"time":"20:00","intensity":0}]'::jsonb),
    (zone_uuid, 'Blue', 2, '[{"time":"06:00","intensity":0},{"time":"07:00","intensity":25},{"time":"08:00","intensity":70},{"time":"12:00","intensity":90},{"time":"16:00","intensity":70},{"time":"18:00","intensity":25},{"time":"20:00","intensity":0}]'::jsonb),
    (zone_uuid, 'Warm White', 3, '[{"time":"06:00","intensity":0},{"time":"07:00","intensity":20},{"time":"08:00","intensity":60},{"time":"12:00","intensity":80},{"time":"16:00","intensity":60},{"time":"18:00","intensity":20},{"time":"20:00","intensity":0}]'::jsonb),
    (zone_uuid, 'Cool White', 4, '[{"time":"06:00","intensity":0},{"time":"07:00","intensity":15},{"time":"08:00","intensity":50},{"time":"12:00","intensity":70},{"time":"16:00","intensity":50},{"time":"18:00","intensity":15},{"time":"20:00","intensity":0}]'::jsonb),
    (zone_uuid, 'UV', 5, '[{"time":"10:00","intensity":0},{"time":"11:00","intensity":20},{"time":"14:00","intensity":30},{"time":"15:00","intensity":20},{"time":"16:00","intensity":0}]'::jsonb)
  ON CONFLICT DO NOTHING;

  -- Create sensors
  INSERT INTO sensors (zone_id, name, type) VALUES
    (zone_uuid, 'Ambient Temperature', 'temperature'),
    (zone_uuid, 'Ambient Humidity', 'humidity'),
    (zone_uuid, 'Soil Moisture', 'soilMoisture'),
    (zone_uuid, 'Soil Temperature', 'soilTemp'),
    (zone_uuid, 'Soil pH', 'soilPH'),
    (zone_uuid, 'Soil EC', 'soilEC'),
    (zone_uuid, 'Soil Nitrogen', 'soilN'),
    (zone_uuid, 'Soil Phosphorus', 'soilP'),
    (zone_uuid, 'Soil Potassium', 'soilK')
  ON CONFLICT DO NOTHING;

  -- Get sensor IDs
  SELECT id INTO temp_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'temperature';
  SELECT id INTO humidity_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'humidity';
  SELECT id INTO soil_moisture_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'soilMoisture';
  SELECT id INTO soil_temp_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'soilTemp';
  SELECT id INTO soil_ph_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'soilPH';
  SELECT id INTO soil_ec_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'soilEC';
  SELECT id INTO soil_n_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'soilN';
  SELECT id INTO soil_p_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'soilP';
  SELECT id INTO soil_k_sensor_id FROM sensors WHERE zone_id = zone_uuid AND type = 'soilK';

  -- Insert sample sensor readings (last 24 hours)
  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT temp_sensor_id, 22 + (random() * 4 - 2)::numeric(4,1), NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT humidity_sensor_id, 65 + (random() * 15 - 7.5)::numeric(4,1), NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT soil_moisture_sensor_id, 55 + (random() * 20 - 10)::numeric(4,1), NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT soil_temp_sensor_id, 20 + (random() * 3 - 1.5)::numeric(4,1), NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT soil_ph_sensor_id, 6.5 + (random() * 0.5 - 0.25)::numeric(3,2), NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT soil_ec_sensor_id, 1.5 + (random() * 0.3 - 0.15)::numeric(3,2), NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT soil_n_sensor_id, (180 + random() * 40 - 20)::integer, NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT soil_p_sensor_id, (45 + random() * 10 - 5)::integer, NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  INSERT INTO sensor_readings (sensor_id, value, created_at)
  SELECT soil_k_sensor_id, (220 + random() * 30 - 15)::integer, NOW() - (interval '5 minutes' * i)
  FROM generate_series(0, 287) i;

  -- Create settings
  INSERT INTO settings (zone_id, sensor_interval, demo_mode, language, theme)
  VALUES (zone_uuid, 60, true, 'de', 'dark')
  ON CONFLICT (zone_id) DO UPDATE SET
    sensor_interval = 60,
    demo_mode = true,
    language = 'de',
    theme = 'dark';

  -- Create alert configs
  INSERT INTO alert_configs (zone_id, sensor_type, min_value, max_value, email_alert, push_alert, enabled) VALUES
    (zone_uuid, 'temperature', 18, 28, true, true, true),
    (zone_uuid, 'humidity', 40, 80, true, true, true),
    (zone_uuid, 'soilMoisture', 30, 70, true, true, true),
    (zone_uuid, 'soilPH', 6.0, 7.0, true, true, true),
    (zone_uuid, 'soilEC', 1.0, 2.5, true, true, true)
  ON CONFLICT DO NOTHING;

  -- Create Pi connection
  INSERT INTO pi_connections (zone_id, api_key, status)
  VALUES (zone_uuid, 'demo_api_key_' || substr(md5(random()::text), 1, 15), 'offline')
  ON CONFLICT DO NOTHING;

END $$;
