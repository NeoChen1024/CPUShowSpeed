// classic-bench: runs the modified Dhrystone, Whetstone and LINPACK kernels as N pinned copies
// for a set duration and writes one JSON document to stdout (progress and errors go to stderr).
#include <fcntl.h>
#include <getopt.h>
#include <poll.h>
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <functional>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

#include "build_info.h"
#include "classic_kernel.h"
#include "platform.hpp"

using nlohmann::json;

namespace {

constexpr double kLinpackOps = 2.0 * 100.0 * 100.0 * 100.0 / 3.0 + 2.0 * 100.0 * 100.0;

struct Benchmark {
    std::string id;
    std::string family;
    std::string unit;
    std::string precision;
    std::string variant;
    std::function<int()> init;
    std::function<int(long, double *)> run;
    double work_per_pass; // in the unit's work quantity
    double scale;         // score = work / kernel seconds * scale; definitions are in docs/classic-bench.md
};

const std::vector<Benchmark> &benchmarks() {
    static const std::vector<Benchmark> list = {
        {"dhrystone-1.1", "Dhrystone", "DMIPS", "", "1.1", [] { return dhry11_init(); },
         [](long n, double *s) { return dhry11_run(n, s); }, 1.0, 1.0 / 1757.0},
        {"dhrystone-2.1", "Dhrystone", "DMIPS", "", "2.1", [] { return dhry21_init() < 0 ? -1 : 0; },
         [](long n, double *s) { return dhry21_run(n, s); }, 1.0, 1.0 / 1757.0},
        {"whetstone-sp", "Whetstone", "MWIPS", "single", "", [] { return 0; },
         [](long n, double *s) { return whet_sp_run(n, s); }, 10.0, 1.0},
        {"whetstone-dp", "Whetstone", "MWIPS", "double", "", [] { return 0; },
         [](long n, double *s) { return whet_dp_run(n, s); }, 10.0, 1.0},
        {"linpack100-dp-rolled", "LINPACK", "MFLOPS", "double", "rolled", [] { return 0; },
         [](long n, double *s) { return linpack_dp_run(n, 1, s); }, kLinpackOps / 1e6, 1.0},
        {"linpack100-dp-unrolled", "LINPACK", "MFLOPS", "double", "unrolled", [] { return 0; },
         [](long n, double *s) { return linpack_dp_run(n, 0, s); }, kLinpackOps / 1e6, 1.0},
        {"linpack100-sp-rolled", "LINPACK", "MFLOPS", "single", "rolled", [] { return 0; },
         [](long n, double *s) { return linpack_sp_run(n, 1, s); }, kLinpackOps / 1e6, 1.0},
        {"linpack100-sp-unrolled", "LINPACK", "MFLOPS", "single", "unrolled", [] { return 0; },
         [](long n, double *s) { return linpack_sp_run(n, 0, s); }, kLinpackOps / 1e6, 1.0},
    };
    return list;
}

struct Options {
    std::vector<std::string> benchmarks;
    std::vector<int> copies = {1}; // one run of every benchmark per entry, in order
    double duration = 10.0;
    double warmup = 2.0;
    double interval = 1.0;
    double unit_ms = 20.0;
    std::vector<int> cpus;
    bool pin = true;
    bool per_copy_series = false;
};

enum Kind : int32_t { kReady = 0, kUnit = 1, kError = 2 };

// Fixed-size record; writes of at most PIPE_BUF bytes to a pipe are atomic, so copies can share one pipe.
struct Record {
    int32_t copy;
    int32_t kind;
    int32_t check_failed;
    int32_t measured;
    int64_t passes;
    double start;
    double end;
    double kernel_seconds;
    char message[64];
};
static_assert(sizeof(Record) <= 512, "record must fit in PIPE_BUF");

void write_record(int fd, const Record &r) {
    const char *p = reinterpret_cast<const char *>(&r);
    size_t left = sizeof(r);
    while (left > 0) {
        ssize_t n = write(fd, p, left);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            _exit(3);
        }
        p += n;
        left -= static_cast<size_t>(n);
    }
}

// Output precision: times to the microsecond, rates to five significant digits (interval rates are not
// reproducible beyond that), frequencies to the MHz.
double round_us(double seconds) { return std::round(seconds * 1e6) / 1e6; }

double round_sig(double v) {
    if (!std::isfinite(v) || v == 0)
        return v;
    double scale = std::pow(10.0, 4 - static_cast<int>(std::floor(std::log10(std::fabs(v)))));
    return std::round(v * scale) / scale;
}

json median_min_max(std::vector<double> v) {
    if (v.empty())
        return nullptr;
    std::sort(v.begin(), v.end());
    size_t m = v.size();
    return {{"median", round_sig(m % 2 ? v[m / 2] : (v[m / 2 - 1] + v[m / 2]) / 2)},
            {"minimum", round_sig(v.front())},
            {"maximum", round_sig(v.back())}};
}

std::string utc_now() {
    std::time_t t = std::time(nullptr);
    std::tm tm{};
    gmtime_r(&t, &tm);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &tm);
    return buf;
}

[[noreturn]] void usage(int code) {
    std::FILE *out = code == 0 ? stdout : stderr;
    std::fprintf(out,
                 "Usage: classic-bench [options]\n"
                 "  -b, --benchmark ID    benchmark to run; repeatable or comma-separated; 'all' (default)\n"
                 "  -c, --copies N[,N...] independent processes, one per CPU; a list runs every benchmark\n"
                 "                        once per entry, e.g. 1,16 (default 1)\n"
                 "  -d, --duration S      measured seconds per benchmark (default 10)\n"
                 "  -w, --warmup S        unscored seconds before measuring (default 2)\n"
                 "  -i, --interval S      reporting interval in seconds (default 1)\n"
                 "      --unit-ms MS      target wall time of one timed unit (default 20)\n"
                 "      --cpus LIST       CPUs to use, e.g. 0,2,4-7 (default: the first N allowed)\n"
                 "      --no-pin          do not pin copies to CPUs\n"
                 "      --per-copy-series also record every copy's rate in each interval\n"
                 "  -l, --list            list benchmark IDs and exit\n"
                 "  -h, --help            show this help\n");
    std::exit(code);
}

std::vector<int> parse_cpus(const std::string &text) {
    std::vector<int> cpus;
    std::stringstream ss(text);
    std::string part;
    while (std::getline(ss, part, ',')) {
        auto dash = part.find('-');
        if (dash == std::string::npos) {
            cpus.push_back(std::stoi(part));
        } else {
            int a = std::stoi(part.substr(0, dash)), b = std::stoi(part.substr(dash + 1));
            for (int c = a; c <= b; ++c)
                cpus.push_back(c);
        }
    }
    return cpus;
}

Options parse(int argc, char **argv) {
    Options o;
    static const option longopts[] = {{"benchmark", required_argument, nullptr, 'b'},
                                      {"copies", required_argument, nullptr, 'c'},
                                      {"duration", required_argument, nullptr, 'd'},
                                      {"warmup", required_argument, nullptr, 'w'},
                                      {"interval", required_argument, nullptr, 'i'},
                                      {"unit-ms", required_argument, nullptr, 'u'},
                                      {"cpus", required_argument, nullptr, 'p'},
                                      {"no-pin", no_argument, nullptr, 'n'},
                                      {"per-copy-series", no_argument, nullptr, 's'},
                                      {"list", no_argument, nullptr, 'l'},
                                      {"help", no_argument, nullptr, 'h'},
                                      {nullptr, 0, nullptr, 0}};
    int ch;
    try {
        while ((ch = getopt_long(argc, argv, "b:c:d:w:i:lh", longopts, nullptr)) != -1) {
            switch (ch) {
            case 'b': {
                std::stringstream ss(optarg);
                std::string id;
                while (std::getline(ss, id, ','))
                    o.benchmarks.push_back(id);
                break;
            }
            case 'c': {
                o.copies.clear();
                std::stringstream ss(optarg);
                std::string n;
                while (std::getline(ss, n, ','))
                    o.copies.push_back(std::stoi(n));
                break;
            }
            case 'd': o.duration = std::stod(optarg); break;
            case 'w': o.warmup = std::stod(optarg); break;
            case 'i': o.interval = std::stod(optarg); break;
            case 'u': o.unit_ms = std::stod(optarg); break;
            case 'p': o.cpus = parse_cpus(optarg); break;
            case 'n': o.pin = false; break;
            case 's': o.per_copy_series = true; break;
            case 'l':
                for (const auto &b : benchmarks())
                    std::printf("%-24s %s\n", b.id.c_str(), b.unit.c_str());
                std::exit(0);
            case 'h': usage(0);
            default: usage(2);
            }
        }
    } catch (const std::exception &) {
        std::fprintf(stderr, "classic-bench: invalid option value\n");
        usage(2);
    }
    if (optind < argc)
        usage(2);
    if (o.benchmarks.empty() || (o.benchmarks.size() == 1 && o.benchmarks[0] == "all")) {
        o.benchmarks.clear();
        for (const auto &b : benchmarks())
            o.benchmarks.push_back(b.id);
    }
    auto bad = [](const char *msg) {
        std::fprintf(stderr, "classic-bench: %s\n", msg);
        std::exit(2);
    };
    if (o.copies.empty() || *std::min_element(o.copies.begin(), o.copies.end()) < 1)
        bad("--copies must list counts of at least 1");
    if (std::set<int>(o.copies.begin(), o.copies.end()).size() != o.copies.size())
        bad("--copies must not repeat a count");
    if (!(o.duration > 0) || !(o.warmup >= 0) || !(o.interval >= 0.1) || !(o.unit_ms >= 1))
        bad("need --duration > 0, --warmup >= 0, --interval >= 0.1 and --unit-ms >= 1");
    if (o.unit_ms * 2 > o.interval * 1000)
        bad("--unit-ms must be at most half of --interval");
    return o;
}

// Child process: pin, calibrate a pass count, wait at the barrier, then run units until the window ends.
[[noreturn]] void child(const Benchmark &b, const Options &o, int copy, int cpu, int go_fd, int report_fd) {
    Record r{};
    r.copy = copy;
    auto fail = [&](const std::string &msg) {
        r.kind = kError;
        std::snprintf(r.message, sizeof(r.message), "%s", msg.c_str());
        write_record(report_fd, r);
        _exit(1);
    };
    if (cpu >= 0)
        if (auto err = cb::pin_to_cpu(cpu))
            fail(*err);
    if (b.init() != 0)
        fail("kernel initialisation failed");

    const double target = o.unit_ms / 1000.0;
    long passes = 1;
    for (int i = 0; i < 64; ++i) {
        double ks, t0 = cb_seconds();
        if (b.run(passes, &ks) != 0)
            fail("result check failed during calibration");
        double wall = cb_seconds() - t0;
        if (wall >= target * 0.8)
            break;
        double grow = wall > 0 ? std::clamp(target / wall * 1.1, 2.0, 100.0) : 100.0;
        if (passes > 1000000000L / static_cast<long>(grow))
            break;
        passes = static_cast<long>(std::ceil(passes * grow));
    }
    r.kind = kReady;
    r.passes = passes;
    write_record(report_fd, r);

    char c;
    while (read(go_fd, &c, 1) > 0) {
    }
    const double t0 = cb_seconds();
    const double window_start = t0 + o.warmup, window_end = window_start + o.duration;
    r.kind = kUnit;
    for (;;) {
        double start = cb_seconds();
        if (start >= window_end)
            break;
        double ks;
        r.check_failed = b.run(passes, &ks) != 0;
        r.start = start;
        r.end = cb_seconds();
        r.kernel_seconds = ks;
        r.measured = start >= window_start;
        write_record(report_fd, r);
        if (r.check_failed)
            break;
    }
    _exit(0);
}

struct CopyStats {
    int cpu = -1;
    long passes = 0;
    long units = 0;
    double work = 0, kernel_seconds = 0, first_start = 0, last_end = 0;
    bool check_failed = false;
};

// Runs `b` as `ncopies` copies; pinned copies use the first `ncopies` entries of `cpus`.
json run_benchmark(const Benchmark &b, const Options &o, int ncopies, const std::vector<int> &cpus) {
    std::fprintf(stderr, "classic-bench: %s, %d cop%s, %.0f s\n", b.id.c_str(), ncopies, ncopies == 1 ? "y" : "ies", o.duration);
    int go[2], report[2];
    if (pipe(go) != 0 || pipe(report) != 0) {
        std::perror("pipe");
        std::exit(1);
    }
    std::vector<pid_t> pids;
    for (int i = 0; i < ncopies; ++i) {
        std::fflush(nullptr);
        pid_t pid = fork();
        if (pid < 0) {
            std::perror("fork");
            std::exit(1);
        }
        if (pid == 0) {
            close(go[1]);
            close(report[0]);
            child(b, o, i, o.pin ? cpus[i] : -1, go[0], report[1]);
        }
        pids.push_back(pid);
    }
    close(go[0]);
    close(report[1]);

    std::vector<CopyStats> copies(ncopies);
    for (int i = 0; i < ncopies; ++i)
        copies[i].cpu = o.pin ? cpus[i] : -1;
    std::vector<std::string> errors;
    // interval index -> per copy (work, kernel seconds)
    std::map<long, std::vector<std::pair<double, double>>> intervals;
    const std::string start_utc = utc_now();
    double window_start = 0;
    int ready = 0;
    bool started = false;
    double next_sample = 0;

    // Frequency is sampled at every interval boundary but only its mean over the run is kept. Pinned copies sample
    // their own CPUs; unpinned copies migrate, so every allowed CPU is sampled. A system-wide source (per_cpu false)
    // is sampled once per boundary and reported without a CPU list.
    std::vector<int> freq_cpus = o.pin ? std::vector<int>(cpus.begin(), cpus.begin() + ncopies) : cb::allowed_cpus();
    std::vector<double> mhz_sum(freq_cpus.size(), 0.0);
    std::vector<long> mhz_count(freq_cpus.size(), 0);
    bool freq_per_cpu = true;
    long freq_samples = 0;
    auto sample_frequency = [&]() {
        ++freq_samples;
        for (size_t i = 0; i < freq_cpus.size(); ++i) {
            bool per_cpu = false;
            auto mhz = cb::cpu_mhz(freq_cpus[i], per_cpu);
            if (!mhz)
                continue;
            mhz_sum[i] += *mhz;
            ++mhz_count[i];
            if (!per_cpu) {
                freq_per_cpu = false;
                break;
            }
        }
    };
    auto mean_mhz = [&](size_t i) -> json {
        return mhz_count[i] ? json(std::round(mhz_sum[i] / mhz_count[i])) : json(nullptr);
    };

    for (;;) {
        int timeout = -1;
        if (started) {
            double wait = next_sample - cb_seconds();
            timeout = wait > 0 ? static_cast<int>(wait * 1000) + 1 : 0;
        }
        pollfd pfd{report[0], POLLIN, 0};
        int rc = poll(&pfd, 1, timeout);
        if (rc < 0 && errno != EINTR) {
            std::perror("poll");
            break;
        }
        if (started && cb_seconds() >= next_sample) {
            sample_frequency();
            next_sample += o.interval;
        }
        if (rc <= 0)
            continue;
        Record r;
        ssize_t n = read(report[0], &r, sizeof(r));
        if (n == 0)
            break;
        if (n != static_cast<ssize_t>(sizeof(r))) {
            errors.push_back("short read from a copy");
            break;
        }
        CopyStats &c = copies.at(r.copy);
        if (r.kind == kError) {
            errors.push_back("copy " + std::to_string(r.copy) + ": " + r.message);
        } else if (r.kind == kReady) {
            c.passes = r.passes;
            if (++ready == ncopies && errors.empty()) {
                window_start = cb_seconds() + o.warmup;
                next_sample = window_start;
                started = true;
                close(go[1]); // releases every copy at once
            }
        } else if (r.kind == kUnit) {
            c.check_failed = c.check_failed || r.check_failed;
            if (!r.measured)
                continue;
            if (c.units == 0)
                c.first_start = r.start;
            ++c.units;
            c.work += r.passes * b.work_per_pass;
            c.kernel_seconds += r.kernel_seconds;
            c.last_end = r.end;
            long k = static_cast<long>(std::floor((r.end - window_start) / o.interval));
            // Units start inside the window but may end just after it; they belong to the last interval.
            const long last = static_cast<long>(std::ceil(o.duration / o.interval)) - 1;
            k = std::clamp(k, 0L, last);
            auto &slot = intervals[k];
            slot.resize(ncopies, {0.0, 0.0});
            slot[r.copy].first += r.passes * b.work_per_pass;
            slot[r.copy].second += r.kernel_seconds;
        }
        if (!errors.empty() && !started) {
            for (pid_t p : pids)
                kill(p, SIGTERM);
            close(go[1]);
            started = true;
        }
    }
    close(report[0]);
    for (pid_t p : pids) {
        int status = 0;
        waitpid(p, &status, 0);
        if (!WIFEXITED(status) || WEXITSTATUS(status) != 0)
            errors.push_back("a copy exited abnormally");
    }

    json result = {{"benchmark", b.id},
                   {"copies", ncopies},
                   {"family", b.family},
                   {"unit", b.unit},
                   {"precision", b.precision.empty() ? json(nullptr) : json(b.precision)},
                   {"variant", b.variant.empty() ? json(nullptr) : json(b.variant)},
                   {"start_utc", start_utc},
                   {"end_utc", utc_now()}};
    json per_copy = json::array();
    double aggregate = 0;
    bool valid = errors.empty();
    for (size_t i = 0; i < copies.size(); ++i) {
        const auto &c = copies[i];
        double score = c.kernel_seconds > 0 ? c.work / c.kernel_seconds * b.scale : 0;
        valid = valid && !c.check_failed && c.units > 0;
        aggregate += score;
        std::vector<double> copy_rates;
        for (const auto &[k, slot] : intervals)
            if (slot[i].second > 0)
                copy_rates.push_back(slot[i].first / slot[i].second * b.scale);
        per_copy.push_back({{"copy", i},
                            {"cpu", c.cpu >= 0 ? json(c.cpu) : json(nullptr)},
                            {"passes_per_unit", c.passes},
                            {"units", c.units},
                            {"kernel_seconds", round_us(c.kernel_seconds)},
                            {"wall_seconds", round_us(c.units ? c.last_end - c.first_start : 0.0)},
                            {"result_check", c.check_failed ? "failed" : "passed"},
                            {"score", round_sig(score)},
                            {"intervals", median_min_max(copy_rates)},
                            {"mean_mhz", o.pin && freq_per_cpu ? mean_mhz(i) : json(nullptr)}});
    }
    json series = json::array();
    std::vector<double> rates;
    for (const auto &[k, slot] : intervals) {
        json copy_rates = json::array();
        double total = 0;
        bool complete = true;
        for (const auto &[work, ks] : slot) {
            if (ks > 0) {
                double rate = work / ks * b.scale;
                copy_rates.push_back(round_sig(rate));
                total += rate;
            } else {
                copy_rates.push_back(nullptr);
                complete = false;
            }
        }
        json entry = {{"t_s", round_us(std::min((k + 1) * o.interval, o.duration))},
                      {"aggregate", round_sig(total)},
                      {"complete", complete}};
        if (o.per_copy_series)
            entry["per_copy"] = copy_rates;
        series.push_back(entry);
        if (complete)
            rates.push_back(total);
    }
    json interval_summary = {{"length_s", o.interval}, {"complete", rates.size()}};
    if (json mmm = median_min_max(rates); !mmm.is_null())
        interval_summary.update(mmm);
    double all_sum = 0;
    long all_count = 0;
    for (size_t i = 0; i < freq_cpus.size(); ++i) {
        all_sum += mhz_sum[i];
        all_count += mhz_count[i];
    }
    result["valid"] = valid;
    result["errors"] = errors;
    result["aggregate_score"] = round_sig(aggregate);
    result["per_copy"] = per_copy;
    result["intervals"] = interval_summary;
    result["interval_series"] = series;
    result["frequency"] = {{"cpus", freq_per_cpu ? json(freq_cpus) : json(nullptr)},
                           {"samples", freq_samples},
                           {"mean_mhz", all_count ? json(std::round(all_sum / all_count)) : json(nullptr)}};
    std::fprintf(stderr, "classic-bench: %s %s %.6g %s\n", b.id.c_str(), valid ? "ok" : "INVALID", aggregate,
                 b.unit.c_str());
    return result;
}

} // namespace

int main(int argc, char **argv) {
    Options o = parse(argc, argv);
    std::vector<const Benchmark *> selected;
    for (const auto &id : o.benchmarks) {
        auto it = std::find_if(benchmarks().begin(), benchmarks().end(), [&](const Benchmark &b) { return b.id == id; });
        if (it == benchmarks().end()) {
            std::fprintf(stderr, "classic-bench: unknown benchmark '%s' (see --list)\n", id.c_str());
            return 2;
        }
        selected.push_back(&*it);
    }
    std::vector<int> cpus;
    if (o.pin) {
        if (!cb::pinning_supported()) {
            std::fprintf(stderr, "classic-bench: CPU pinning is not supported here; continuing unpinned\n");
            o.pin = false;
        } else {
            std::vector<int> allowed = cb::allowed_cpus();
            cpus = o.cpus.empty() ? allowed : o.cpus;
            const int most = *std::max_element(o.copies.begin(), o.copies.end());
            if (static_cast<int>(cpus.size()) < most) {
                std::fprintf(stderr, "classic-bench: %d copies need %d CPUs, %zu available (use --cpus or --no-pin)\n",
                             most, most, cpus.size());
                return 2;
            }
            cpus.resize(most);
        }
    }

    cb::HostInfo host = cb::host_info();
    json doc;
    doc["schema"] = "classic-bench-v1";
    doc["tool"] = {{"name", "classic-bench"},
                   {"version", CB_VERSION},
                   {"build",
                    {{"profile", CB_PROFILE},
                     {"c_compiler", CB_C_COMPILER},
                     {"c_compiler_version", CB_C_COMPILER_VERSION},
                     {"kernel_c_flags", CB_KERNEL_FLAGS},
                     {"kernel_c_dialect", "gnu89"},
                     {"interprocedural_optimization", false},
                     {"cxx_compiler", CB_CXX_COMPILER},
                     {"target_processor", CB_TARGET_PROCESSOR}}},
                   {"sources", json::parse(CB_SOURCES_JSON)}};
    doc["host"] = {{"os", host.os},
                   {"release", host.release},
                   {"machine", host.machine},
                   {"cpu_model", host.cpu_model.empty() ? json(nullptr) : json(host.cpu_model)},
                   {"logical_cpus", host.logical_cpus},
                   {"frequency_source", cb::frequency_source()}};
    doc["settings"] = {{"copies", o.copies},
                       {"pinned", o.pin},
                       {"cpus", o.pin ? json(cpus) : json(nullptr)},
                       {"duration_s", o.duration},
                       {"warmup_s", o.warmup},
                       {"interval_s", o.interval},
                       {"unit_target_ms", o.unit_ms},
                       {"per_copy_series", o.per_copy_series},
                       {"timer", "CLOCK_MONOTONIC"}};
    json results = json::array();
    bool all_valid = true;
    // Every benchmark at the first count, then every benchmark at the next.
    for (int n : o.copies)
        for (const Benchmark *b : selected) {
            json r = run_benchmark(*b, o, n, cpus);
            all_valid = all_valid && r["valid"].get<bool>();
            results.push_back(std::move(r));
        }
    doc["results"] = results;
    std::cout << doc.dump(2) << std::endl;
    return all_valid ? 0 : 1;
}
