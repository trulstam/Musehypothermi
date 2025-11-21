cmake_minimum_required(VERSION 3.10)
project(musehypothermi_host_sim)
add_definitions(-DHOST_BUILD)
add_definitions(-DSIMULATION_MODE=1)
add_executable(host_sim
    host_sim.cpp
)
target_compile_features(host_sim PRIVATE cxx_std_17)
target_include_directories(host_sim PRIVATE ../main .)
