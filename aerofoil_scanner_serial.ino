#include <Wire.h>
#include <SensirionI2CSdp.h>

#define PCA9548A_ADDR 0x70
#define NUM_SENSORS 5

SensirionI2CSdp sdp[NUM_SENSORS];
bool sensorOK[NUM_SENSORS];

void selectChannel(uint8_t channel)
{
    Wire.beginTransmission(PCA9548A_ADDR);
    Wire.write(1 << channel);
    Wire.endTransmission();
}

void setup()
{
    Serial.begin(115200);
    delay(1000);
    Wire.begin(21, 22);

    // --- Confirm mux is present ---
    Wire.beginTransmission(PCA9548A_ADDR);
    if (Wire.endTransmission() == 0)
        Serial.println("# Mux found at 0x70");
    else
        Serial.println("# WARNING: Mux NOT found at 0x70 - check wiring/power");

    // --- Initialise each sensor channel ---
    for (uint8_t ch = 0; ch < NUM_SENSORS; ch++)
    {
        selectChannel(ch);
        delay(10);

        sdp[ch].begin(Wire, SDP8XX_I2C_ADDRESS_0);

        uint16_t error;
        error = sdp[ch].stopContinuousMeasurement();
        delay(10);
        error = sdp[ch].startContinuousMeasurementWithDiffPressureTCompAndAveraging();

        if (error)
        {
            Serial.print("# Channel ");
            Serial.print(ch);
            Serial.print(" Start Error: ");
            Serial.println(error);
            sensorOK[ch] = false;
        }
        else
        {
            Serial.print("# Channel ");
            Serial.print(ch);
            Serial.println(" Sensor Started Successfully!");
            sensorOK[ch] = true;
        }
    }

    // --- CSV header, prefixed so the logger can pick out real data rows ---
    Serial.println("DATA,time_ms,P_ch0,P_ch1,P_ch2,P_ch3,P_ch4");
}

void loop()
{
    Serial.print("DATA,");
    Serial.print(millis());

    for (uint8_t ch = 0; ch < NUM_SENSORS; ch++)
    {
        float pressure = NAN;
        float temperature = NAN;

        if (sensorOK[ch])
        {
            selectChannel(ch);
            uint16_t error = sdp[ch].readMeasurement(pressure, temperature);
            if (error) pressure = NAN;
        }

        Serial.print(",");
        Serial.print(pressure, 3);
    }

    Serial.println();
    delay(200);
}
