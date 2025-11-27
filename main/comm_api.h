#ifndef COMM_API_H
#define COMM_API_H

#include "arduino_platform.h"
#include <ArduinoJson.h>

class CommAPI {
public:
    CommAPI(Stream &serialStream);
    void begin(Stream &serialStream, bool factoryResetOccurred = false);
    void process();

    void sendData();             // Live data (plate temp, rectal temp, PID output)
    void sendPIDParams();        // PID parameters
    void sendStatus();           // System status snapshot
    void sendStatus(const char* key, float value);
    void sendStatus(const char* key, int value);
    void sendStatus(const char* key, double value);
    void sendConfig();           // Configuration values
    void sendResponse(const String &message);
    void sendEvent(const String &eventMessage);
    void saveAllToEEPROM();      // Persist core parameters

    void sendFailsafeStatus();   // Explicit failsafe status

private:
    void handleCommand(const String &jsonString);

    Stream *serial;
    String buffer;
};

#endif
