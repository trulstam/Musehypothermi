#pragma once

class SensorModule {
public:
    double getCoolingPlateTemp() const { return coolingTemp; }
    double getRectalTemp() const { return rectalTemp; }

    void setCoolingPlateTemp(double temp) { coolingTemp = temp; }
    void setRectalTemp(double temp) { rectalTemp = temp; }

private:
    double coolingTemp = 30.0;
    double rectalTemp = 37.0;
};

