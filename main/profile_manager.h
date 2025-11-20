#ifndef PROFILE_MANAGER_H
#define PROFILE_MANAGER_H

#include <Arduino.h>

class ProfileManager {
  public:
    struct ProfileStep {
      uint32_t time_ms;      // Absolute time from profile start
      float plate_target;    // Target plate temperature at this timestamp
    };

    static const uint8_t MAX_STEPS = 10;

    ProfileManager();

    void begin();
    void update();

    void loadProfile(const ProfileStep* steps, uint8_t length);

    void start();
    void pause();
    void resume();
    void stop();

    bool isActive();
    bool isPaused();

    uint8_t getCurrentStep();
    uint32_t getRemainingTime();

  private:
    ProfileStep profile[MAX_STEPS];
    uint8_t profileLength;

    bool active;
    bool paused;

    uint8_t currentStep;
    uint32_t profileStartTimeMs;
    uint32_t pauseStartTimeMs;
    uint32_t totalPausedMs;

    void advanceStep(uint8_t newStep);
    void applyCurrentTarget();
};

// 👉🏻 Ekstern deklarasjon av instansen for bruk i andre filer
extern ProfileManager profileManager;

#endif // PROFILE_MANAGER_H
