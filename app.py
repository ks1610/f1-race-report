import fastf1
import fastf1.plotting
from matplotlib import pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.collections import LineCollection
import numpy as np
import io
import base64
import datetime
import pandas as pd # Import pandas
from flask import Flask, render_template, request
import os

# 1. Setup Flask App
app = Flask(__name__)

# 2. Setup fastf1 and enable cache (must be a folder named 'cache')
#fastf1.plotting.setup_mpl()
fastf1.plotting.setup_mpl(dark=True)
cache_dir = 'cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache('cache')

# 3. YOUR DASHBOARD SCRIPT (Converted to a function)
# This function is now only used for a SINGLE driver
def create_dashboard(year, race, driver):
    """
    Generates the F1 dashboard for a single driver
    and returns it as a Base64 encoded image.
    """
    try:
        # --- 2. Load the session ---
        session = fastf1.get_session(year, race, 'R')
        session.load(telemetry=True)

        # --- 3. Get driver data ---
        driver_laps = session.laps.pick_drivers(driver)

        if not len(driver_laps):
            return None, f"Error: No data found for driver {driver}."

        # --- NEW: Add error checking for fastest lap ---
        fastest_lap = driver_laps.pick_fastest()
        if fastest_lap is None or fastest_lap.empty:
            return None, f"Error: No completed lap data found for {driver} (e.g., DNF on Lap 1)."
            
        telemetry = fastest_lap.get_telemetry()
        if telemetry is None or telemetry.empty:
             return None, f"Error: No telemetry data found for {driver}'s fastest lap."
        
        # --- 4. Define the plotting layout (Dashboard) ---
        fig = plt.figure(figsize=(20, 25))
        gs = fig.add_gridspec(5, 2) # 5 rows, 2 columns

        # Get event date for title
        event_date = session.event.EventDate.strftime('%b %d')
        fig.suptitle(
            f"F1 Data Dashboard: {driver} - {session.event.year} {session.event['EventName']} ({event_date}) - Race",
            fontsize=24,
            fontweight='bold'
        )

        # --- PLOT 1: Lap Times & Position (Full Width) ---
        ax_laptime = fig.add_subplot(gs[0, :])
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
        
        ax_position = ax_laptime.twinx()
        ax_position.plot(
            driver_laps['LapNumber'],
            driver_laps['Position'],
            color='grey',
            linestyle='--',
            label='Position'
        )
        ax_position.set_ylabel("Position")
        ax_position.invert_yaxis()
        
        lines, labels = ax_laptime.get_legend_handles_labels()
        lines2, labels2 = ax_position.get_legend_handles_labels()
        ax_laptime.legend(lines + lines2, labels + labels2, loc='upper left')

        # --- PLOT 2: Telemetry - Speed ---
        ax_speed = fig.add_subplot(gs[1, :])
        ax_speed.set_title(f"Fastest Lap ({fastest_lap['LapTime']}) Telemetry - Speed", fontsize=16)
        ax_speed.plot(telemetry['Distance'], telemetry['Speed'], color='blue', label='Speed (km/h)')
        ax_speed.set_xlabel("Distance (m)")
        ax_speed.set_ylabel("Speed (km/h)")
        ax_speed.legend()

        # --- PLOT 3: Telemetry - Inputs ---
        ax_inputs = fig.add_subplot(gs[2, :])
        ax_inputs.set_title("Fastest Lap Telemetry - Driver Inputs", fontsize=16)
        ax_inputs.plot(telemetry['Distance'], telemetry['Throttle'], color='green', label='Throttle (%)')
        ax_inputs.plot(telemetry['Distance'], telemetry['Brake'], color='red', label='Brake (On/Off)')
        ax_inputs.set_xlabel("Distance (m)")
        ax_inputs.set_ylabel("Input (%)")
        ax_inputs.legend()

        # --- PLOT 4: Telemetry - Gear & RPM ---
        ax_gear = fig.add_subplot(gs[3, :])
        ax_gear.set_title("Fastest Lap Telemetry - Gear & RPM", fontsize=16)
        ax_gear.plot(telemetry['Distance'], telemetry['nGear'], color='purple', label='Gear')
        ax_gear.set_xlabel("Distance (m)")
        ax_gear.set_ylabel("Gear")
        
        ax_rpm = ax_gear.twinx()
        ax_rpm.plot(telemetry['Distance'], telemetry['RPM'], color='orange', linestyle='--', label='RPM')
        ax_rpm.set_ylabel("RPM")
        
        lines, labels = ax_gear.get_legend_handles_labels()
        lines2, labels2 = ax_rpm.get_legend_handles_labels()
        ax_gear.legend(lines + lines2, labels + labels2, loc='upper left')

        # --- PLOT 5: Track Map ---
        ax_track = fig.add_subplot(gs[4, 0])
        ax_track.set_title("Fastest Lap - Speed Trace", fontsize=16)
        x = telemetry['X']
        y = telemetry['Y']
        color = telemetry['Speed']
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        cmap = plt.colormaps.get_cmap('plasma')
        norm = plt.Normalize(color.min(), color.max())
        lc = LineCollection(segments, cmap=cmap, norm=norm, linestyle='-', linewidth=2)
        lc.set_array(color)
        line = ax_track.add_collection(lc)
        cbaxes = fig.add_axes([0.1, 0.05, 0.3, 0.01])
        legend = fig.colorbar(line, cax=cbaxes, orientation="horizontal")
        legend.set_label("Speed (km/h)")
        ax_track.axis('equal')
        ax_track.set_xticks([])
        ax_track.set_yticks([])

        # --- PLOT 6: Weather Data ---
        ax_weather = fig.add_subplot(gs[4, 1])
        ax_weather.set_title("Weather During Race", fontsize=16)
        weather_data = session.weather_data
        ax_weather.plot(weather_data['Time'], weather_data['AirTemp'], color='red', label='Air Temp (°C)')
        ax_weather.plot(weather_data['Time'], weather_data['TrackTemp'], color='blue', label='Track Temp (°C)')
        ax_weather.set_xlabel("Time")
        ax_weather.set_ylabel("Temperature (°C)")
        ax_weather.legend()

        # --- Save plot to in-memory buffer ---
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=200) # Use lower DPI for web
        
        # Encode to Base64
        data = base64.b64encode(buf.getbuffer()).decode('ascii')
        plt.close(fig) # Close figure to free memory
        
        return f"data:image/png;base64,{data}", None

    except Exception as e:
        plt.close('all') # Close any open figures on error
        print(f"Error generating dashboard: {e}")
        return None, f"An error occurred: {e}. The driver may not have data for this session."

# 4. --- NEW FUNCTION (CORRECTED) ---
def get_race_results(year, race):
    """
    Gets the final race results for ALL drivers.
    Returns a list of dictionaries.
    """
    try:
        session = fastf1.get_session(year, race, 'R')
        session.load(telemetry=False, weather=False, messages=False, laps=True) # Light load

        # Get the results DataFrame
        results = session.results

        # --- START FIX ---
        
        # Convert Time (timedelta) to a readable string
        if 'Time' in results.columns:
            results['Time'] = results['Time'].apply(lambda x: str(x).split('days ')[-1] if pd.notna(x) else 'N/A')

        # Convert Position to integer
        results['Position'] = results['Position'].astype(int)

        # Select the columns we need, using their *correct* names
        # The correct names are 'Abbreviation' and 'TeamName'
        final_cols = ['Position', 'FullName', 'Abbreviation', 'TeamName', 'Laps', 'Time', 'Status', 'Points']
        
        # Check if all columns exist
        missing_cols = [col for col in final_cols if col not in results.columns]
        if missing_cols:
            raise Exception(f"Data is missing columns: {', '.join(missing_cols)}")
            
        results_data = results[final_cols]
        
        # Rename columns to match what the HTML template expects ('Driver' and 'Team')
        results_data = results_data.rename(columns={
            'Abbreviation': 'Driver',
            'TeamName': 'Team',
            'FullName': 'FullName'  # Explicitly pass 'FullName'
        })
        
        # --- END FIX ---
        
        # Convert DataFrame to a list of dictionaries for the template
        return results_data.to_dict('records'), None
        
    except Exception as e:
        plt.close('all')
        print(f"Error getting race results: {e}")
        return None, f"An error occurred: {e}. Could not load results."


# 5. FLASK ROUTE: The main webpage (UPDATED)
@app.route('/')
def index():
    # Get values from URL (e.g., /?year=2024)
    selected_year = request.args.get('year', type=int)
    selected_race = request.args.get('race')
    selected_driver = request.args.get('driver')

    # Data lists for dropdowns
    years_list = list(range(datetime.datetime.now().year, 2017, -1)) # 2018 is first year
    races_list = []
    drivers_list = []
    
    # --- NEW: Add a variable for results data ---
    plot_data = None
    results_data = None
    error = None

    try:
        if selected_year:
            # Year is selected, get the race schedule
            schedule = fastf1.get_event_schedule(selected_year, include_testing=False)
            races_list = schedule['EventName'].tolist()

        if selected_year and selected_race:
            # Race is selected, get the driver list
            session = fastf1.get_session(selected_year, selected_race, 'R')
            session.load(laps=True, telemetry=False, weather=False, messages=False)
            drivers_list = sorted(session.laps['Driver'].unique().tolist())

        if selected_year and selected_race and selected_driver:
            # --- NEW: Logic to check "ALL" vs. single driver ---
            if selected_driver == "ALL":
                # User wants the results table
                results_data, error = get_race_results(selected_year, selected_race)
            else:
                # User wants the single-driver dashboard
                plot_data, error = create_dashboard(selected_year, selected_race, selected_driver)
            
    except Exception as e:
        print(f"Error in web route: {e}")
        error = f"An error occurred: {e}. Please check your selections."

    # Render the HTML page, passing in all our data
    return render_template('index.html',
                           years=years_list,
                           races=races_list,
                           drivers=drivers_list,
                           selected_year=selected_year,
                           selected_race=selected_race,
                           selected_driver=selected_driver,
                           plot_data=plot_data,
                           results_data=results_data, # Pass results data to template
                           error=error)

# 6. Run the App
if __name__ == '__main__':
    app.run(debug=True)