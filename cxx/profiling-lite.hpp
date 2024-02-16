#pragma once

#include <cstdint>
#include <string_view>

namespace profiling_lite {

using thread_id = uint64_t;
using timestamp_t = uint64_t;

//! Structure defining a (static) location in the code.
struct location {
  //! The name of the location, what would be displayed by default as the name of the zone.
  const char* name;
  //! The function name.
  const char* function;
  //! The file name.
  const char* file;
  //! The line number.
  uint32_t line;
};

#define PROFILING_LITE_CURRENT_LOCATION()                                                          \
  [](const char* f) -> profiling_lite::location* {                                                 \
    static profiling_lite::location l{f, f, __FILE__, __LINE__};                                   \
    return &l;                                                                                     \
  }(__FUNCTION__)
#define PROFILING_LITE_CURRENT_LOCATION_N(name)                                                    \
  [](const char* f) -> profiling_lite::location* {                                                 \
    static profiling_lite::location l{name, f, __FILE__, __LINE__};                                \
    return &l;                                                                                     \
  }(__FUNCTION__)

thread_id get_current_thread();
timestamp_t get_time();

void set_thread_name(thread_id tid, const char* name);
void define_counter_track(uint64_t tid, const char* name);

void emit_zone_start(thread_id tid, timestamp_t timestamp, const location* static_location);
void emit_zone_end(thread_id tid, timestamp_t timestamp);
void emit_zone_dynamic_name(thread_id tid, const char* dyn_name);
void emit_zone_param(thread_id tid, const char* static_name, bool value);
void emit_zone_param(thread_id tid, const char* static_name, int64_t value);
void emit_zone_param(thread_id tid, const char* static_name, uint64_t value);
void emit_zone_param(thread_id tid, const char* static_name, double value);
void emit_zone_param(thread_id tid, const char* static_name, const char* dyn_value);
void emit_zone_flow(thread_id tid, uint64_t flow_id);
void emit_zone_category(thread_id tid, const char* static_name);

void emit_counter_value(thread_id tid, timestamp_t timestamp, int64_t value);
void emit_counter_value(thread_id tid, timestamp_t timestamp, double value);

void emit_thread_switch_start(thread_id tid, uint64_t switch_id);
void emit_thread_switch_end(thread_id tid, timestamp_t timestamp, uint64_t switch_id);

void emit_spawn(uint64_t spawn_id, thread_id tid, timestamp_t timestamp, uint8_t num_threads);
void emit_spawn_continue(uint64_t spawn_id, thread_id tid, timestamp_t timestamp);
void emit_spawn_ending(uint64_t spawn_id, thread_id tid, timestamp_t timestamp);
void emit_spawn_done(uint64_t spawn_id, thread_id tid, timestamp_t timestamp);

struct zone {
  explicit zone(const location* loc) { emit_zone_start(get_current_thread(), get_time(), loc); }

  ~zone() { emit_zone_end(get_current_thread(), get_time()); }

  void set_dyn_name(std::string_view name) {
    emit_zone_dynamic_name(get_current_thread(), name.data());
  }
  void set_param(const char* static_name, bool value) {
    emit_zone_param(get_current_thread(), static_name, value);
  }
  void set_param(const char* static_name, uint64_t value) {
    emit_zone_param(get_current_thread(), static_name, value);
  }
  void set_param(const char* static_name, int64_t value) {
    emit_zone_param(get_current_thread(), static_name, value);
  }
  void set_param(const char* static_name, std::string_view name) {
    emit_zone_param(get_current_thread(), static_name, name.data());
  }
  void add_flow(uint64_t flow_id) { emit_zone_flow(get_current_thread(), flow_id); }
  void set_category(const char* static_name) {
    emit_zone_category(get_current_thread(), static_name);
  }
};

} // namespace profiling_lite