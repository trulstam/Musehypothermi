#pragma once

#include <map>
#include <string>
#include <vector>

#include "Arduino.h"

class CommAPI {
public:
    void sendEvent(const String& message) { events.emplace_back(message.c_str()); }

    void sendStatus(const char* key, float value) { statuses[key] = value; }
    void sendStatus(const char* key, int value) { statuses[key] = static_cast<double>(value); }
    void sendStatus(const char* key, double value) { statuses[key] = value; }

    std::vector<std::string> events;
    std::map<std::string, double> statuses;
};

