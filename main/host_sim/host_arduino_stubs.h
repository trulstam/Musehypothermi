#pragma once
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <unordered_map>
#include <thread>
#include <vector>
#include <algorithm>
#include <cctype>

using std::size_t;

inline unsigned long millis() {
    static auto start = std::chrono::steady_clock::now();
    auto now = std::chrono::steady_clock::now();
    return static_cast<unsigned long>(std::chrono::duration_cast<std::chrono::milliseconds>(now - start).count());
}

inline void delay(unsigned long ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

template <typename T>
inline T constrain(T x, T a, T b) { return std::min(std::max(x, a), b); }
inline double constrain(double x, double a, double b) { return std::min(std::max(x, a), b); }

template <typename T>
inline T min(T a, T b) { return (a < b) ? a : b; }

template <typename T>
inline T max(T a, T b) { return (a > b) ? a : b; }

inline double mapDouble(double x, double in_min, double in_max, double out_min, double out_max) {
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

inline double map(int x, int in_min, int in_max, double out_min, double out_max) {
    return mapDouble(static_cast<double>(x), static_cast<double>(in_min), static_cast<double>(in_max), out_min, out_max);
}

template <typename T>
inline T map(T x, T in_min, T in_max, T out_min, T out_max) {
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

#define F(x) x
#define PROGMEM

class String : public std::string {
public:
    using std::string::string;
    String() : std::string() {}
    String(const char* s) : std::string(s) {}
    String(const std::string& s) : std::string(s) {}
    String(long v) : std::string(std::to_string(v)) {}
    String& operator+=(const String& other) { std::string::operator+=(other); return *this; }
    String& toLowerCase() {
        std::transform(begin(), end(), begin(), [](unsigned char c){ return static_cast<char>(std::tolower(c)); });
        return *this;
    }
};

class Stream {
public:
    virtual ~Stream() = default;
    virtual int available() { return 0; }
    virtual char read() { return 0; }
    virtual size_t println() { return std::printf("\n"); }
    virtual size_t println(const char* msg) { return std::printf("%s\n", msg); }
    virtual size_t print(const char* msg) { return std::printf("%s", msg); }
    template <typename T>
    size_t print(T value, int digits = 0) {
        return std::printf("%.*f", digits, static_cast<double>(value));
    }
    template <typename T>
    size_t println(T value, int digits = 0) {
        size_t written = print(value, digits);
        std::printf("\n");
        return written + 1;
    }
};

class SerialStub : public Stream {
public:
    using Stream::print;
    using Stream::println;
};

static SerialStub Serial;

class EEPROMClass {
public:
    template <typename T>
    void put(int address, const T& value) {
        std::vector<uint8_t> bytes(sizeof(T));
        std::memcpy(bytes.data(), &value, sizeof(T));
        storage[address] = bytes;
    }

    template <typename T>
    void get(int address, T& value) const {
        auto it = storage.find(address);
        if (it == storage.end() || it->second.size() != sizeof(T)) {
            value = T();
            return;
        }
        std::memcpy(&value, it->second.data(), sizeof(T));
    }

private:
    mutable std::unordered_map<int, std::vector<uint8_t>> storage;
};

inline EEPROMClass EEPROM;

inline float analogRead(uint8_t) { return 0.0f; }
inline void analogWrite(uint8_t, int) {}
inline void pinMode(uint8_t, uint8_t) {}
inline void digitalWrite(uint8_t, uint8_t) {}
inline void tone(uint8_t, unsigned int, unsigned long = 0) {}
inline void noTone(uint8_t) {}
inline void analogReadResolution(int) {}
inline void analogReference(int) {}

#ifndef HIGH
#define HIGH 0x1
#endif
#ifndef LOW
#define LOW  0x0
#endif
#ifndef INPUT
#define INPUT 0x0
#endif
#ifndef OUTPUT
#define OUTPUT 0x1
#endif
#ifndef INPUT_PULLUP
#define INPUT_PULLUP 0x2
#endif
#ifndef AR_EXTERNAL
#define AR_EXTERNAL 0
#endif
#ifndef AR_DEFAULT
#define AR_DEFAULT 1
#endif
#ifndef A1
#define A1 1
#endif
#ifndef A2
#define A2 2
#endif
#ifndef A3
#define A3 3
#endif
#ifndef A4
#define A4 4
#endif

inline unsigned long micros() { return millis() * 1000UL; }
