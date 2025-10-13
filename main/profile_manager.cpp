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
    currentStep(0), stepStartTime(0), pausedTime(0), currentTarget(0.0) {}

void ProfileManager::begin() {
  active = false;
  paused = false;
}

void ProfileManager::loadProfile(ProfileStep* steps, uint8_t length) {
  if (length == 0 || length > MAX_STEPS) return;

  for (uint8_t i = 0; i < length; i++) {
    profile[i] = steps[i];
  }
  profileLength = length;
}

void ProfileManager::start() {
  if (profileLength == 0) return;
  active = true;
  paused = false;
  currentStep = 0;
  stepStartTime = millis();
  currentTarget = profile[0].plate_start_temp;
  pid.setTargetTemp(currentTarget);
  pid.start();
}

void ProfileManager::pause() {
  if (!active || paused) return;
  paused = true;
  pausedTime = millis();
  pid.stop();
}

void ProfileManager::resume() {
  if (!paused) return;
  paused = false;
  uint32_t pauseDuration = millis() - pausedTime;
  stepStartTime += pauseDuration;
  pid.start();
}

void ProfileManager::stop() {
  active = false;
  paused = false;
  pid.stop();
}

bool ProfileManager::isActive() { return active; }
bool ProfileManager::isPaused() { return paused; }
uint8_t ProfileManager::getCurrentStep() { return currentStep; }

uint32_t ProfileManager::getRemainingTime() {
  if (!active) return 0;
  uint32_t elapsed = millis() - stepStartTime;
  uint32_t remaining = profile[currentStep].total_step_time_ms - elapsed;
  return remaining;
}

void ProfileManager::update() {
  if (!active || paused || isFailsafeActive()) {
    if (isFailsafeActive()) stop();
    return;
  }

  updateRamp();
  applyRectalOverride();
  checkStepComplete();
}

void ProfileManager::updateRamp() {
  ProfileStep& step = profile[currentStep];
  uint32_t now = millis();
  uint32_t elapsed = now - stepStartTime;

  if (step.ramp_time_ms == 0) {
    // Ingen rampetid angitt – hopp umiddelbart til sluttverdien.
    currentTarget = step.plate_end_temp;
    pid.setTargetTemp(currentTarget);
    return;
  }

  if (elapsed <= step.ramp_time_ms) {
    float fraction = (float)elapsed / (float)step.ramp_time_ms;
    currentTarget = step.plate_start_temp +
      (step.plate_end_temp - step.plate_start_temp) * fraction;
  } else {
    currentTarget = step.plate_end_temp;
  }

  pid.setTargetTemp(currentTarget);
}

void ProfileManager::applyRectalOverride() {
  ProfileStep& step = profile[currentStep];
  if (step.rectal_override_target > -100) {
    double rectalTemp = sensors.getRectalTemp();
    if (rectalTemp < step.rectal_override_target) {
      currentTarget += 0.5;  // Juster opp target med margin
      pid.setTargetTemp(currentTarget);
    }
  }
}

void ProfileManager::checkStepComplete() {
  uint32_t now = millis();
  uint32_t elapsed = now - stepStartTime;
  if (elapsed >= profile[currentStep].total_step_time_ms) {
    currentStep++;
    if (currentStep >= profileLength) {
      stop();
    } else {
      stepStartTime = now;
      currentTarget = profile[currentStep].plate_start_temp;
      pid.setTargetTemp(currentTarget);
    }
  }
}
