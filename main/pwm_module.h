#ifndef PWM_MODULE_H
#define PWM_MODULE_H

#include <stdint.h>

class PWMModule {
public:
    PWMModule();
    void begin();                // Initierer PWM ved å bruke Arduino sitt standardoppsett
    void setDutyCycle(int duty); // 0–2399 (maps til 8-bit analogWrite)
    void stopPWM();              // Setter duty til 0 og stopper generatoren
};

#endif
