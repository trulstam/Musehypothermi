#ifndef PID_MODULE_H
#define PID_MODULE_H

#include <PID_v1.h>
#include "eeprom_manager.h"
#include "pwm_module.h"

// Failsafe declarations
void triggerFailsafe(const char* reason);
void clearFailsafe();
bool isFailsafeActive();

#define MAX_PWM 2399

class PIDModule {
public:
    struct ProfileStep {
        float time;
        float temp;
    };

    PIDModule();
    void begin(EEPROMManager &eepromManager);
    void update(double currentTemp);
    void start();
    void stop();
    bool isActive();

    // Autotune
    void startAutotune();
    void runAutotune();
    void abortAutotune();
    bool isAutotuneActive();
    const char* getAutotuneStatus();

    // PID param control
    void setKp(float value);
    void setKi(float value);
    void setKd(float value);
    void setTargetTemp(float value);
    void setMaxOutputPercent(float percent);

    // PID param getters
    float getKp();
    float getKi();
    float getKd();
    float getTargetTemp();
    float getMaxOutputPercent();
    float getOutput();
    float getCurrentInput();
    float getPwmOutput();

    // Profile control
    void loadProfile(ProfileStep* steps, int length);
    bool isProfileActive();

    // Debugging
    void enableDebug(bool enable);
    bool isDebugEnabled();

private:
    void applyOutputLimit();
    void applyPIDOutput();
    void setPeltierOutput(double output);
    void calculateZieglerNicholsParams();
    void updateProfile();

    PID pid;
    EEPROMManager* eeprom;
    PWMModule pwm;

    double Input;
    double Output;
    double Setpoint;

    float kp, ki, kd;
    float maxOutputPercent;

    bool active;
    bool autotuneActive;
    const char* autotuneStatus;
    float backupKp, backupKi, backupKd;
    unsigned long autotuneStartMillis;
    int autotuneCycles;

    bool debugEnabled;

    ProfileStep profile[10];
    int profileLength;
    int currentProfileStep;
    unsigned long profileStartMillis;
    bool profileActive;
};

#endif
