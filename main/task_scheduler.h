#ifndef TASK_SCHEDULER_H
#define TASK_SCHEDULER_H

#include "pid_module_asymmetric.h"    // Trengs for autotune abort ved failsafe
#include "comm_api.h"      // Trengs for comm.sendEvent()

// Failsafe/Panic-funksjoner
void triggerFailsafe(const char* reason);
void clearFailsafe();
bool isFailsafeActive();
const char* getFailsafeReason();

void triggerPanic(const char* reason);
void clearPanic();
bool isPanicActive();
const char* getPanicReason();

// Heartbeat monitor
void heartbeatReceived();

// Init og kjør tasks
void initTasks();
void runTasks();

#endif
