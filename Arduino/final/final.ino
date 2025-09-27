/*
  Combined TDS and Turbidity Sensor Program
  - Reads a TDS sensor on pin A1 and a Turbidity sensor on pin A0.
  - Calculates TDS in PPM and Turbidity in NTU.
  - Sends the data as a comma-separated string "TDS,NTU" every second.
*/

// --- Pin Definitions ---
#define TDS_SENSOR_PIN A1
#define TURBIDITY_SENSOR_PIN A0

// --- General Settings ---
#define VREF 5.0 // Voltage reference for Arduino ADC

// --- TDS Sensor Specific Variables ---
#define SCOUNT 30 // Number of samples for TDS averaging
int analogBuffer[SCOUNT];
int analogBufferIndex = 0;

// --- Turbidity Sensor Specific Variables ---
// Calibrated values for your specific turbidity sensor
const float VOLTAGE_CLEAR = 3.670; 
const float NTU_CLEAR = 1.0;
const float VOLTAGE_TURBID = 2.0;
const float NTU_TURBID = 650.0;

// Helper function to map float values (used by turbidity sensor)
float fmap(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

void setup() {
  Serial.begin(9600);
  pinMode(TDS_SENSOR_PIN, INPUT);
}

void loop() {
  // === Non-blocking Timers using millis() ===
  static unsigned long tdsSampleTime = millis();
  static unsigned long mainPrintTime = millis();

  // 1. Take a TDS sample every 40ms to fill its buffer
  if (millis() - tdsSampleTime > 40U) {
    tdsSampleTime = millis();
    analogBuffer[analogBufferIndex++] = analogRead(TDS_SENSOR_PIN);
    if (analogBufferIndex == SCOUNT) {
      analogBufferIndex = 0;
    }
  }

  // 2. Calculate and print all sensor data every 1000ms (1 second)
  if (millis() - mainPrintTime > 1000U) {
    mainPrintTime = millis();

    // --- A: Calculate TDS Value ---
    // Create a temporary sorted buffer to remove outliers
    int tempBuffer[SCOUNT];
    for (int i = 0; i < SCOUNT; i++) tempBuffer[i] = analogBuffer[i];
    for (int i = 0; i < SCOUNT - 1; i++) {
      for (int j = 0; j < SCOUNT - i - 1; j++) {
        if (tempBuffer[j] > tempBuffer[j + 1]) {
          int temp = tempBuffer[j];
          tempBuffer[j] = tempBuffer[j + 1];
          tempBuffer[j + 1] = temp;
        }
      }
    }
    // Average the middle 50% of readings
    unsigned long avgValue = 0;
    for (int i = SCOUNT / 4; i < SCOUNT * 3 / 4; i++) {
      avgValue += tempBuffer[i];
    }
    float averageAnalog = (float)avgValue / (SCOUNT / 2);
    float averageVoltage = averageAnalog * VREF / 1024.0;
    // Temperature compensation is hardcoded to 25°C
    float compensationCoefficient = 1.0 + 0.02 * (25.0 - 25.0); 
    float compensationVoltage = averageVoltage / compensationCoefficient;
    float tdsValue = (133.42 * pow(compensationVoltage, 3) - 255.86 * pow(compensationVoltage, 2) + 857.39 * compensationVoltage) * 0.5;

    // --- B: Calculate Turbidity (NTU) Value ---
    int turbidityAnalogVal = analogRead(TURBIDITY_SENSOR_PIN);
    float turbidityVoltage = turbidityAnalogVal * (VREF / 1024.0);
    float ntuValue = fmap(turbidityVoltage, VOLTAGE_CLEAR, VOLTAGE_TURBID, NTU_CLEAR, NTU_TURBID);
    ntuValue = constrain(ntuValue, NTU_CLEAR, NTU_TURBID); // Ensure value is within calibrated range

    // --- C: Send final data to Python ---
    // Format: "TDS,NTU"
    Serial.print(tdsValue, 0); // Print TDS as a whole number
    Serial.print(",");
    Serial.println(ntuValue, 2); // Print NTU as a whole number and add newline
  }
}