#pragma once

class PWMModule {
public:
    void begin() {}
    void setDutyCycle(int duty) { lastDuty = duty; }
    void stopPWM() { lastDuty = 0; }

    int lastDuty = 0;
};

