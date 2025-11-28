#ifndef COMM_API_H
#define COMM_API_H

#include "arduino_platform.h"
#include <ArduinoJson.h>

#include "eeprom_manager.h"

class CommAPI {
public:
    CommAPI(Stream &serialStream);
    void begin(Stream &serialStream, bool factoryResetOccurred = false);
    void process();

    void sendData();                           // Live data (plate temp, rectal, PID, pust)
    void sendPIDParams();                      // Kp, Ki, Kd, MaxOutput
    void sendStatus();                         // Full systemstatus
    void sendStatus(const char* key, float value);   // Overbelastet for JSON
    void sendStatus(const char* key, int value);     // Overbelastet for JSON
    void sendStatus(const char* key, double value);  // Ny – støtter double
    void sendConfig();                         // Konfig (inkl. EEPROM)
    void sendResponse(const String &message);
    void sendEvent(const String &eventMessage);
    void saveAllToEEPROM();                    // Kalles ved "save_eeprom"

    void sendFailsafeStatus();                 // Eksplisitt failsafe-status

private:
    void handleCommand(const String &jsonString);
    void parseProfile(JsonArray arr);
    void sendCalibrationTable(uint8_t sensorId, const char *sensorName);

    Stream *serial;
    String buffer;
};

#endif
