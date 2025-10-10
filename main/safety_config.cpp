// Safety Configuration for Real Hypothermia System
// File: safety_config.h

#ifndef SAFETY_CONFIG_H
#define SAFETY_CONFIG_H

// ============================================================================
// CRITICAL SAFETY PARAMETERS - ADJUST FOR YOUR SPECIFIC SYSTEM
// ============================================================================

namespace SafetyConfig {
    // Temperature limits (°C)
    const float ABSOLUTE_MIN_TEMP = 12.0;      // Never go below this
    const float ABSOLUTE_MAX_TEMP = 42.0;      // Never go above this
    const float SAFETY_MARGIN_COOLING = 1.5;  // Stop cooling this far from target
    const float SAFETY_MARGIN_HEATING = 0.5;  // Less critical for heating
    
    // Rate limits (°C/second)
    const float MAX_COOLING_RATE = 1.5;        // Conservative cooling rate
    const float MAX_HEATING_RATE = 3.0;        // Heating can be faster
    const float EMERGENCY_RATE_LIMIT = 2.5;    // Emergency stop threshold
    
    // PID Parameters - COOLING (Conservative)
    const float DEFAULT_KP_COOLING = 0.8;      // Lower Kp for stability
    const float DEFAULT_KI_COOLING = 0.02;     // Very low Ki to prevent windup
    const float DEFAULT_KD_COOLING = 3.0;      // High Kd for damping
    const float MAX_KP_COOLING = 2.0;          // Never exceed this Kp
    const float MAX_KI_COOLING = 0.1;          // Never exceed this Ki
    
    // PID Parameters - HEATING (More Aggressive)
    const float DEFAULT_KP_HEATING = 2.5;      // Higher Kp for responsiveness
    const float DEFAULT_KI_HEATING = 0.2;      // Higher Ki for steady-state
    const float DEFAULT_KD_HEATING = 1.2;      // Moderate Kd
    const float MAX_KP_HEATING = 5.0;          // Maximum heating Kp
    const float MAX_KI_HEATING = 1.0;          // Maximum heating Ki
    
    // Output limits (%)
    const float MAX_COOLING_OUTPUT = 60.0;     // Limit cooling power
    const float MAX_HEATING_OUTPUT = 100.0;    // Full heating allowed
    const float STARTUP_COOLING_LIMIT = 30.0;  // Even more conservative at startup
    
    // Control deadbands (°C)
    const float TEMPERATURE_DEADBAND = 0.08;   // ±0.08°C around target
    const float MODE_SWITCH_HYSTERESIS = 0.15; // Prevent rapid switching
    
    // Timing parameters (milliseconds)
    const unsigned long SAFETY_CHECK_INTERVAL = 100;     // 10Hz safety checks
    const unsigned long EMERGENCY_TIMEOUT = 2000;        // 2s to stop in emergency
    const unsigned long RATE_CALCULATION_WINDOW = 5000;  // 5s window for rate calc
    
    // Autotune safety parameters
    const float AUTOTUNE_MAX_COOLING_STEP = 25.0;        // Max cooling step for autotune
    const float AUTOTUNE_MAX_HEATING_STEP = 50.0;        // Max heating step for autotune
    const unsigned long AUTOTUNE_TIMEOUT = 300000;       // 5 minutes max
    const float AUTOTUNE_MIN_TEMP_CHANGE = 0.5;          // Minimum change for valid autotune
    
    // Failsafe breathing parameters
    const float MIN_BREATHING_RATE = 5.0;                // BPM - emergency if below
    const unsigned long BREATHING_TIMEOUT = 15000;       // 15s without breathing = emergency
    
    // Water cooling system parameters (for your specific setup)
    const float WATER_TEMP_SPRING = 8.0;                 // Approximate spring water temp
    const float PELTIER_MAX_DELTA_T = 70.0;              // Max Peltier ΔT
    const float THEORETICAL_MIN_TEMP = WATER_TEMP_SPRING - 10.0; // Conservative estimate
    
    // System-specific thermal parameters
    const float COOLING_EFFICIENCY_FACTOR = 2.5;         // Cooling is 2.5x more efficient
    const float THERMAL_TIME_CONSTANT_COOLING = 30.0;    // Seconds - faster cooling
    const float THERMAL_TIME_CONSTANT_HEATING = 80.0;    // Seconds - slower heating
}

// Safety state enumeration
enum class SafetyState {
    SAFE,                    // Normal operation
    WARNING_COOLING_FAST,    // Cooling rate approaching limit
    WARNING_TEMP_LOW,        // Temperature near minimum
    EMERGENCY_RATE_EXCEEDED, // Cooling rate exceeded
    EMERGENCY_TEMP_LOW,      // Temperature below absolute minimum
    EMERGENCY_NO_BREATHING,  // No breathing detected
    EMERGENCY_SYSTEM_FAULT   // System fault detected
};

// Safety monitor class
class SafetyMonitor {
public:
    SafetyMonitor();
    void begin();
    void update(float currentTemp, float breathingRate);
    
    SafetyState getCurrentState() { return currentState; }
    bool isSafeToOperate() { return currentState == SafetyState::SAFE; }
    bool isEmergencyState() { return (int)currentState >= 3; }
    
    void setTargetTemp(float target);
    bool isSafeCoolingTarget(float target);
    bool isSafeHeatingTarget(float target);
    
    float getMaxSafeCoolingOutput(float currentTemp, float targetTemp);
    float getMaxSafeHeatingOutput(float currentTemp, float targetTemp);
    
    void triggerEmergencyStop(const char* reason);
    void clearEmergencyStop();
    
    const char* getStateDescription();

private:
    SafetyState currentState;
    float targetTemperature;
    
    // Rate monitoring
    float temperatureHistory[10];
    unsigned long timeHistory[10];
    int historyIndex;
    float currentCoolingRate;
    
    // Emergency state
    bool emergencyStopActive;
    unsigned long emergencyStartTime;
    
    void updateTemperatureRate(float temp);
    void checkTemperatureLimits(float temp);
    void checkRateLimits();
    void checkBreathingRate(float breathingRate);
    
    void setState(SafetyState newState);
};

#endif // SAFETY_CONFIG_H