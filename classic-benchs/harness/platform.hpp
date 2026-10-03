// Platform queries for the classic-bench harness: CPU pinning, frequency and host description.
#pragma once

#include <optional>
#include <string>
#include <vector>

namespace cb {

// Logical CPUs this process may run on, in ascending order.
std::vector<int> allowed_cpus();

// True if this platform can pin a process to one CPU.
bool pinning_supported();

// Pins the calling process to `cpu`; returns an error message on failure.
std::optional<std::string> pin_to_cpu(int cpu);

// Current frequency in MHz as reported by the OS for `cpu`, or nothing if unavailable.
// `per_cpu` reports whether the value is specific to that CPU rather than system-wide.
std::optional<double> cpu_mhz(int cpu, bool &per_cpu);

// Name of the frequency source (for example a sysctl or sysfs path pattern), or "unavailable".
std::string frequency_source();

struct HostInfo {
    std::string os;
    std::string release;
    std::string machine;
    std::string cpu_model;
    int logical_cpus;
};

HostInfo host_info();

} // namespace cb
