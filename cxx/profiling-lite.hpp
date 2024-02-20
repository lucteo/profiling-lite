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
timestamp_t now();

void define_stack(const void* begin, const void* end, const char* name);
void set_thread_name(thread_id tid, const char* name);

void emit_zone_start(const void* stack_ptr, thread_id tid, timestamp_t timestamp,
                     const location* static_location);
void emit_zone_end(const void* stack_ptr, timestamp_t timestamp);
void emit_zone_dynamic_name(const void* stack_ptr, const char* dyn_name);
void emit_zone_param(const void* stack_ptr, const char* static_name, bool value);
void emit_zone_param(const void* stack_ptr, const char* static_name, int64_t value);
void emit_zone_param(const void* stack_ptr, const char* static_name, uint64_t value);
void emit_zone_param(const void* stack_ptr, const char* static_name, double value);
void emit_zone_param(const void* stack_ptr, const char* static_name, const char* dyn_value);
void emit_zone_flow(const void* stack_ptr, uint64_t flow_id);
void emit_zone_flow_terminate(const void* stack_ptr, uint64_t flow_id);
void emit_zone_category(const void* stack_ptr, const char* static_name);

void define_counter_track(uint64_t tid, const char* name);
void emit_counter_value(thread_id tid, timestamp_t timestamp, int64_t value);
void emit_counter_value(thread_id tid, timestamp_t timestamp, double value);

struct zone {
  explicit zone(const location* loc) { emit_zone_start(this, get_current_thread(), now(), loc); }

  ~zone() { emit_zone_end(this, now()); }

  void set_dyn_name(std::string_view name) { emit_zone_dynamic_name(this, name.data()); }
  void set_param(const char* static_name, bool value) { emit_zone_param(this, static_name, value); }
  void set_param(const char* static_name, uint64_t value) {
    emit_zone_param(this, static_name, value);
  }
  void set_param(const char* static_name, int64_t value) {
    emit_zone_param(this, static_name, value);
  }
  void set_param(const char* static_name, std::string_view name) {
    emit_zone_param(this, static_name, name.data());
  }
  void add_flow(uint64_t flow_id) { emit_zone_flow(this, flow_id); }
  void add_flow_terminate(uint64_t flow_id) { emit_zone_flow_terminate(this, flow_id); }
  void set_category(const char* static_name) { emit_zone_category(this, static_name); }
};

struct zone_instant {
  explicit zone_instant(const location* loc) : timestamp_(now()) {
    emit_zone_start(this, get_current_thread(), timestamp_, loc);
  }

  ~zone_instant() { emit_zone_end(this, timestamp_); }

  void set_dyn_name(std::string_view name) { emit_zone_dynamic_name(this, name.data()); }
  void set_param(const char* static_name, bool value) { emit_zone_param(this, static_name, value); }
  void set_param(const char* static_name, uint64_t value) {
    emit_zone_param(this, static_name, value);
  }
  void set_param(const char* static_name, int64_t value) {
    emit_zone_param(this, static_name, value);
  }
  void set_param(const char* static_name, std::string_view name) {
    emit_zone_param(this, static_name, name.data());
  }
  void add_flow(uint64_t flow_id) { emit_zone_flow(this, flow_id); }
  void add_flow_terminate(uint64_t flow_id) { emit_zone_flow_terminate(this, flow_id); }
  void set_category(const char* static_name) { emit_zone_category(this, static_name); }

private:
  uint64_t timestamp_;
};

} // namespace profiling_lite