#pragma once
#include <string>
#include <unordered_map>
#include <variant>
#include "host_arduino_stubs.h"

class JsonObject;

class JsonVariant {
public:
    JsonVariant() = default;
    JsonVariant(double v) : value(v) {}
    JsonVariant(int v) : value(static_cast<double>(v)) {}
    JsonVariant(const char* s) : value(std::string(s)) {}
    JsonVariant(const std::string& s) : value(s) {}

    template <typename T>
    T as() const { return static_cast<T>(std::get<double>(value)); }

    operator double() const { return std::get<double>(value); }
    operator std::string() const { return std::get<std::string>(value); }

private:
    std::variant<double, std::string> value {0.0};
};

class JsonObject {
public:
    JsonVariant& operator[](const std::string& key) { return storage[key]; }
    bool containsKey(const std::string& key) const { return storage.find(key) != storage.end(); }

private:
    std::unordered_map<std::string, JsonVariant> storage;
};

template <size_t N>
class StaticJsonDocument {
public:
    JsonObject& to<JsonObject>() { return object; }
    JsonObject& operator[](const std::string&) { return object; }
    bool containsKey(const char*) const { return false; }

private:
    JsonObject object;
};

template <size_t N>
StaticJsonDocument<N> deserializeJson(StaticJsonDocument<N>& doc, const String&) { return doc; }

enum DeserializationError { Ok = 0 };

inline DeserializationError deserializeJson(StaticJsonDocument<3072>&, const String&) { return Ok; }
