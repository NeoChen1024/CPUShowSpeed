cmake_minimum_required(VERSION 3.20)
project(classic_bench VERSION 0.1.0 LANGUAGES C CXX)

# Kernel build profile. "reference" fixes the kernel flags so results are comparable;
# "custom" takes CB_KERNEL_FLAGS from the user and is labelled as such in every result.
set(CB_PROFILE "reference" CACHE STRING "Kernel build profile: reference or custom")
set_property(CACHE CB_PROFILE PROPERTY STRINGS reference custom)
set(CB_REFERENCE_FLAGS "-O2")
set(CB_KERNEL_FLAGS "${CB_REFERENCE_FLAGS}" CACHE STRING "Kernel C flags for the custom profile")
if(CB_PROFILE STREQUAL "reference")
  set(CB_EFFECTIVE_FLAGS "${CB_REFERENCE_FLAGS}")
elseif(CB_PROFILE STREQUAL "custom")
  set(CB_EFFECTIVE_FLAGS "${CB_KERNEL_FLAGS}")
else()
  message(FATAL_ERROR "CB_PROFILE must be reference or custom")
endif()
if(CMAKE_C_FLAGS OR CMAKE_C_FLAGS_${CMAKE_BUILD_TYPE})
  message(FATAL_ERROR "Set kernel flags through CB_PROFILE/CB_KERNEL_FLAGS, not CMAKE_C_FLAGS or a build type")
endif()
separate_arguments(CB_FLAG_LIST UNIX_COMMAND "${CB_EFFECTIVE_FLAGS}")

set(CMAKE_INTERPROCEDURAL_OPTIMIZATION OFF)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE "" CACHE STRING "" FORCE)
endif()

# The classical sources are pre-ANSI or early ANSI C: compile them as gnu89 rather than
# rewriting K&R definitions, and silence warnings about that old style.
function(cb_kernel name)
  cmake_parse_arguments(K "" "" "SOURCES;DEFINES" ${ARGN})
  add_library(${name} OBJECT ${K_SOURCES})
  set_target_properties(${name} PROPERTIES C_STANDARD 90 C_EXTENSIONS ON INTERPROCEDURAL_OPTIMIZATION OFF)
  target_include_directories(${name} PRIVATE common)
  target_compile_definitions(${name} PRIVATE ${K_DEFINES})
  target_compile_options(${name} PRIVATE ${CB_FLAG_LIST} -w)
endfunction()

# Dhrystone 2.1 keeps dhry_1.c and dhry_2.c as separate translation units (Weicker's rules).
cb_kernel(dhrystone21 SOURCES dhrystone-2.1/dhry_1.c dhrystone-2.1/dhry_2.c)
cb_kernel(dhrystone11 SOURCES dhrystone-1.1/dhry11.c)
cb_kernel(whetstone_sp SOURCES whetstone/whets.c)
cb_kernel(whetstone_dp SOURCES whetstone/whets.c DEFINES DP)
cb_kernel(linpack_dp SOURCES linpack/linpack.c)
cb_kernel(linpack_sp SOURCES linpack/linpack.c DEFINES SP)

add_library(cb_time OBJECT common/cb_time.c)
set_target_properties(cb_time PROPERTIES C_STANDARD 11)
target_include_directories(cb_time PRIVATE common)

# Source identities embedded in every result.
set(CB_SOURCES_JSON "{")
set(sep "")
foreach(pair
    "dhrystone-2.1|original/dhrystone-2.1/dhry-c|dhrystone-2.1/dhry.h,dhrystone-2.1/dhry_1.c,dhrystone-2.1/dhry_2.c"
    "dhrystone-1.1|original/dhrystone-1.1/Dhry1.c|dhrystone-1.1/dhry11.c"
    "whetstone|original/whetstone/whets.c|whetstone/whets.c"
    "linpack|original/linpack/linpackc.new|linpack/linpack.c"
    "common|-|common/classic_kernel.h,common/cb_time.c")
  string(REPLACE "|" ";" parts "${pair}")
  list(GET parts 0 key)
  list(GET parts 1 orig)
  list(GET parts 2 mods)
  string(REPLACE "," ";" mods "${mods}")
  set(entry "\"${key}\":{")
  if(NOT orig STREQUAL "-")
    file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/${orig}" h)
    string(APPEND entry "\"original\":{\"path\":\"classic-benchs/${orig}\",\"sha256\":\"${h}\"},")
  endif()
  string(APPEND entry "\"modified\":{")
  set(msep "")
  foreach(m IN LISTS mods)
    file(SHA256 "${CMAKE_CURRENT_SOURCE_DIR}/${m}" h)
    string(APPEND entry "${msep}\"classic-benchs/${m}\":\"${h}\"")
    set(msep ",")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${m}")
  endforeach()
  string(APPEND entry "}}")
  string(APPEND CB_SOURCES_JSON "${sep}${entry}")
  set(sep ",")
endforeach()
string(APPEND CB_SOURCES_JSON "}")

set(CB_C_COMPILER "${CMAKE_C_COMPILER_ID}")
set(CB_C_COMPILER_VERSION "${CMAKE_C_COMPILER_VERSION}")
set(CB_CXX_COMPILER "${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
set(CB_TARGET_PROCESSOR "${CMAKE_SYSTEM_NAME} ${CMAKE_SYSTEM_PROCESSOR}")
configure_file(harness/build_info.h.in "${CMAKE_CURRENT_BINARY_DIR}/build_info.h" @ONLY)

set(CB_JSON_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../third-party/nlohmann-json/single_include")
if(NOT EXISTS "${CB_JSON_DIR}/nlohmann/json.hpp")
  message(FATAL_ERROR "nlohmann/json is missing; run: git submodule update --init third-party/nlohmann-json")
endif()

add_executable(classic-bench harness/main.cpp harness/platform.cpp
  $<TARGET_OBJECTS:dhrystone21> $<TARGET_OBJECTS:dhrystone11>
  $<TARGET_OBJECTS:whetstone_sp> $<TARGET_OBJECTS:whetstone_dp>
  $<TARGET_OBJECTS:linpack_dp> $<TARGET_OBJECTS:linpack_sp>
  $<TARGET_OBJECTS:cb_time>)
target_include_directories(classic-bench PRIVATE common harness "${CMAKE_CURRENT_BINARY_DIR}")
target_include_directories(classic-bench SYSTEM PRIVATE "${CB_JSON_DIR}")
target_compile_options(classic-bench PRIVATE -O2 -Wall -Wextra -Wshadow)
find_library(MATH_LIBRARY m)
if(MATH_LIBRARY)
  target_link_libraries(classic-bench PRIVATE ${MATH_LIBRARY})
endif()
