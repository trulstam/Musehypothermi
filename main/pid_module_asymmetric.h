#ifndef PID_MODULE_ASYMMETRIC_H
#define PID_MODULE_ASYMMETRIC_H

#include <PID_v1.h>
#include <ArduinoJson.h>
#include "eeprom_manager.h"
#include "pwm_module.h"

#include <stddef.h>

// Forward declarations for external functions
bool isFailsafeActive();
void clearFailsafe();

// Global PWM tracker for simulation
extern int currentPwmOutput;

#define MAX_PWM 2399

// The asymmetric autotune previously buffered 600 samples for both the
// heating and cooling phases (≈19 KB). That exhausted the MCU's RAM once
// combined with other globals. Limit the buffer to 200 samples per phase,
// which still covers more than three minutes of data at the 1 Hz sampling
// rate used by the autotune routines.
static constexpr size_t AUTOTUNE_SAMPLE_CAPACITY = 200;

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
    void configureAutotune(float target, float heatingStepPercent, float coolingStepPercent,
                           unsigned long maxDurationMs);
    void startAsymmetricAutotune();
    void runAsymmetricAutotune();
    void abortAutotune();
    bool isAutotuneActive() { return autotuneActive; }
    const char* getAutotuneStatus();
    bool hasAutotuneRecommendations() const;
    bool applyAutotuneRecommendations();

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
    void publishFilterTelemetry(const char* stage, double rawValue, double finalValue);
    void resetOutputState();

    // PID switching logic
    void updatePIDMode(double error);
    void switchToCoolingPID();
    void switchToHeatingPID();

    // Enhanced autotune
    void performCoolingAutotune();
    void performHeatingAutotune();

    struct AutotuneSample {
        unsigned long timeMs;
        float plateTemp;
        float coreTemp;
        float pwmPercent;
    };

    struct AutotuneDataset {
        AutotuneSample samples[AUTOTUNE_SAMPLE_CAPACITY];
        int count;
        unsigned long startMillis;
        float stepPercent;
        float baseline;
    };

    struct AutotuneConfig {
        float target;
        float heatingStepPercent;
        float coolingStepPercent;
        unsigned long maxDurationMs;
    };

    struct AutotuneRecommendation {
        bool valid;
        bool heatingValid;
        bool coolingValid;
        float heatingKp;
        float heatingKi;
        float heatingKd;
        float coolingKp;
        float coolingKi;
        float coolingKd;
        float heatingProcessGain;
        float heatingTimeConstant;
        float heatingDeadTime;
        float heatingInitialSlope;
        float coolingProcessGain;
        float coolingTimeConstant;
        float coolingDeadTime;
        float coolingInitialSlope;
    };

    enum class AutotunePhase {
        kIdle,
        kStabilizing,
        kHeatingStep,
        kHeatingRecover,
        kCoolingStep,
        kCoolingRecover,
        kComplete,
        kFailed,
    };

    struct AutotuneSession {
        AutotunePhase phase;
        unsigned long sessionStart;
        unsigned long stateStart;
        unsigned long lastSampleMillis;
        unsigned long lastDerivativeMillis;
        float lastDerivativeTemp;
        float currentSlope;
        unsigned long stabilityStart;
        float target;
        float holdOutputPercent;
        float heatingCommandPercent;
        float coolingCommandPercent;
        unsigned long maxDurationMs;
        AutotuneDataset heating;
        AutotuneDataset cooling;
        AutotuneRecommendation recommendation;
    };

    AutotuneSession autotuneSession;
    AutotuneConfig autotuneConfig;

    void resetAutotuneSession();
    void transitionAutotunePhase(AutotunePhase nextPhase, const char* statusMessage);
    void applyAutotuneOutput(float percent);
    void logAutotuneSample(AutotuneDataset& dataset, unsigned long now, float plateTemp, float coreTemp,
                           float appliedOutputPercent);
    bool datasetFull(const AutotuneDataset& dataset) const;
    bool calculateProcessParameters(const AutotuneDataset& dataset, float& processGain, float& timeConstant,
                                    float& deadTime, float& initialSlope);
    void computeRecommendedPid(float processGain, float timeConstant, float deadTime, bool heating,
                               float& kp, float& ki, float& kd);
    void finalizeAutotune();
    void sendAutotuneResults(const AutotuneRecommendation& rec, const AutotuneDataset& heating,
                             const AutotuneDataset& cooling);
    void appendSeries(JsonArray timestamps, JsonArray plateTemps, const AutotuneDataset& dataset,
                      JsonArray* coreTemps = nullptr);
};

#endif // PID_MODULE_ASYMMETRIC_H
