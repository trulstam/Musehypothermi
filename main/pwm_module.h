#ifndef PWM_MODULE_H
#define PWM_MODULE_H

#include <stdint.h>

class PWMModule {
public:
    PWMModule();
    void begin();              // Init: konfigurer pin og start GPT0
    void setDutyCycle(int duty); // 0–2399 (20kHz PWM)
    void stopPWM();           // Stopper teller og setter duty til 0

private:
    void configurePin6();     // Setter opp pin 6 (P313) for GPT0
    void enableGPT0();        // Init GPT0 med 20kHz PWM
};

#endif