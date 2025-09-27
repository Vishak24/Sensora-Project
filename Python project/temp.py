import serial
import pandas as pd
import joblib
import time
import numpy as np
import os


SERIAL_PORT = '/dev/tty.usbserial-1120' 
BAUD_RATE = 9600

try:
    model = joblib.load('water_risk_model_core_two.pkl')
    # Get the order of the classes the model was trained on
    model_classes = model.classes_
    print("✅ AI model loaded successfully.")
    print(f"   Model is trained to predict: {list(model_classes)}")
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit()

# --- 3. Connect to the Arduino ---
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"✅ Connected to Arduino on {SERIAL_PORT}.")
    time.sleep(2) # Give the connection a moment to settle
except Exception as e:
    print(f"❌ Error connecting to Arduino: {e}")
    print("   Please check your SERIAL_PORT variable and that the Arduino is connected.")
    exit()

# --- 4. Main Loop: Listen, Predict, Display ---
print("\n🚀 Starting real-time prediction loop... Press Ctrl+C to exit.")
while True:
    try:
        # Read one line of data from the Arduino (e.g., "900.00,1.50")
        line = ser.readline().decode('utf-8').strip()

        if line:
            os.system('cls' if os.name == 'nt' else 'clear') # Clear the console for a clean view
            print("🚀 Real-Time Water Quality Monitor")
            print("------------------------------------")
            print(f"Received Raw Data: EC, Turbidity -> {line}")
            
            parts = line.split(',')
            if len(parts) == 2:
                ec_val = float(parts[0])
                turbidity_val = float(parts[1])

                # Prepare data for the model in a DataFrame
                live_df = pd.DataFrame([{'ec': ec_val, 'turbidity': turbidity_val}])
                live_df['ec_delta_1h'] = 0
                live_df['turbidity_delta_1h'] = 0
                live_df['ec_avg_24h'] = ec_val
                live_df['turbidity_avg_24h'] = turbidity_val
                features_order = ['ec', 'turbidity', 'ec_delta_1h', 'turbidity_delta_1h', 'ec_avg_24h', 'turbidity_avg_24h']
                live_df = live_df[features_order]

                # --- Get probabilities for ALL classes ---
                probabilities = model.predict_proba(live_df)[0]
                
                # --- Calculate Overall Score and Status ---
                normal_proba = 0
                try:
                    normal_index = np.where(model_classes == 'Normal')[0][0]
                    normal_proba = probabilities[normal_index]
                except IndexError: pass
                
                quality_score = int(normal_proba * 100)
                
                status = "Bad 🔴"
                if quality_score > 80:
                    status = "Good 🟢"
                elif quality_score > 40:
                    status = "Moderate 🟡"

                print("\n--- OVERALL ASSESSMENT ---")
                print(f"Water Quality Score: {quality_score}%")
                print(f"Status: {status}")
                
                # --- Create and display the detailed risk breakdown ---
                print("\n--- RISK FACTOR ANALYSIS ---")
                risk_breakdown = {model_classes[i]: probabilities[i] * 100 for i in range(len(model_classes))}
                
                # Sort by probability, descending
                sorted_risks = sorted(risk_breakdown.items(), key=lambda item: item[1], reverse=True)

                for risk, probability in sorted_risks:
                    if probability > 0.1: # Only show risks with meaningful probability
                        print(f"{risk.replace('_', ' '):<30}: {probability:.1f}%")

            else:
                print(f"Warning: Received malformed data: {line}")
            
            print("------------------------------------")

    except KeyboardInterrupt:
        print("\nExiting program.")
        break
    except Exception as e:
        print(f"An error occurred: {e}")
        break

ser.close()
print("Serial connection closed.")