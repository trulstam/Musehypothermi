cmake_minimum_required(VERSION 3.13)
project(muse_host_tests CXX)

set(CMAKE_CXX_STANDARD 17)
add_compile_definitions(HOST_BUILD)

include_directories(..)

set(COMMON_SOURCES
    ../pid_module_asymmetric.cpp
    ../sensor_module.cpp
    ../pressure_module.cpp
    ../pwm_module.cpp
    ../task_scheduler.cpp
    ../profile_manager.cpp
    ../eeprom_manager.cpp
)

add_executable(test_pid ${COMMON_SOURCES} test_pid.cpp)
add_executable(test_profile ${COMMON_SOURCES} test_profile.cpp)
add_executable(test_failsafe ${COMMON_SOURCES} test_failsafe.cpp)

target_sources(test_pid PRIVATE comm_api_stub.cpp)
target_sources(test_profile PRIVATE comm_api_stub.cpp)
target_sources(test_failsafe PRIVATE comm_api_stub.cpp)
