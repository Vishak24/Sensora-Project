import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("Generating RECALIBRATED 'Core Two' synthetic dataset...")

# --- 1. Create a Time Series for 30 days ---
time_index = pd.to_datetime(pd.date_range(start='2025-09-01 00:00', end='2025-10-01 00:00', freq='15min'), utc=True).tz_convert('Asia/Kolkata')
n_points = len(time_index)
df = pd.DataFrame({'timestamp': time_index})

# --- 2. RECALIBRATED "Normal" Baseline Data ---
# Based on your real-world readings of ~120 EC and ~5 NTU.
# We'll set the baseline a little lower than 5 NTU so that 5 is seen as a moderate deviation.
df['ec'] = np.random.normal(120, 20, n_points)      # NEW BASELINE
df['turbidity'] = np.random.normal(2.5, 0.5, n_points) # NEW BASELINE
df['LABEL'] = 'Normal'
print("Generated 'Normal' baseline data based on real-world values.")

# --- 3. Inject Programmed "Contamination Events" ---

# Event 1: E. coli Risk (Turbidity spike from the NEW baseline)
start_idx = int(n_points * 0.1)
duration = 48
end_idx = start_idx + duration
df.iloc[start_idx:end_idx, df.columns.get_loc('turbidity')] += np.linspace(20, 1, duration) * np.random.uniform(0.9, 1.1, duration)
df.iloc[start_idx:end_idx, df.columns.get_loc('ec')] -= 30 # Less dilution for lower EC water
df.iloc[start_idx:end_idx, df.columns.get_loc('LABEL')] = 'Bacterial_Risk_Ecoli'
print("Injected 'Bacterial_Risk_Ecoli' event.")

# Event 2: Geochemical Risk (Slight EC rise with very clear water)
start_idx = int(n_points * 0.2)
duration = 96
end_idx = start_idx + duration
df.iloc[start_idx:end_idx, df.columns.get_loc('ec')] += np.random.normal(50, 10, duration)
df.iloc[start_idx:end_idx, df.columns.get_loc('turbidity')] = np.random.normal(0.2, 0.05, duration)
df.iloc[start_idx:end_idx, df.columns.get_loc('LABEL')] = 'Geochemical_Risk_Arsenic_Iron'
print("Injected 'Geochemical_Risk' event.")

# Event 3: High Hardness State
start_idx = int(n_points * 0.65)
duration = 192
end_idx = start_idx + duration
df.iloc[start_idx:end_idx, df.columns.get_loc('ec')] = np.random.normal(1800, 100, duration)
df.iloc[start_idx:end_idx, df.columns.get_loc('LABEL')] = 'Aesthetic_Risk_Hardness'
print("Injected 'Aesthetic_Risk_Hardness' event.")

# Event 4: Chloride Risk (Saltwater Intrusion)
start_idx = int(n_points * 0.8)
duration = n_points - start_idx
df.iloc[start_idx:, df.columns.get_loc('ec')] += np.linspace(100, 1500, duration)
df.iloc[start_idx:, df.columns.get_loc('LABEL')] = 'Intrusion_Risk_Chloride'
print("Injected 'Intrusion_Risk_Chloride' event.")


# --- 4. Engineer Features ---
df = df.set_index('timestamp')
df['ec_delta_1h'] = df['ec'].diff(periods=4)
df['turbidity_delta_1h'] = df['turbidity'].diff(periods=4)
df['ec_avg_24h'] = df['ec'].rolling(window=96).mean()
df['turbidity_avg_24h'] = df['turbidity'].rolling(window=96).mean()
df.dropna(inplace=True)

# --- 5. Save the Final Dataset ---
df.to_csv('labeled_training_data_recalibrated.csv')
print("\nRecalibrated synthetic dataset created successfully!")
print("Here is a summary of the events created:")
print(df['LABEL'].value_counts())

# --- 6. Visualize the Data to Confirm ---
print("\nDisplaying plot of generated data...")
df[['ec', 'turbidity']].plot(subplots=True, figsize=(15, 6), title="Recalibrated 'Core Two' Sensor Data with Injected Events")
plt.xlabel("Timestamp")
plt.tight_layout() # Adjusts plot to prevent labels from overlapping
plt.show()