import serial
import pandas as pd
import joblib
import time
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, jsonify
from flask_cors import CORS
import threading

# --- 1. Configuration ---
SERIAL_PORT = '/dev/tty.usbserial-1120' # ❗️ UPDATE this to your Arduino's port
BAUD_RATE = 9600
MODEL_FILE_PATH = 'water_risk_model_core_two.pkl'
FEATURES_ORDER = ['ec', 'turbidity', 'ec_delta_1h', 'turbidity_delta_1h', 'ec_avg_24h', 'turbidity_avg_24h']

# --- 2. Global State for Data ---
# This dictionary will hold the latest data for the frontend
latest_data = {
    "ec": 0,
    "turbidity": 0,
    "quality_score": 0,
    "status": "Initializing...",
    "risk_breakdown": {},
    "last_updated": "N/A",
    "connected": False
}

history_df = pd.DataFrame(columns=['timestamp', 'ec', 'turbidity'])

# --- 3. Feature Calculation Logic ---
def calculate_features(current_ec, current_turbidity):
    global history_df
    now = datetime.now()
    new_row = pd.DataFrame([{'timestamp': now, 'ec': current_ec, 'turbidity': current_turbidity}])
    history_df = pd.concat([history_df, new_row], ignore_index=True)
    history_df = history_df[history_df['timestamp'] > (now - timedelta(hours=25))]

    one_hour_ago = now - timedelta(hours=1)
    twenty_four_hours_ago = now - timedelta(hours=24)
    past_1h_reading = history_df.iloc[(history_df['timestamp'] - one_hour_ago).abs().argsort()[:1]]
    last_24h_df = history_df[history_df['timestamp'] > twenty_four_hours_ago]

    ec_delta_1h = current_ec - past_1h_reading['ec'].iloc[0] if not past_1h_reading.empty else 0
    turbidity_delta_1h = current_turbidity - past_1h_reading['turbidity'].iloc[0] if not past_1h_reading.empty else 0
    ec_avg_24h = last_24h_df['ec'].mean() if not last_24h_df.empty else current_ec
    turbidity_avg_24h = last_24h_df['turbidity'].mean() if not last_24h_df.empty else current_turbidity

    live_df = pd.DataFrame([{'ec': current_ec, 'turbidity': current_turbidity, 'ec_delta_1h': ec_delta_1h, 'turbidity_delta_1h': turbidity_delta_1h, 'ec_avg_24h': ec_avg_24h, 'turbidity_avg_24h': turbidity_avg_24h}])
    return live_df[FEATURES_ORDER]

# --- 4. Arduino and AI Prediction Loop (Runs in a separate thread) ---
def prediction_loop():
    global latest_data
    
    try:
        model = joblib.load(MODEL_FILE_PATH)
        model_classes = model.classes_
        print("✅ AI model loaded successfully.")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    while True:
        ser = None
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
            print(f"✅ Connected to Arduino on {SERIAL_PORT}.")
            latest_data["connected"] = True
            time.sleep(2)
            
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    parts = line.split(',')
                    if len(parts) == 2:
                        ec_val = float(parts[0])
                        turbidity_val = float(parts[1])

                        live_features_df = calculate_features(ec_val, turbidity_val)
                        probabilities = model.predict_proba(live_features_df)[0]
                        
                        normal_proba = 0
                        try:
                            normal_index = np.where(model_classes == 'Normal')[0][0]
                            normal_proba = probabilities[normal_index]
                        except (IndexError, ValueError):
                            pass

                        quality_score = int(normal_proba * 100)
                        
                        status = "High Risk"
                        if quality_score > 80: status = "Low Risk"
                        elif quality_score > 40: status = "Moderate Risk"
                        
                        risk_breakdown = {model_classes[i]: probabilities[i] * 100 for i in range(len(model_classes))}

                        # Update the global state
                        latest_data.update({
                            "ec": ec_val,
                            "turbidity": turbidity_val,
                            "quality_score": quality_score,
                            "status": status,
                            "risk_breakdown": risk_breakdown,
                            "last_updated": datetime.now().strftime("%I:%M:%S %p"),
                            "connected": True
                        })

        except serial.SerialException:
            print(f"🔌 Arduino disconnected or not found on {SERIAL_PORT}. Retrying in 5 seconds...")
            latest_data["connected"] = False
            if ser and ser.is_open:
                ser.close()
            time.sleep(5)
        except Exception as e:
            print(f"An error occurred in the prediction loop: {e}")
            latest_data["connected"] = False
            time.sleep(5)

# --- 5. Flask Web Server ---
app = Flask(__name__)
CORS(app) # Allows the frontend to fetch data

@app.route('/data')
def get_data():
    """Endpoint for the frontend to get the latest data."""
    return jsonify(latest_data)

if __name__ == '__main__':
    # Start the prediction loop in a background thread
    prediction_thread = threading.Thread(target=prediction_loop, daemon=True)
    prediction_thread.start()
    
    # Run the Flask web server
    app.run(port=5000)