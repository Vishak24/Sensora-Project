#include <Arduino.h>

// Define the analog pin connected to the turbidity sensor's output
const int sensorPin = A0;

// --- Calibrated Values ---
// Voltage from sensor when placed in clear water.
const float VOLTAGE_CLEAR = 3.63; 
const float NTU_CLEAR = 0.0;

// Voltage from sensor when placed in very turbid water.
const float VOLTAGE_TURBID = 2.0; 
const float NTU_TURBID = 650.0;

// Function to map a float value from one range to another (linear interpolation)
float fmap(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

void setup() {
  // Initialize serial communication to view the output on your computer
  Serial.begin(9600); 
  Serial.println("Turbidity Sensor Measurement (NTU)");
}

void loop() {
  // Read the raw analog value from the sensor (0-1023)
  int sensorValue = analogRead(sensorPin);
  
  // Convert the analog reading to a voltage (0-5V)
  float voltage = sensorValue * (5.0 / 1024.0);

  // Convert voltage to NTU using linear mapping based on your calibration points.
  // Note: The input range is from high voltage (clear) to low voltage (turbid)
  // because the sensor's output is inversely proportional to turbidity.
  float ntu = fmap(voltage, VOLTAGE_CLEAR, VOLTAGE_TURBID, NTU_CLEAR, NTU_TURBID);

  // Constrain the output to be within your calibrated range to avoid strange values.
  ntu = constrain(ntu, NTU_CLEAR, NTU_TURBID);

  // Print the calculated voltage and NTU value
  Serial.print("Voltage: ");
  Serial.print(voltage, 2); // Print voltage with 2 decimal places
  Serial.print(" V, ");
  Serial.print("Turbidity: ");
  Serial.print(ntu, 0); // Print NTU as a whole number
  Serial.println(" NTU");
  
  // Wait for a second before tak