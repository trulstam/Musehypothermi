#pragma once

class JsonValue {
public:
    template <typename T>
    JsonValue& operator=(const T&) {
        return *this;
    }

    JsonValue operator[](const char*) { return JsonValue{}; }
};

template <size_t N>
class StaticJsonDocument {
public:
    JsonValue operator[](const char*) { return JsonValue{}; }
};

template <typename Stream, size_t N>
void serializeJson(const StaticJsonDocument<N>&, Stream&) {}

