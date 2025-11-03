#pragma once

#include <cstdint>
#include <string>
#include <sstream>

#define HIGH 1
#define LOW 0
#define OUTPUT 1

inline unsigned long millis();
void setMockMillis(unsigned long value);
void advanceMockMillis(unsigned long delta);

inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline void delay(unsigned long) {}

template <typename T, typename Min, typename Max>
inline T constrain(T value, Min minValue, Max maxValue) {
    T minT = static_cast<T>(minValue);
    T maxT = static_cast<T>(maxValue);
    if (value < minT) {
        return minT;
    }
    if (value > maxT) {
        return maxT;
    }
    return value;
}

class String {
public:
    String() = default;
    String(const char* str) : value_(str ? str : "") {}
    String(const std::string& str) : value_(str) {}
    String(char c) : value_(1, c) {}
    String(int v) { value_ = std::to_string(v); }
    String(long v) { value_ = std::to_string(v); }
    String(unsigned long v) { value_ = std::to_string(v); }
    String(float v, int decimals = 2) { setNumber(v, decimals); }
    String(double v, int decimals = 2) { setNumber(v, decimals); }

    String& operator+=(const String& other) {
        value_ += other.value_;
        return *this;
    }

    String& operator+=(const char* other) {
        value_ += other ? other : "";
        return *this;
    }

    String& operator+=(char c) {
        value_ += c;
        return *this;
    }

    String& operator+=(int v) {
        value_ += std::to_string(v);
        return *this;
    }

    String& operator+=(double v) {
        setNumberAppend(v, 2);
        return *this;
    }

    const char* c_str() const { return value_.c_str(); }
    std::string str() const { return value_; }

private:
    void setNumber(double v, int decimals) {
        std::ostringstream oss;
        oss.setf(std::ios::fixed);
        oss.precision(decimals);
        oss << v;
        value_ = oss.str();
    }

    void setNumberAppend(double v, int decimals) {
        std::ostringstream oss;
        oss.setf(std::ios::fixed);
        oss.precision(decimals);
        oss << v;
        value_ += oss.str();
    }

    std::string value_;
};

inline String operator+(String lhs, const String& rhs) {
    lhs += rhs;
    return lhs;
}

inline String operator+(String lhs, const char* rhs) {
    lhs += rhs;
    return lhs;
}

inline String operator+(const char* lhs, String rhs) {
    String copy(lhs);
    copy += rhs;
    return copy;
}

class SerialMock {
public:
    void println() {}
    void println(const char*) {}
    void println(const String&) {}

    template <typename T>
    void print(const T&) {}
};

inline SerialMock Serial;

inline const char* F(const char* str) { return str; }

inline unsigned long millis() {
    extern unsigned long __mockMillis;
    return __mockMillis;
}

