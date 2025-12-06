#!/usr/bin/env python3
"""Import historical energy data for Main Light into plug_logs database.

The API calculates kWh as:
    kWh = sum(power * 60/3600) / 1000 = sum(power) / 60000

So to get X kWh, we need: sum(power) = X * 60000

For November with 28.36 kWh:
    sum(power) = 28.36 * 60000 = 1,701,600

We create 720 hourly entries (30 days * 24 hours):
    power per entry = 1,701,600 / 720 = 2363 W

This seems high but is correct because each entry represents
60 one-minute readings at ~39W average (39 * 60 = 2340W).
"""

import sqlite3
from datetime import datetime, timedelta
import random

# Connect to the database
db_path = "/opt/grow-pi/data/growpi.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Main Light device ID
main_light_id = "bf36487f67d7bb8fc18buj"

print("=== Importing Historical Energy Data ===")
print(f"Database: {db_path}")

# Historical data:
# November 2025: 28.36 kWh
# December 2025 (1-5): 18 kWh

# Calculate required sum(power) for each month
# kWh = sum(power) / 60000
# sum(power) = kWh * 60000

nov_kwh = 28.36
nov_sum_power = nov_kwh * 60000  # 1,701,600
nov_entries = 30 * 24  # 720 hourly entries
nov_power_per_entry = nov_sum_power / nov_entries  # ~2363 W

dec_kwh = 18.0
dec_sum_power = dec_kwh * 60000  # 1,080,000
dec_entries = 5 * 24  # 120 hourly entries (Dec 1-5)
dec_power_per_entry = dec_sum_power / dec_entries  # 9000 W

print(f"\nNovember 2025:")
print(f"  Target: {nov_kwh} kWh")
print(f"  Required sum(power): {nov_sum_power}")
print(f"  Entries: {nov_entries}")
print(f"  Power per entry: {nov_power_per_entry:.0f} W")

print(f"\nDecember 1-5, 2025:")
print(f"  Target: {dec_kwh} kWh")
print(f"  Required sum(power): {dec_sum_power}")
print(f"  Entries: {dec_entries}")
print(f"  Power per entry: {dec_power_per_entry:.0f} W")

# Check existing entries
cursor.execute("SELECT COUNT(*) FROM plug_logs WHERE device_id = ?", (main_light_id,))
existing = cursor.fetchone()[0]
print(f"\nExisting Main Light entries: {existing}")

# Generate November entries
# Schema: id, device_id, voltage, current, power, created_at, synced_at
import uuid

entries = []
nov_start = datetime(2025, 11, 1, 0, 0, 0)

for hour in range(nov_entries):
    ts = nov_start + timedelta(hours=hour)
    power = nov_power_per_entry  # Exact value, no variation
    entries.append((
        str(uuid.uuid4()),  # id
        main_light_id,      # device_id
        230.0,              # voltage
        round(power / 230.0, 3),  # current
        round(power, 1),    # power
        ts.strftime("%Y-%m-%d %H:%M:%S"),  # created_at
    ))

# Generate December 1-5 entries
dec_start = datetime(2025, 12, 1, 0, 0, 0)

for hour in range(dec_entries):
    ts = dec_start + timedelta(hours=hour)
    power = dec_power_per_entry  # Exact value, no variation
    entries.append((
        str(uuid.uuid4()),
        main_light_id,
        230.0,
        round(power / 230.0, 3),
        round(power, 1),
        ts.strftime("%Y-%m-%d %H:%M:%S"),
    ))

print(f"\nGenerated {len(entries)} entries")

# Insert entries
cursor.executemany("""
    INSERT INTO plug_logs (id, device_id, voltage, current, power, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
""", entries)

conn.commit()

# Verify totals
cursor.execute("""
    SELECT
        strftime('%Y-%m', created_at) as month,
        COUNT(*) as entries,
        SUM(power) as total_power
    FROM plug_logs
    WHERE device_id = ?
    GROUP BY month
    ORDER BY month
""", (main_light_id,))

print("\n=== Verification ===")
for row in cursor.fetchall():
    month = row[0]
    count = row[1]
    total = row[2] or 0
    kwh = total / 60000
    print(f"{month}: {count} entries, {kwh:.2f} kWh")

conn.close()
print("\nImport complete!")
