// Platform queries for Linux, FreeBSD, NetBSD and OpenBSD. Unavailable values are reported as missing, never estimated.
#if defined(__linux__)
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <sched.h>
#elif defined(__FreeBSD__)
#include <sys/param.h>
#include <sys/cpuset.h>
#include <sys/sysctl.h>
#elif defined(__NetBSD__)
#include <sched.h>
#include <sys/sysctl.h>
#elif defined(__OpenBSD__)
#include <sys/types.h>
#include <sys/sysctl.h>
#endif

#include <sys/utsname.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <fstream>
#include <sstream>

#include "platform.hpp"

namespace cb {

namespace {

[[maybe_unused]] std::optional<std::string> read_first_line(const std::string &path) {
    std::ifstream in(path);
    std::string line;
    if (in && std::getline(in, line))
        return line;
    return std::nullopt;
}

#if defined(__FreeBSD__) || defined(__NetBSD__)
std::optional<std::string> sysctl_string(const char *name) {
    size_t len = 0;
    if (sysctlbyname(name, nullptr, &len, nullptr, 0) != 0 || len == 0)
        return std::nullopt;
    std::string value(len, '\0');
    if (sysctlbyname(name, value.data(), &len, nullptr, 0) != 0)
        return std::nullopt;
    value.resize(strnlen(value.c_str(), len));
    return value;
}

std::optional<long> sysctl_number(const char *name) {
    // The frequency sysctls are int on some releases and long or uint64 on others.
    unsigned char buf[8] = {};
    size_t len = sizeof(buf);
    if (sysctlbyname(name, buf, &len, nullptr, 0) != 0)
        return std::nullopt;
    if (len == sizeof(int)) {
        int v;
        std::memcpy(&v, buf, sizeof(v));
        return v;
    }
    if (len == sizeof(long long)) {
        long long v;
        std::memcpy(&v, buf, sizeof(v));
        return static_cast<long>(v);
    }
    return std::nullopt;
}
#endif

} // namespace

std::vector<int> allowed_cpus() {
    std::vector<int> cpus;
#if defined(__linux__)
    cpu_set_t set;
    CPU_ZERO(&set);
    if (sched_getaffinity(0, sizeof(set), &set) == 0) {
        for (int i = 0; i < CPU_SETSIZE; ++i)
            if (CPU_ISSET(i, &set))
                cpus.push_back(i);
        return cpus;
    }
#elif defined(__FreeBSD__)
    cpuset_t set;
    CPU_ZERO(&set);
    if (cpuset_getaffinity(CPU_LEVEL_WHICH, CPU_WHICH_PID, -1, sizeof(set), &set) == 0) {
        for (int i = 0; i < CPU_SETSIZE; ++i)
            if (CPU_ISSET(i, &set))
                cpus.push_back(i);
        return cpus;
    }
#endif
    long n = sysconf(_SC_NPROCESSORS_ONLN);
    for (int i = 0; i < n; ++i)
        cpus.push_back(i);
    return cpus;
}

bool pinning_supported() {
#if defined(__linux__) || defined(__FreeBSD__) || defined(__NetBSD__)
    return true;
#else
    return false;
#endif
}

std::optional<std::string> pin_to_cpu(int cpu) {
#if defined(__linux__)
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0)
        return std::string("sched_setaffinity: ") + std::strerror(errno);
    return std::nullopt;
#elif defined(__FreeBSD__)
    cpuset_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (cpuset_setaffinity(CPU_LEVEL_WHICH, CPU_WHICH_PID, -1, sizeof(set), &set) != 0)
        return std::string("cpuset_setaffinity: ") + std::strerror(errno);
    return std::nullopt;
#elif defined(__NetBSD__)
    cpuset_t *set = cpuset_create();
    if (set == nullptr)
        return std::string("cpuset_create failed");
    cpuset_zero(set);
    cpuset_set(static_cast<cpuid_t>(cpu), set);
    int rc = sched_setaffinity_np(getpid(), cpuset_size(set), set);
    int err = errno;
    cpuset_destroy(set);
    if (rc != 0)
        return std::string("sched_setaffinity_np: ") + std::strerror(err);
    return std::nullopt;
#else
    (void)cpu;
    return std::string("CPU pinning is not supported on this platform");
#endif
}

std::optional<double> cpu_mhz(int cpu, bool &per_cpu) {
    per_cpu = false;
#if defined(__linux__)
    auto line = read_first_line("/sys/devices/system/cpu/cpu" + std::to_string(cpu) + "/cpufreq/scaling_cur_freq");
    if (!line)
        return std::nullopt;
    try {
        per_cpu = true;
        return std::stod(*line) / 1000.0; // kHz
    } catch (...) {
        per_cpu = false;
        return std::nullopt;
    }
#elif defined(__FreeBSD__)
    std::string name = "dev.cpu." + std::to_string(cpu) + ".freq";
    if (auto v = sysctl_number(name.c_str())) {
        per_cpu = true;
        return static_cast<double>(*v);
    }
    if (auto v = sysctl_number("dev.cpu.0.freq"))
        return static_cast<double>(*v);
    return std::nullopt;
#elif defined(__NetBSD__)
    (void)cpu;
    if (auto v = sysctl_number("machdep.cpu.frequency.current"))
        return static_cast<double>(*v);
    return std::nullopt;
#elif defined(__OpenBSD__)
    (void)cpu;
    int mib[2] = {CTL_HW, HW_CPUSPEED};
    int mhz = 0;
    size_t len = sizeof(mhz);
    if (sysctl(mib, 2, &mhz, &len, nullptr, 0) == 0)
        return static_cast<double>(mhz);
    return std::nullopt;
#else
    (void)cpu;
    return std::nullopt;
#endif
}

std::string frequency_source() {
#if defined(__linux__)
    return "/sys/devices/system/cpu/cpuN/cpufreq/scaling_cur_freq";
#elif defined(__FreeBSD__)
    return "sysctl dev.cpu.N.freq";
#elif defined(__NetBSD__)
    return "sysctl machdep.cpu.frequency.current";
#elif defined(__OpenBSD__)
    return "sysctl hw.cpuspeed";
#else
    return "unavailable";
#endif
}

HostInfo host_info() {
    HostInfo info;
    struct utsname u;
    if (uname(&u) == 0) {
        info.os = u.sysname;
        info.release = u.release;
        info.machine = u.machine;
    }
    info.logical_cpus = static_cast<int>(sysconf(_SC_NPROCESSORS_ONLN));
#if defined(__linux__)
    std::ifstream in("/proc/cpuinfo");
    std::string line;
    while (std::getline(in, line)) {
        auto colon = line.find(':');
        if (colon == std::string::npos)
            continue;
        std::string key = line.substr(0, colon);
        while (!key.empty() && (key.back() == ' ' || key.back() == '\t'))
            key.pop_back();
        if (key == "model name" || key == "Model" || key == "cpu model" || key == "cpu") {
            std::string value = line.substr(colon + 1);
            value.erase(0, value.find_first_not_of(" \t"));
            if (!value.empty()) {
                info.cpu_model = value;
                break;
            }
        }
    }
#elif defined(__FreeBSD__)
    info.cpu_model = sysctl_string("hw.model").value_or("");
#elif defined(__NetBSD__)
    info.cpu_model = sysctl_string("machdep.cpu_brand").value_or(sysctl_string("hw.model").value_or(""));
#elif defined(__OpenBSD__)
    int mib[2] = {CTL_HW, HW_MODEL};
    char model[256] = {};
    size_t len = sizeof(model);
    if (sysctl(mib, 2, model, &len, nullptr, 0) == 0)
        info.cpu_model = model;
#endif
    return info;
}

} // namespace cb
