#pragma once
#include "../host_firmware_stubs.h"

class ProfileManager {
public:
    struct ProfileStep { float time; float temp; };
    void begin() {}
    void loadProfile(const ProfileStep*, uint8_t) {}
    void start() {}
    void stop() {}
    void pause() {}
    void resume() {}
    bool isActive() const { return active; }
    bool isPaused() const { return false; }
    uint8_t getCurrentStep() const { return 0; }
private:
    bool active {false};
};

extern ProfileManager profileManager;
