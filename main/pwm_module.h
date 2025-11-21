#ifndef PWM_MODULE_H
#define PWM_MODULE_H

#ifdef HOST_BUILD
class PWMModule {
public:
    PWMModule() = default;
    void begin() {}

    void setDutyCycle(int duty) {
        if (duty > 2399) duty = 2399;
        if (duty < 0) duty = 0;
        lastDutyCycle = duty;
    }

    void stopPWM() { lastDutyCycle = 0; }

    int getLastDutyCycle() const { return lastDutyCycle; }

private:
    int lastDutyCycle {0};
};
#else
#include <stdint.h>

class PWMModule {
public:
    PWMModule();
    void begin();              // Init: konfigurer pin og start GPT0
    void setDutyCycle(int duty); // 0–2399 (20kHz PWM)
    void stopPWM();           // Stopper teller og setter duty til 0

    // Host/test visibility for latest duty command
    int getLastDutyCycle() const { return lastDutyCycle; }

private:
    void configurePin6();     // Setter opp pin 6 (P313) for GPT0
    void enableGPT0();        // Init GPT0 med 20kHz PWM

    int lastDutyCycle {0};
};
#endif

#endif
