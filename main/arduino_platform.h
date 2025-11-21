#pragma once

#ifndef SIMULATION_MODE
#define SIMULATION_MODE 0
#endif

#if SIMULATION_MODE
#include "../simulation/Arduino_host.h"
#else
#include <Arduino.h>
#endif
