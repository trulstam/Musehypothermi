#include "comm_api.h"

CommAPI::CommAPI(Stream &serialStream) { serial = &serialStream; }
void CommAPI::begin(Stream &serialStream, bool) { serial = &serialStream; }
void CommAPI::process() {}
void CommAPI::sendData() {}
void CommAPI::sendPIDParams() {}
void CommAPI::sendStatus() {}
void CommAPI::sendStatus(const char*, float) {}
void CommAPI::sendStatus(const char*, int) {}
void CommAPI::sendStatus(const char*, double) {}
void CommAPI::sendConfig() {}
void CommAPI::sendResponse(const String &) {}
void CommAPI::sendEvent(const String &) {}
void CommAPI::saveAllToEEPROM() {}
void CommAPI::sendFailsafeStatus() {}
void CommAPI::handleCommand(const String &) {}
void CommAPI::parseProfile(JsonArray) {}
