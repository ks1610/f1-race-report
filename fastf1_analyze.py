import fastf1
import fastf1.plotting
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.collections import LineCollection # New Import
import numpy as np

# 1. Setup fastf1 and plotting
fastf1.plotting.setup_mpl()
fastf1.Cache.enable_cache('cache')

# 2. Load the session
session = fastf1.get_session(2025, 'Brazil', 'R')
session.load(telemetry=True)

# 3. Get driver data
driver = 'VER'
driver_laps = session.laps.pick_drivers(driver)

# --- CHANGE 1: Use get_telemetry() for all data ---
fastest_lap = driver_laps.pick_fastest()
# Get all telemetry channels for the fastest lap
telemetry = fastest_lap.get_telemetry()

# Get laps for weather
laps_for_weather = driver_laps[driver_laps['PitOutTime'].isna()]

print(f"Analyzing {driver} - {session.event['EventName']} {session.event.year}")

# 4. Define the plotting layout (Dashboard)
fig = plt.figure(figsize=(20, 25))
gs = fig.add_gridspec(5, 2) # 5 rows, 2 columns

# --- MODIFIED SECTION ---
# Get the event date for the title
# This formats the timestamp (e.g., 2024-05-26) into a string (e.g., "May 26")
event_date = session.event.EventDate.strftime('%b %d')

# Add a main title for the whole figure
fig.suptitle(
    f"F1 Data Dashboard: {driver} - {session.event.year} {session.event['EventName']} ({event_date}) - Race",
    fontsize=24,
    fontweight='bold'
)
# --- END MODIFIED SECTION ---

# --- PLOT 1: Lap Times & Position (Full Width) ---
ax_laptime = fig.add_subplot(gs[0, :]) # Row 0, all columns
ax_laptime.set_title("Lap Times & Race Position", fontsize=16)

compounds = driver_laps['Compound'].unique()
for compound in compounds:
    compound_laps = driver_laps[driver_laps['Compound'] == compound]
    lap_times_seconds = compound_laps['LapTime'].dt.total_seconds()
    
    color = fastf1.plotting.get_compound_color(compound, session=session)
    
    ax_laptime.plot(
        compound_laps['LapNumber'],
        lap_times_seconds,
        color=color,
        label=compound,
        linestyle='-',
        marker='o',
        markersize=5
    )
ax_laptime.set_xlabel("Lap Number")
ax_laptime.set_ylabel("Lap Time (s)")

# Add position on a twin axis
ax_position = ax_laptime.twinx()
ax_position.plot(
    driver_laps['LapNumber'],
    driver_laps['Position'],
    color='grey',
    linestyle='--',
    label='Position'
)
ax_position.set_ylabel("Position")
ax_position.invert_yaxis() # P1 at the top

# Combine legends for plot 1
lines, labels = ax_laptime.get_legend_handles_labels()
lines2, labels2 = ax_position.get_legend_handles_labels()
ax_laptime.legend(lines + lines2, labels + labels2, loc='upper left')


# --- PLOT 2: Telemetry - Speed (Full Width) ---
ax_speed = fig.add_subplot(gs[1, :]) # Row 1, all columns
ax_speed.set_title(f"Fastest Lap ({fastest_lap['LapTime']}) Telemetry - Speed", fontsize=16)
ax_speed.plot(telemetry['Distance'], telemetry['Speed'], color='blue', label='Speed (km/h)')
ax_speed.set_xlabel("Distance (m)")
ax_speed.set_ylabel("Speed (km/h)")
ax_speed.legend()


# --- PLOT 3: Telemetry - Inputs (Full Width) ---
ax_inputs = fig.add_subplot(gs[2, :]) # Row 2, all columns
ax_inputs.set_title("Fastest Lap Telemetry - Driver Inputs", fontsize=16)
ax_inputs.plot(telemetry['Distance'], telemetry['Throttle'], color='green', label='Throttle (%)')
ax_inputs.plot(telemetry['Distance'], telemetry['Brake'], color='red', label='Brake (On/Off)')
ax_inputs.set_xlabel("Distance (m)")
ax_inputs.set_ylabel("Input (%)")
ax_inputs.legend()


# --- PLOT 4: Telemetry - Gear & RPM (Full Width) ---
ax_gear = fig.add_subplot(gs[3, :]) # Row 3, all columns
ax_gear.set_title("Fastest Lap Telemetry - Gear & RPM", fontsize=16)
ax_gear.plot(telemetry['Distance'], telemetry['nGear'], color='purple', label='Gear')
ax_gear.set_xlabel("Distance (m)")
ax_gear.set_ylabel("Gear")

ax_rpm = ax_gear.twinx()
ax_rpm.plot(telemetry['Distance'], telemetry['RPM'], color='orange', linestyle='--', label='RPM')
ax_rpm.set_ylabel("RPM")

# Combine legends for Gear & RPM
lines, labels = ax_gear.get_legend_handles_labels()
lines2, labels2 = ax_rpm.get_legend_handles_labels()
ax_gear.legend(lines + lines2, labels + labels2, loc='upper left')


# --- PLOT 5: Track Map (Bottom Left) ---
ax_track = fig.add_subplot(gs[4, 0]) # Row 4, Column 0
ax_track.set_title("Fastest Lap - Speed Trace", fontsize=16)

# Get X, Y, and Speed data from telemetry
x = telemetry['X']
y = telemetry['Y']
color = telemetry['Speed']

# Create a set of line segments
points = np.array([x, y]).T.reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)

# Create a colormap
cmap = plt.colormaps.get_cmap('plasma')
norm = plt.Normalize(color.min(), color.max())
lc = LineCollection(segments, cmap=cmap, norm=norm, linestyle='-', linewidth=2)

# Set the values used for colormapping
lc.set_array(color)

# Add the line collection to the axis
line = ax_track.add_collection(lc)

# Add a color bar
cbaxes = fig.add_axes([0.1, 0.05, 0.3, 0.01]) # [left, bottom, width, height]
legend = fig.colorbar(line, cax=cbaxes, orientation="horizontal")
legend.set_label("Speed (km/h)")

# Clean up the track plot
ax_track.axis('equal')
ax_track.set_xlabel("")
ax_track.set_ylabel("")
ax_track.set_xticks([])
ax_track.set_yticks([])


# --- PLOT 6: Weather Data (Bottom Right) ---
ax_weather = fig.add_subplot(gs[4, 1]) # Row 4, Column 1
ax_weather.set_title("Weather During Race", fontsize=16)
# Get the weather data from the session
weather_data = session.weather_data
ax_weather.plot(weather_data['Time'], weather_data['AirTemp'], color='red', label='Air Temp (°C)')
ax_weather.plot(weather_data['Time'], weather_data['TrackTemp'], color='blue', label='Track Temp (°C)')
ax_weather.set_xlabel("Time") # Correct X-axis
ax_weather.set_ylabel("Temperature (°C)")
ax_weather.legend()


# --- Save the Dashboard ---
plt.tight_layout(rect=[0, 0.03, 1, 0.97]) # Adjust layout
plt.savefig('f1_dashboard.png', dpi=300) # Save with high resolution
print("\nDashboard saved as 'f1_dashboard.png'")