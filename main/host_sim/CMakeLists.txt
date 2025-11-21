cmake_minimum_required(VERSION 3.10)
project(musehypothermi_host_sim)
add_definitions(-DHOST_BUILD)
add_executable(host_sim
    host_sim.cpp
    Arduino_host.h
    host_arduino_stubs.h
    ../pid_module.cpp
    ../pid_module.h
    ../profile_manager.cpp
    ../profile_manager.h
    ../pressure_module.cpp
    ../pressure_module.h
    ../sensor_module.cpp
    ../sensor_module.h
)
target_compile_features(host_sim PRIVATE cxx_std_17)
target_include_directories(host_sim PRIVATE ..)
