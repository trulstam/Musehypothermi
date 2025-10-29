#ifndef PID_MODULE_ASYMMETRIC_H
#define PID_MODULE_ASYMMETRIC_H

#include <PID_v1.h>
#include <stddef.h>
#include "eeprom_manager.h"
#include "pwm_module.h"

// Forward declarations for external functions
bool isFailsafeActive();
void clearFailsafe();

// Global PWM tracker for simulation
extern int currentPwmOutput;

#define MAX_PWM 2399

class AsymmetricPIDModule {
public:
    struct AsymmetricPIDParams {
        float kp_cooling;     // Conservative Kp for cooling (lower)
        float ki_cooling;     // Conservative Ki for cooling (lower)
        float kd_cooling;     // Higher Kd for cooling (more damping)
        
        float kp_heating;     // More aggressive Kp for heating
        float ki_heating;     // Higher Ki for heating
        float kd_heating;     // Lower Kd for heating
        
        float cooling_limit;  // Max cooling output (negative, e.g., -50%)
        float heating_limit;  // Max heating output (positive, e.g., +100%)
        
        float deadband;       // Temperature deadband around setpoint (±0.1°C)
        float safety_margin;  // Safety margin below target (e.g., 1°C)
    };

    AsymmetricPIDModule();
    void begin(EEPROMManager &eepromManager);
    void update(double currentTemp);
    
    void start();
    void stop();
    bool isActive();
    
    // Safety controls
    void setEmergencyStop(bool enabled);
    void setCoolingRateLimit(float maxCoolingRatePerSecond, bool persist = true);
    
    // PID parameter management
    void setCoolingPID(float kp, float ki, float kd, bool persist = true);
    void setHeatingPID(float kp, float ki, float kd, bool persist = true);
    void setOutputLimits(float coolingLimit, float heatingLimit, bool persist = true);
    void setSafetyParams(float deadband, float safetyMargin, bool persist = true);
    
    // Getters for compatibility with original PIDModule
    float getKp();
    float getKi();
    float getKd();
    float getHeatingKp() const { return currentParams.kp_heating; }
    float getHeatingKi() const { return currentParams.ki_heating; }
    float getHeatingKd() const { return currentParams.kd_heating; }
    float getCoolingKp() const { return currentParams.kp_cooling; }
    float getCoolingKi() const { return currentParams.ki_cooling; }
    float getCoolingKd() const { return currentParams.kd_cooling; }
    float getTargetTemp() { return Setpoint; }
    float getActivePlateTarget() { return Setpoint; }
    float getMaxOutputPercent();
    float getOutput() { return finalOutput; }
    float getRawPIDOutput() { return rawPIDOutput; }
    float getPwmOutput() { return finalOutput; }
    bool isCooling() { return coolingMode; }
    bool isEmergencyStop() { return emergencyStop; }
    float getTemperatureRate() { return temperatureRate; }
    float getCurrentDeadband() { return currentParams.deadband; }
    float getCoolingRateLimit() const { return maxCoolingRate; }
    float getSafetyMargin() const { return currentParams.safety_margin; }
    float getHeatingOutputLimit() const { return currentParams.heating_limit; }
    float getCoolingOutputLimit() const {
        return currentParams.cooling_limit < 0 ? -currentParams.cooling_limit : currentParams.cooling_limit;
    }

    // Compatibility setters
    void setTargetTemp(float value) { Setpoint = value; }
    void setKp(float value);
    void setKi(float value);
    void setKd(float value);
    void setMaxOutputPercent(float percent, bool persist = true);

    // Autotune functionality
    void startAutotune();  // Standard autotune for compatibility
    void startAsymmetricAutotune(float requestedStepPercent = -1.0f, const char* direction = "heating");
    void runAsymmetricAutotune();
    void abortAutotune();
    bool isAutotuneActive() { return autotuneActive; }
    const char* getAutotuneStatus();
    
    // Debug methods
    void enableDebug(bool enable);
    bool isDebugEnabled();
    
    // Configuration methods
    void saveAsymmetricParams();
    void loadAsymmetricParams();

private:
    // PID instances
    PID coolingPID;
    PID heatingPID;
    
    // Current operating parameters
    AsymmetricPIDParams currentParams;
    
    // Control variables
    double Input;
    double Setpoint;
    double rawPIDOutput;
    double finalOutput;
    double coolingOutput, heatingOutput;
    
    // State tracking
    bool active;
    bool coolingMode;
    bool emergencyStop;
    bool autotuneActive;
    const char* autotuneStatusString;
    
    // Debug
    bool debugEnabled;
    
    // Safety features
    double maxCoolingRate;
    unsigned long lastUpdateTime;
    double lastTemperature;
    double temperatureRate;
    
    // Output smoothing
    double outputSmoothingFactor;
    double lastOutput;
    
    // EEPROM management
    EEPROMManager* eeprom;
    PWMModule pwm;

    // Safety methods
    bool checkSafetyLimits(double currentTemp, double targetTemp);
    void applySafetyConstraints();
    void applyRateLimiting();
    void applyOutputSmoothing();
    void resetOutputState();

    // PID switching logic
    void updatePIDMode(double error);
    void switchToCoolingPID();
    void switchToHeatingPID();

    // Enhanced autotune
    void performCoolingAutotune();
    void performHeatingAutotune();

    // Autotune helpers/state
    static constexpr size_t kAutotuneLogSize = 300;
    static constexpr unsigned long kAutotuneSampleIntervalMs = 500;
    static constexpr unsigned long kAutotuneTimeoutMs = 300000;  // 5 minutes
    unsigned long autotuneTimestamps[kAutotuneLogSize];
    float autotuneTemperatures[kAutotuneLogSize];
    size_t autotuneLogIndex;
    unsigned long autotuneStartMillis;
    unsigned long lastAutotuneSample;
    float autotuneStepPercent;

    void resetAutotuneState();
    void applyManualOutputPercent(float percent);
    void finalizeAutotune(bool success);
    bool calculateAutotuneResults();
};

#endif // PID_MODULE_ASYMMETRIC_H
