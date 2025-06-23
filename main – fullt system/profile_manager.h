#ifndef PROFILE_MANAGER_H
#define PROFILE_MANAGER_H

#include <Arduino.h>

class ProfileManager {
  public:
    struct ProfileStep {
      float plate_start_temp;
      float plate_end_temp;
      uint32_t ramp_time_ms;
      float rectal_override_target;
      uint32_t total_step_time_ms;
    };

    ProfileManager();

    void begin();
    void update();

    void loadProfile(ProfileStep* steps, uint8_t length);

    void start();
    void pause();
    void resume();
    void stop();

    bool isActive();
    bool isPaused();

    uint8_t getCurrentStep();
    uint32_t getRemainingTime();

  private:
    static const uint8_t MAX_STEPS = 10;
    ProfileStep profile[MAX_STEPS];
    uint8_t profileLength;

    bool active;
    bool paused;

    uint8_t currentStep;
    uint32_t stepStartTime;
    uint32_t pausedTime;

    float currentTarget;

    void updateRamp();
    void checkStepComplete();
    void applyRectalOverride();
};

// 👉🏻 Ekstern deklarasjon av instansen for bruk i andre filer
extern ProfileManager profileManager;

#endif // PROFILE_MANAGER_H
