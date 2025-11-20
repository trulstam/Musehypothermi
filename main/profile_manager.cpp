#include "profile_manager.h"
#include "pid_module_asymmetric.h"
#include "sensor_module.h"
#include "task_scheduler.h"

// 👉🏻 Opprett den globale instansen av ProfileManager
ProfileManager profileManager;

extern AsymmetricPIDModule pid;
extern SensorModule sensors;

ProfileManager::ProfileManager()
  : profileLength(0), active(false), paused(false),
    currentStep(0), profileStartTimeMs(0), pauseStartTimeMs(0), totalPausedMs(0) {}

void ProfileManager::begin() {
  active = false;
  paused = false;
}

void ProfileManager::loadProfile(const ProfileStep* steps, uint8_t length) {
  if (length == 0) return;

  profileLength = min<uint8_t>(length, MAX_STEPS);

  for (uint8_t i = 0; i < profileLength; i++) {
    profile[i] = steps[i];
  }
}

void ProfileManager::start() {
  if (profileLength == 0) return;
  active = true;
  paused = false;
  currentStep = 0;
  profileStartTimeMs = millis();
  totalPausedMs = 0;
  applyCurrentTarget();
  pid.start();
}

void ProfileManager::pause() {
  if (!active || paused) return;
  paused = true;
  pauseStartTimeMs = millis();
  pid.stop();
}

void ProfileManager::resume() {
  if (!paused) return;
  paused = false;
  uint32_t pauseDuration = millis() - pauseStartTimeMs;
  totalPausedMs += pauseDuration;
  pid.start();
}

void ProfileManager::stop() {
  active = false;
  paused = false;
  currentStep = 0;
  pid.stop();
}

bool ProfileManager::isActive() { return active; }
bool ProfileManager::isPaused() { return paused; }
uint8_t ProfileManager::getCurrentStep() { return currentStep; }

uint32_t ProfileManager::getRemainingTime() {
  if (!active) return 0;
  if (profileLength == 0) return 0;

  const ProfileStep& lastStep = profile[profileLength - 1];
  uint32_t elapsed = millis() - profileStartTimeMs - totalPausedMs;
  if (elapsed >= lastStep.time_ms) return 0;
  return lastStep.time_ms - elapsed;
}

void ProfileManager::update() {
  if (!active || paused || isFailsafeActive()) {
    if (isFailsafeActive()) stop();
    return;
  }

  uint32_t elapsed = millis() - profileStartTimeMs - totalPausedMs;

  if (currentStep + 1 < profileLength && elapsed >= profile[currentStep + 1].time_ms) {
    advanceStep(currentStep + 1);
  }

  // Stop profile once the final step time has passed
  if (elapsed > profile[profileLength - 1].time_ms) {
    stop();
  }
}

void ProfileManager::advanceStep(uint8_t newStep) {
  if (newStep >= profileLength) return;
  currentStep = newStep;
  applyCurrentTarget();
}

void ProfileManager::applyCurrentTarget() {
  if (currentStep >= profileLength) return;
  pid.setTargetTemp(profile[currentStep].plate_target);
}
