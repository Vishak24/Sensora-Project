// --- Voltage Measurement Utility ---
#define TURBIDITY_SENSOR_PIN A0
#define VREF 5.0

void setup() {
  Serial.begin(9600);
}

void loop() {
  // Read the raw analog value and convert it to voltage
  int sensorValue = analogRead(TURBIDITY_SENSOR_PIN);
  float voltage = sensorValue * (VREF / 1024.0);
  
  // Print the voltage continuously
  Serial.print("Current Turbidity Voltage: ");
  Serial.println(voltage, 3); // Print with 3 decimal places for precision
  
  delay(1000);
}