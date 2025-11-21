#pragma once
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>

using std::size_t;

inline unsigned long millis() {
    static auto start = std::chrono::steady_clock::now();
    auto now = std::chrono::steady_clock::now();
    return static_cast<unsigned long>(std::chrono::duration_cast<std::chrono::milliseconds>(now - start).count());
}

inline void delay(unsigned long ms) { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

template <typename T>
inline T constrain(T x, T a, T b) { return std::min(std::max(x, a), b); }

template <typename T>
inline T min(T a, T b) { return (a < b) ? a : b; }

template <typename T>
inline T max(T a, T b) { return (a > b) ? a : b; }

inline double mapDouble(double x, double in_min, double in_max, double out_min, double out_max) {
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
    String& operator+=(const String& other) { std::string::operator+=(other); return *this; }
};

class Stream {
public:
    virtual ~Stream() = default;
    virtual int available() { return 0; }
    virtual char read() { return 0; }
    virtual size_t println(const char* msg) { return std::printf("%s\n", msg); }
    virtual size_t print(const char* msg) { return std::printf("%s", msg); }
};

class SerialStub : public Stream {
public:
    using Stream::print;
    using Stream::println;
};

static SerialStub Serial;

inline float analogRead(uint8_t) { return 0.0f; }
inline void analogWrite(uint8_t, int) {}
inline void pinMode(uint8_t, uint8_t) {}
inline void digitalWrite(uint8_t, uint8_t) {}
inline void tone(uint8_t, unsigned int, unsigned long = 0) {}
inline void noTone(uint8_t) {}

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

inline unsigned long micros() { return millis() * 1000UL; }
