#pragma once

#include <stdint.h>

inline bool pwmBegin(uint32_t) { return true; }
inline void pwmSetDuty01(float) {}
inline void pwmDebugDump() {}
inline void pwmStop() {}

class PWMModule {
public:
    void begin() {}
    void setDutyCycle(int duty) { lastDuty = duty; }
    void stopPWM() { lastDuty = 0; }

    int lastDuty = 0;
};

