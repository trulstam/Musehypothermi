#ifndef TASK_SCHEDULER_H
#define TASK_SCHEDULER_H

#include "pid_module_asymmetric.h"    // Trengs for autotune abort ved failsafe
#include "comm_api.h"      // Trengs for comm.sendEvent()

// Failsafe-funksjoner
void triggerFailsafe(const char* reason);
void clearFailsafe();
bool isFailsafeActive();
const char* getFailsafeReason();
bool isBreathingFailsafeEnabled();
void setBreathingFailsafeEnabled(bool enabled);

// Heartbeat monitor
void heartbeatReceived();

// Init og kjør tasks
void initTasks();
void runTasks();

#endif
