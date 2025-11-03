#pragma once

#define EEPROM_MANAGER_H
#define COMM_API_H
#define SENSOR_MODULE_H  // prevents inclusion of production sensor header
#define PWM_MODULE_H

#include "Arduino.h"
#include "ArduinoJson.h"
#include "PID_v1.h"
#include "comm_api.h"
#include "sensor_module.h"
#include "pwm_module.h"
#include "eeprom_manager.h"

