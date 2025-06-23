#ifndef PWM_MODULE_H
#define PWM_MODULE_H

#include <stdint.h>

class PWMModule {
public:
    PWMModule();
    void begin();
    void setDutyCycle(int duty);
    void stopPWM();

private:
    void configurePin6();
    void enableGPT0();
};

#endif
