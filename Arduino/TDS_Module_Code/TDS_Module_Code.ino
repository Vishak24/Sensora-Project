/*
  TDS (Total Dissolved Solids) Sensor Reader
  
  This sketch reads the value from a gravity-style analog TDS sensor and 
  displays the TDS value in Parts Per Million (PPM) on the Serial Monitor.

  Connections:
  - TDS Sensor VCC to Arduino 5V
  - TDS Sensor GND to Arduino GND
  - TDS Sensor Analog Output (A/S) to Arduino A1
*/

// Define the analog pin where the TDS sensor is connected.
#define TDS_SENSOR_PIN A1

// Voltage reference for the ADC (Analog-to-Digital Converter). 
// 5.0V for Arduino Uno.
#define VREF 5.0

// Number of samples to take for averaging. This helps to get a more stable reading.
#define SCOUNT 30

// Array to store the analog readings for averaging.
int analogBuffer[SCOUNT]; 

// Index for the circular buffer.
int analogBufferIndex = 0;

// Variables to hold the current and average analog values.
float averageVoltage = 0;
float tdsValue = 0;

void setup() {
  // Start serial communication at 9600 baud rate for debugging.
  Serial.begin(9600);
  
  // Set the pin mode for the sensor pin.
  pinMode(TDS_SENSOR_PIN, INPUT);
}

void loop() {
  static unsigned long analogSampleTimepoint = millis();
  
  // Take a reading every 40 milliseconds.
  if (millis() - analogSampleTimepoint > 40U) {
    analogSampleTimepoint = millis();
    // Store the current reading in the buffer.
    analogBuffer[analogBufferIndex] = analogRead(TDS_SENSOR_PIN);
    // Increment the buffer index.
    analogBufferIndex++;
    // If the buffer is full, reset the index to 0 to overwrite old values.
    if (analogBufferIndex == SCOUNT) {
      analogBufferIndex = 0;
    }
  }

  static unsigned long printTimepoint = millis();

  // Print the calculated TDS value to the serial monitor every 800 milliseconds.
  if (millis() - printTimepoint > 800U) {
    printTimepoint = millis();
    
    // Create a temporary buffer to sort the readings for noise reduction.
    int tempBuffer[SCOUNT];
    for(int i=0; i<SCOUNT; i++) {
      tempBuffer[i] = analogBuffer[i];
    }

    // Sort the temporary buffer using a simple bubble sort.
    for (int i = 0; i < SCOUNT - 1; i++) {
      for (int j = 0; j < SCOUNT - i - 1; j++) {
        if (tempBuffer[j] > tempBuffer[j + 1]) {
          int temp = tempBuffer[j];
          tempBuffer[j] = tempBuffer[j + 1];
          tempBuffer[j + 1] = temp;
        }
      }
    }

    // Calculate the average of the middle range of values from the *sorted* buffer to reject outliers.
    unsigned long avgValue = 0;
    for (int i = SCOUNT/4; i < SCOUNT*3/4; i++) {
      avgValue += tempBuffer[i];
    }
    float averageAnalog = (float)avgValue / (SCOUNT / 2);

    // Convert the analog reading to voltage.
    averageVoltage = averageAnalog * VREF / 1024.0;
    
    // Convert voltage to TDS value (PPM)
    // This formula is a common approximation for many generic TDS sensors and assumes a water temperature of 25°C.
    // For accurate readings, you MUST calibrate your sensor with a standard TDS solution.
    float compensationCoefficient=1.0+0.02*(25.0-25.0); // Temperature compensation (set to 25C for simplicity)
    float compensationVoltage=averageVoltage/compensationCoefficient;
    
    tdsValue = (133.42 * compensationVoltage * compensationVoltage * compensationVoltage - 255.86 * compensationVoltage * compensationVoltage + 857.39 * compensationVoltage) * 0.5;

    // Print the results to the Serial Monitor.
    // The Raw Analog value is useful for debugging. If this is 0, check your wiring.
    Serial.print("Raw Analog: ");
    Serial.print(averageAnalog, 0);
    Serial.print("   ");
    Serial.print("Voltage: ");
    Serial.print(averageVoltage, 2);
    Serial.print("V   ");
    Serial.print("TDS Value: ");
    Serial.print(tdsValue, 0);
    Serial.println(" ppm");
  }
}