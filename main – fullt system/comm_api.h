#ifndef COMM_API_H
#define COMM_API_H

#include <Arduino.h>
#include <ArduinoJson.h>

class CommAPI {
public:
    CommAPI(Stream &serialStream);
    void begin(Stream &serialStream, bool factoryResetOccurred = false);
    void process();

    void sendData();
    void sendPIDParams();
    void sendStatus();
    void sendResponse(const String &message);

    // ➕ Disse mangler i din nåværende header:
    void sendEvent(const String &eventMessage);
    void sendConfig();
    void saveAllToEEPROM();

private:
    void handleCommand(const String &jsonString);
    void parseProfile(JsonArray arr);

    Stream *serial;
    String buffer;
};

#endif
