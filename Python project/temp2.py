import serial
import pandas as pd
import joblib
import time
import numpy as np
import os
from datetime import datetime, timedelta

# --- 1. Configuration ---
# ❗️ UPDATE this to your Arduino's serial port
SERIAL_PORT = '/dev/tty.usbserial-1120' 
BAUD_RATE = 9600
MODEL_FILE_PATH = 'water_risk_model_core_two.pkl'
FEATURES_ORDER = ['ec', 'turbidity', 'ec_delta_1h', 'turbidity_delta_1h', 'ec_avg_24h', 'turbidity_avg_24h']

# --- 2. Data History and Feature Calculation ---
# This DataFrame will store sensor readings to calculate historical features
history_df = pd.DataFrame(columns=['timestamp', 'ec', 'turbidity'])

def calculate_features(current_ec, current_turbidity):
    """
    Stores the latest sensor reading and calculates the six features
    required by the AI model, matching the training script's logic.
    """
    global history_df
    now = datetime.now()

    # Add current reading to our history
    new_row = pd.DataFrame([{'timestamp': now, 'ec': current_ec, 'turbidity': current_turbidity}])
    history_df = pd.concat([history_df, new_row], ignore_index=True)

    # Prune old data to save memory (keep the last 25 hours)
    history_df = history_df[history_df['timestamp'] > (now - timedelta(hours=25))]

    # --- Feature Engineering ---
    one_hour_ago = now - timedelta(hours=1)
    twenty_four_hours_ago = now - timedelta(hours=24)

    # Find the closest reading to one hour ago to calculate the delta
    past_1h_reading = history_df.iloc[(history_df['timestamp'] - one_hour_ago).abs().argsort()[:1]]
    
    # Get all readings from the last 24 hours for the average
    last_24h_df = history_df[history_df['timestamp'] > twenty_four_hours_ago]

    # Calculate deltas (if not enough history, default to 0)
    ec_delta_1h = current_ec - past_1h_reading['ec'].iloc[0] if not past_1h_reading.empty else 0
    turbidity_delta_1h = current_turbidity - past_1h_reading['turbidity'].iloc[0] if not past_1h_reading.empty else 0
    
    # Calculate 24-hour averages (if not enough history, use the current value)
    ec_avg_24h = last_24h_df['ec'].mean() if not last_24h_df.empty else current_ec
    turbidity_avg_24h = last_24h_df['turbidity'].mean() if not last_24h_df.empty else current_turbidity

    # Create a DataFrame with the features in the correct order for the model
    live_df = pd.DataFrame([{
        'ec': current_ec, 'turbidity': current_turbidity,
        'ec_delta_1h': ec_delta_1h, 'turbidity_delta_1h': turbidity_delta_1h,
        'ec_avg_24h': ec_avg_24h, 'turbidity_avg_24h': turbidity_avg_24h
    }])
    
    return live_df[FEATURES_ORDER]

# --- 3. Main Application ---
def main():
    """Main function to load the model, connect to Arduino, and run predictions."""
    try:
        model = joblib.load(MODEL_FILE_PATH)
        model_classes = model.classes_
        print("✅ AI model loaded successfully.")
        print(f"   Model is trained to predict: {list(model_classes)}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Connected to Arduino on {SERIAL_PORT}.")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Error connecting to Arduino: {e}")
        return

    print("\n🚀 Starting real-time prediction loop... Press Ctrl+C to exit.")
    print("Note: Predictions become more accurate after 24 hours of data collection.")

    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if line:
                os.system('cls' if os.name == 'nt' else 'clear')
                print("🚀 Real-Time Water Quality Monitor")
                print("------------------------------------")
                
                parts = line.split(',')
                if len(parts) == 2:
                    ec_val = float(parts[0])
                    turbidity_val = float(parts[1])

                    print(f"Received Raw Data: EC={ec_val:.2f}, Turbidity={turbidity_val:.2f}")

                    # Calculate features correctly using historical data
                    live_features_df = calculate_features(ec_val, turbidity_val)
                    
                    # Get probabilities for all classes from the model
                    probabilities = model.predict_proba(live_features_df)[0]
                    
                    # Calculate the overall score based on the 'Normal' class probability
                    normal_proba = 0
                    try:
                        normal_index = np.where(model_classes == 'Normal')[0][0]
                        normal_proba = probabilities[normal_index]
                    except (IndexError, ValueError):
                        print("Warning: 'Normal' class not found in model's classes.")

                    quality_score = int(normal_proba * 100)
                    
                    # Determine status based on the score
                    status = "Bad 🔴"
                    if quality_score > 80: status = "Good 🟢"
                    elif quality_score > 40: status = "Moderate 🟡"

                    print("\n--- OVERALL ASSESSMENT ---")
                    print(f"Water Quality Score: {quality_score}%")
                    print(f"Status: {status}")

                    print("\n--- RISK FACTOR ANALYSIS ---")
                    risk_breakdown = {model_classes[i]: probabilities[i] * 100 for i in range(len(model_classes))}
                    sorted_risks = sorted(risk_breakdown.items(), key=lambda item: item[1], reverse=True)

                    for risk, probability in sorted_risks:
                        if probability > 0.1: # Only show risks with meaningful probability
                            print(f"{risk.replace('_', ' '):<35}: {probability:.1f}%")

                else:
                    print(f"Warning: Received malformed data: {line}")
                
                print("------------------------------------")
                time.sleep(1) # Small delay to prevent flickering

        except KeyboardInterrupt:
            print("\nExiting program.")
            break
        except (ValueError, IndexError):
            # Catches errors if the Arduino sends incomplete data, common on startup
            time.sleep(1)
            continue
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    ser.close()
    print("Serial connection closed.")

if __name__ == "__main__":
    main()