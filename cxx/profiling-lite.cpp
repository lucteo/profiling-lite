#include "profiling-lite.hpp"

#include <cassert>
#include <chrono>
#include <mutex>
#include <thread>
#include <unordered_set>

#include <sstream>

#if defined(__linux__) || defined(__APPLE__)
#include <signal.h>
#endif

namespace profiling_lite {

namespace detail {

uint8_t* to_uint8_ptr(void* p) { return reinterpret_cast<uint8_t*>(p); }
const uint8_t* to_uint8_ptr(const void* p) { return reinterpret_cast<const uint8_t*>(p); }

enum class packet_type : uint8_t {
  free = 0,

  init = 16,
  static_string,
  location,

  stack,
  thread_name,

  zone_start,
  zone_end,
  zone_dynamic_name,
  zone_param_bool,
  zone_param_int,
  zone_param_uint,
  zone_param_double,
  zone_param_string,
  zone_flow,
  zone_flow_terminate,
  zone_category,

  counter_track,
  counter_value_int,
  counter_value_double,
};

#pragma pack(push, 1)

template <packet_type PT> struct packet;

struct packet_base {
  packet_type type_;
};

struct static_packet_base : packet_base {
  static constexpr bool has_dynamic_size = false;
  size_t extra_size() const { return 0; }
};

template <> struct packet<packet_type::init> : static_packet_base {
  char magic_[4];
  uint32_t version_;
};

template <> struct packet<packet_type::static_string> : packet_base {
  uint64_t static_string_;
  uint16_t size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return size_; }
};

template <> struct packet<packet_type::stack> : packet_base {
  uint64_t begin_;
  uint64_t end_;
  uint16_t name_size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return name_size_; }
};

template <> struct packet<packet_type::thread_name> : packet_base {
  thread_id tid_;
  uint16_t name_size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return name_size_; }
};

template <> struct packet<packet_type::location> : static_packet_base {
  uint64_t location_id_;
  uint64_t static_name_;
  uint64_t static_function_;
  uint64_t static_file_;
  uint32_t line_;
};

template <> struct packet<packet_type::zone_start> : static_packet_base {
  uint64_t stack_ptr_;
  thread_id tid_;
  timestamp_t timestamp_;
  uint64_t location_id_;
};
template <> struct packet<packet_type::zone_end> : static_packet_base {
  uint64_t stack_ptr_;
  timestamp_t timestamp_;
};
template <> struct packet<packet_type::zone_dynamic_name> : packet_base {
  uint64_t stack_ptr_;
  uint16_t name_size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return name_size_; }
};
template <> struct packet<packet_type::zone_param_bool> : static_packet_base {
  uint64_t stack_ptr_;
  uint64_t static_name_;
  uint8_t value_;
};
template <> struct packet<packet_type::zone_param_int> : static_packet_base {
  uint64_t stack_ptr_;
  uint64_t static_name_;
  int64_t value_;
};
template <> struct packet<packet_type::zone_param_uint> : static_packet_base {
  uint64_t stack_ptr_;
  uint64_t static_name_;
  uint64_t value_;
};
template <> struct packet<packet_type::zone_param_double> : static_packet_base {
  uint64_t stack_ptr_;
  uint64_t static_name_;
  double value_;
};
template <> struct packet<packet_type::zone_param_string> : packet_base {
  uint64_t stack_ptr_;
  uint64_t static_name_;
  uint16_t value_size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return value_size_; }
};
template <> struct packet<packet_type::zone_flow> : static_packet_base {
  uint64_t stack_ptr_;
  uint64_t flow_id_;
};
template <> struct packet<packet_type::zone_flow_terminate> : static_packet_base {
  uint64_t stack_ptr_;
  uint64_t flow_id_;
};
template <> struct packet<packet_type::zone_category> : static_packet_base {
  uint64_t stack_ptr_;
  uint64_t static_name_;
};

template <> struct packet<packet_type::counter_track> : packet_base {
  thread_id tid_;
  uint16_t name_size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return name_size_; }
};
template <> struct packet<packet_type::counter_value_int> : static_packet_base {
  thread_id tid_;
  timestamp_t timestamp_;
  int64_t value_;
};
template <> struct packet<packet_type::counter_value_double> : static_packet_base {
  thread_id tid_;
  timestamp_t timestamp_;
  double value_;
};

template <packet_type PT> size_t typed_packet_size(const packet_base* pckt) {
  auto p = static_cast<const packet<PT>*>(pckt);
  return sizeof(*p) + p->extra_size();
}

size_t packet_size(const packet_base* pckt) {
  // clang-format off
  switch (pckt->type_) {
  case packet_type::free:                   return 0;
  case packet_type::init:                   return typed_packet_size<packet_type::init>(pckt);
  case packet_type::static_string:          return typed_packet_size<packet_type::static_string>(pckt);
  case packet_type::location:               return typed_packet_size<packet_type::location>(pckt);
  case packet_type::stack:                  return typed_packet_size<packet_type::stack>(pckt);
  case packet_type::thread_name:            return typed_packet_size<packet_type::thread_name>(pckt);
  case packet_type::zone_start:             return typed_packet_size<packet_type::zone_start>(pckt);
  case packet_type::zone_end:               return typed_packet_size<packet_type::zone_end>(pckt);
  case packet_type::zone_dynamic_name:      return typed_packet_size<packet_type::zone_dynamic_name>(pckt);
  case packet_type::zone_param_bool:        return typed_packet_size<packet_type::zone_param_bool>(pckt);
  case packet_type::zone_param_int:         return typed_packet_size<packet_type::zone_param_int>(pckt);
  case packet_type::zone_param_uint:        return typed_packet_size<packet_type::zone_param_uint>(pckt);
  case packet_type::zone_param_double:      return typed_packet_size<packet_type::zone_param_double>(pckt);
  case packet_type::zone_param_string:      return typed_packet_size<packet_type::zone_param_string>(pckt);
  case packet_type::zone_flow:              return typed_packet_size<packet_type::zone_flow>(pckt);
  case packet_type::zone_flow_terminate:    return typed_packet_size<packet_type::zone_flow_terminate>(pckt);
  case packet_type::zone_category:          return typed_packet_size<packet_type::zone_category>(pckt);
  case packet_type::counter_track:          return typed_packet_size<packet_type::counter_track>(pckt);
  case packet_type::counter_value_int:      return typed_packet_size<packet_type::counter_value_int>(pckt);
  case packet_type::counter_value_double:   return typed_packet_size<packet_type::counter_value_double>(pckt);
  }
  // clang-format on
}

#pragma pack(pop)

//! Atomically read (acquire) the type of `pckt`.
packet_type read_type(const packet_base* p) {
  const std::atomic<packet_type>* p_atomic =
      reinterpret_cast<const std::atomic<packet_type>*>(&p->type_);
  return p_atomic->load(std::memory_order_acquire);
}

//! Commits the packet by atomically storing its type.
template <packet_type PT> void commit(packet<PT>* p) {
  std::atomic<packet_type>* p_atomic = reinterpret_cast<std::atomic<packet_type>*>(&p->type_);
  p_atomic->store(PT, std::memory_order_release);
}

//! Returns the next packet after `pckt`.
const packet_base* next_packet(const packet_base* pckt) {
  return reinterpret_cast<const packet_base*>(to_uint8_ptr(pckt) + packet_size(pckt));
}
packet_base* next_packet(packet_base* pckt) {
  return reinterpret_cast<packet_base*>(to_uint8_ptr(pckt) + packet_size(pckt));
}

struct packets_range {
  packet_base* begin_;
  packet_base* end_;

  bool empty() const { return begin_ == end_; }
  size_t size_in_bytes() const { return to_uint8_ptr(end_) - to_uint8_ptr(begin_); }

  void clear() { memset(begin_, 0, size_in_bytes()); }
};

//! Ring buffer used to store profiling packets, decoupling the writers from the reader.
class ring_buffer {
public:
  ring_buffer(size_t size)
      : data_(new uint8_t[size]), size_(size), packet_limit_(data_ + size - 1024) {
    memset(data_, 0, size);
    write_pos_ = data_;
    reading_pos_ = reinterpret_cast<packet_base*>(data_);
  }
  ~ring_buffer() { delete[] data_; }

  //! Acquire space for writing a static packet of the given type.
  template <packet_type PT> packet<PT>* acquire_packet_static() {
    static_assert(!packet<PT>::has_dynamic_size, "Packet type is not static");
    size_t size = sizeof(packet<PT>);
    auto p = reserve_space(size);
    return reinterpret_cast<packet<PT>*>(p);
  }

  //! Acquire space for writing a dynamic packet of the given type, with the given extra size.
  template <packet_type PT> packet<PT>* acquire_packet_dynamic(size_t extra_size) {
    static_assert(packet<PT>::has_dynamic_size, "Packet type is not dynamic");
    size_t size = sizeof(packet<PT>) + extra_size;
    auto p = reserve_space(size);
    return reinterpret_cast<packet<PT>*>(p);
  }

  //! Get a chunk of fully written packets, ready to be consumed by the reader.
  packets_range get_ready_data() {
    auto start = reading_pos_;
    auto current = start;
    auto limit = reinterpret_cast<const packet_base*>(packet_limit_);
    while (current < limit) {
      auto type = read_type(current);
      if (type == packet_type::free)
        break;
      current = next_packet(current);
    }

    if (current >= limit) {
      reading_pos_ = reinterpret_cast<packet_base*>(data_);
    } else {
      reading_pos_ = current;
    }
    return {start, current};
  }

private:
  //! The buffer allocated to store the packets.
  uint8_t* data_;
  //! The size of the data buffer.
  size_t size_;
  //! After this point, we don't write any new packets; however, one packet can extend beyond this.
  uint8_t* packet_limit_;
  //! The position where the next packet will be written.
  std::atomic<uint8_t*> write_pos_;
  //! The position where the reader should start reading next.
  packet_base* reading_pos_;

  //! Reserve space for a packet of the given size (without the type value).
  //! Returns the start of the reserved space.
  uint8_t* reserve_space(size_t size) {
    auto write_pos = write_pos_.load(std::memory_order_relaxed);
    auto last_pos = write_pos;
    while (!write_pos_.compare_exchange_weak(write_pos, next_packet_pos(write_pos, size),
                                             std::memory_order_release)) {
      last_pos = write_pos;
    }

    return last_pos;
  }

  uint8_t* next_packet_pos(uint8_t* p, size_t size) {
    auto res = p + size;
    return res >= packet_limit_ ? data_ : res;
  }
};

class Profiler {
public:
  static Profiler& instance() {
    static Profiler theInstance;
    return theInstance;
  }

  ~Profiler() {
    should_exit_ = true;
    writer_thread_.join();
  }

  ring_buffer& buffer() { return buffer_; }

private:
  static constexpr size_t buffer_size = 4 * 1024 * 1024;
  ring_buffer buffer_;
  std::unordered_set<uint64_t> static_strings_;
  std::unordered_set<uint64_t> static_locations_;
  std::thread writer_thread_;
  std::atomic<bool> should_exit_{false};

  Profiler() : buffer_(buffer_size) {
    auto p = buffer_.acquire_packet_static<packet_type::init>();
    p->magic_[0] = 'P';
    p->magic_[1] = 'R';
    p->magic_[2] = 'O';
    p->magic_[3] = 'F';
    p->version_ = 1;
    commit(p);

    setup_crash_handler();

    writer_thread_ = std::thread(&Profiler::thread_func, this);
  }

  void setup_crash_handler() {
#if defined(__linux__) || defined(__APPLE__)
    struct sigaction sa = {};
    sa.sa_sigaction = handle_crash;
    sa.sa_flags = SA_SIGINFO;
    sigaction(SIGILL, &sa, nullptr);
    sigaction(SIGFPE, &sa, nullptr);
    sigaction(SIGSEGV, &sa, nullptr);
    sigaction(SIGPIPE, &sa, nullptr);
    sigaction(SIGBUS, &sa, nullptr);
    // sigaction(SIGABRT, &sa, nullptr);
#endif
  }

  static std::string current_thread() {
    std::stringstream ss;
    ss << std::this_thread::get_id();
    return ss.str();
  }

  static void handle_crash(int signal, siginfo_t* info, void* /*ucontext*/) {
    emit_zone_start(&signal, get_current_thread(), now(),
                    PROFILING_LITE_CURRENT_LOCATION_N("CRASHED"));
    emit_zone_param(&signal, "signal", static_cast<int64_t>(signal));
    printf("%s: CRASHED\n", current_thread().c_str());
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    emit_zone_end(&signal, now());
    // Wait for a bit, giving the chance for out thread to write the profile data.
    printf("quitting...\n");
    Profiler::instance().should_exit_ = true;
    std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    std::abort();
  }

  void thread_func() {
    auto f = open_capture();
    while (true) {
      // Read one buffer to write to file.
      auto packets_to_write = buffer_.get_ready_data();
      if (packets_to_write.empty()) {
        // No data to write.
        if (should_exit_.load(std::memory_order_relaxed)) {
          // We should exit; make several attempts to write all the available data.
          for (int i = 0; i < 10; i++) {
            write_packets(f, buffer_.get_ready_data());
            std::this_thread::yield();
          }
          break;
        }
        std::this_thread::yield();
      } else {
        write_packets(f, packets_to_write);
      }
    }
  }

  //! Write the packets in the given range to the output file.
  void write_packets(FILE* f, packets_range r) {
    if (r.empty())
      return;

    // Iterate over the packets we need to write, check if we need to do anything else.
    for (const packet_base* p = r.begin_; p < r.end_ && p->type_ != packet_type::free;
         p = next_packet(p)) {
      check_packet_extra_actions(p);
    }
    // Actually write the buffer to the file.
    write_buffer_to_file(f, r.begin_, r.size_in_bytes());
    fflush(f);
    // Clear up the buffer, so that we can reuse it.
    r.clear();
  }

  //! Check if we need to perform anything else on our side for this packet.
  void check_packet_extra_actions(const packet_base* packet_begin) {
    switch (packet_begin->type_) {
    case packet_type::zone_start: {
      auto p = reinterpret_cast<const packet<packet_type::zone_start>*>(packet_begin);
      check_location(p->location_id_);
      break;
    }
    case packet_type::zone_param_bool: {
      auto p = reinterpret_cast<const packet<packet_type::zone_param_bool>*>(packet_begin);
      check_static_string(p->static_name_);
      break;
    }
    case packet_type::zone_param_int: {
      auto p = reinterpret_cast<const packet<packet_type::zone_param_int>*>(packet_begin);
      check_static_string(p->static_name_);
      break;
    }
    case packet_type::zone_param_uint: {
      auto p = reinterpret_cast<const packet<packet_type::zone_param_uint>*>(packet_begin);
      check_static_string(p->static_name_);
      break;
    }
    case packet_type::zone_param_double: {
      auto p = reinterpret_cast<const packet<packet_type::zone_param_double>*>(packet_begin);
      check_static_string(p->static_name_);
      break;
    }
    case packet_type::zone_param_string: {
      auto p = reinterpret_cast<const packet<packet_type::zone_param_string>*>(packet_begin);
      check_static_string(p->static_name_);
      break;
    }
    case packet_type::zone_category: {
      auto p = reinterpret_cast<const packet<packet_type::zone_category>*>(packet_begin);
      check_static_string(p->static_name_);
      break;
    }
    default:
      break;
    }
  }

  //! Check if the static string is already known, and if not, write it to the buffer.
  void check_static_string(uint64_t string_id) {
    auto it = static_strings_.find(string_id);
    if (it == static_strings_.end()) {
      static_strings_.insert(string_id);
      const char* str = reinterpret_cast<const char*>(string_id);
      auto p = buffer_.acquire_packet_dynamic<packet_type::static_string>(strlen(str));

      p->static_string_ = reinterpret_cast<uint64_t>(str);
      p->size_ = strlen(str);
      memcpy(to_uint8_ptr(p) + sizeof(*p), str, p->size_);
      commit(p);
    }
  }

  //! Check if the static location is already known, and if not, write it to the buffer.
  void check_location(uint64_t location_id) {
    auto it = static_locations_.find(location_id);
    if (it == static_locations_.end()) {
      static_locations_.insert(location_id);

      const location* loc = reinterpret_cast<const location*>(location_id);
      check_static_string(reinterpret_cast<uint64_t>(loc->name));
      check_static_string(reinterpret_cast<uint64_t>(loc->function));
      check_static_string(reinterpret_cast<uint64_t>(loc->file));

      auto p = buffer_.acquire_packet_static<packet_type::location>();
      p->location_id_ = reinterpret_cast<uint64_t>(loc);
      p->static_name_ = reinterpret_cast<uint64_t>(loc->name);
      p->static_function_ = reinterpret_cast<uint64_t>(loc->function);
      p->static_file_ = reinterpret_cast<uint64_t>(loc->file);
      p->line_ = loc->line;
      commit(p);
    }
  }

  FILE* open_capture() {
    FILE* f = fopen("capture.bin-trace", "wb");
    if (!f) {
      printf("Failed to open output capture file: capture.bin-trace\n");
      std::terminate();
    }
    return f;
  }
  void write_buffer_to_file(FILE* f, const void* data, size_t size) {
    while (size > 0) {
      auto to_write = std::min(size, size_t(1024*1024));
      auto written = fwrite(data, 1, to_write, f);
      if (written != to_write) {
        printf("Failed to write to output capture file: capture.bin-trace\n");
        std::terminate();
      }
      size -= written;
      data = static_cast<const char*>(data) + written;
    }
    auto written = fwrite(data, 1, size, f);
    if (written != size) {
      printf("Failed to write to output capture file: capture.bin-trace\n");
      std::terminate();
    }
  }
};

} // namespace detail

thread_id get_current_thread() {
  auto tid = std::this_thread::get_id();
  static_assert(sizeof(tid) <= sizeof(thread_id), "std::thread::id doesn't fit in thread_id");
  return *reinterpret_cast<thread_id*>(&tid);
}
timestamp_t now() {
  auto t = std::chrono::steady_clock::now().time_since_epoch();
  auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(t).count();
  return static_cast<timestamp_t>(now_ns);
}

void define_stack(const void* begin, const void* end, const char* name) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_dynamic<detail::packet_type::stack>(strlen(name));
  p->begin_ = reinterpret_cast<uint64_t>(begin);
  p->end_ = reinterpret_cast<uint64_t>(end);
  p->name_size_ = strlen(name);
  memcpy(to_uint8_ptr(p) + sizeof(*p), name, p->name_size_);
  commit(p);
}
void set_thread_name(thread_id tid, const char* name) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_dynamic<detail::packet_type::thread_name>(strlen(name));
  p->tid_ = tid;
  p->name_size_ = strlen(name);
  memcpy(to_uint8_ptr(p) + sizeof(*p), name, p->name_size_);
  commit(p);
}

void emit_zone_start(const void* stack_ptr, thread_id tid, timestamp_t timestamp,
                     const location* static_location) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_start>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  p->location_id_ = reinterpret_cast<uint64_t>(static_location);
  commit(p);
}
void emit_zone_end(const void* stack_ptr, timestamp_t timestamp) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_end>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->timestamp_ = timestamp;
  commit(p);
}
void emit_zone_dynamic_name(const void* stack_ptr, const char* dyn_name) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_dynamic<detail::packet_type::zone_dynamic_name>(strlen(dyn_name));
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->name_size_ = strlen(dyn_name);
  memcpy(to_uint8_ptr(p) + sizeof(*p), dyn_name, p->name_size_);
  commit(p);
}
void emit_zone_param(const void* stack_ptr, const char* static_name, bool value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_param_bool>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_ = value;
  commit(p);
}
void emit_zone_param(const void* stack_ptr, const char* static_name, int64_t value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_param_int>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_ = value;
  commit(p);
}
void emit_zone_param(const void* stack_ptr, const char* static_name, uint64_t value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_param_uint>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_ = value;
  commit(p);
}
void emit_zone_param(const void* stack_ptr, const char* static_name, double value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_param_double>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_ = value;
  commit(p);
}
void emit_zone_param(const void* stack_ptr, const char* static_name, const char* dyn_value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_dynamic<detail::packet_type::zone_param_string>(strlen(dyn_value));
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_size_ = strlen(dyn_value);
  memcpy(to_uint8_ptr(p) + sizeof(*p), dyn_value, p->value_size_);
  commit(p);
}
void emit_zone_flow(const void* stack_ptr, uint64_t flow_id) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_flow>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->flow_id_ = flow_id;
  commit(p);
}
void emit_zone_flow_terminate(const void* stack_ptr, uint64_t flow_id) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_flow_terminate>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->flow_id_ = flow_id;
  commit(p);
}
void emit_zone_category(const void* stack_ptr, const char* static_name) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_category>();
  p->stack_ptr_ = reinterpret_cast<uint64_t>(stack_ptr);
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  commit(p);
}

void define_counter_track(uint64_t tid, const char* name) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_dynamic<detail::packet_type::counter_track>(strlen(name));
  p->tid_ = tid;
  p->name_size_ = strlen(name);
  memcpy(to_uint8_ptr(p) + sizeof(*p), name, p->name_size_);
  commit(p);
}
void emit_counter_value(uint64_t tid, timestamp_t timestamp, int64_t value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::counter_value_int>();
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  p->value_ = value;
  commit(p);
}
void emit_counter_value(uint64_t tid, timestamp_t timestamp, double value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::counter_value_double>();
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  p->value_ = value;
  commit(p);
}

} // namespace profiling_lite
