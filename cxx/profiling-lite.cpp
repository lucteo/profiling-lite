#include "profiling-lite.hpp"

#include <cassert>
#include <chrono>
#include <mutex>
#include <thread>
#include <unordered_set>

namespace profiling_lite {

namespace detail {

uint8_t* to_uint8_ptr(void* p) { return reinterpret_cast<uint8_t*>(p); }
const uint8_t* to_uint8_ptr(const void* p) { return reinterpret_cast<const uint8_t*>(p); }

enum class packet_type : uint8_t {
  free = 0,

  init = 16,
  static_string,
  location,

  thread_name,
  counter_track,

  zone_start,
  zone_end,
  zone_dynamic_name,
  zone_param_bool,
  zone_param_int,
  zone_param_uint,
  zone_param_double,
  zone_param_string,
  zone_flow,
  zone_category,

  counter_value_int,
  counter_value_double,

  thread_switch_start,
  thread_switch_end,

  spawn,
  spawn_continue,
  spawn_ending,
  spawn_done,
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

template <> struct packet<packet_type::thread_name> : packet_base {
  thread_id tid_;
  uint16_t name_size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return name_size_; }
};

template <> struct packet<packet_type::counter_track> : packet_base {
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
  thread_id tid_;
  timestamp_t timestamp_;
  uint64_t location_id_;
};
template <> struct packet<packet_type::zone_end> : static_packet_base {
  thread_id tid_;
  timestamp_t timestamp_;
};
template <> struct packet<packet_type::zone_dynamic_name> : packet_base {
  thread_id tid_;
  uint16_t name_size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return name_size_; }
};
template <> struct packet<packet_type::zone_param_bool> : static_packet_base {
  thread_id tid_;
  uint64_t static_name_;
  uint8_t value_;
};
template <> struct packet<packet_type::zone_param_int> : static_packet_base {
  thread_id tid_;
  uint64_t static_name_;
  int64_t value_;
};
template <> struct packet<packet_type::zone_param_uint> : static_packet_base {
  thread_id tid_;
  uint64_t static_name_;
  uint64_t value_;
};
template <> struct packet<packet_type::zone_param_double> : static_packet_base {
  thread_id tid_;
  uint64_t static_name_;
  double value_;
};
template <> struct packet<packet_type::zone_param_string> : packet_base {
  thread_id tid_;
  uint64_t static_name_;
  uint16_t value_size_;

  static constexpr bool has_dynamic_size = true;
  size_t extra_size() const { return value_size_; }
};
template <> struct packet<packet_type::zone_flow> : static_packet_base {
  thread_id tid_;
  uint64_t flow_id_;
};
template <> struct packet<packet_type::zone_category> : static_packet_base {
  thread_id tid_;
  uint64_t static_name_;
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

template <> struct packet<packet_type::thread_switch_start> : static_packet_base {
  thread_id tid_;
  uint64_t switch_id_;
};
template <> struct packet<packet_type::thread_switch_end> : static_packet_base {
  thread_id tid_;
  timestamp_t timestamp_;
  uint64_t switch_id_;
};

template <> struct packet<packet_type::spawn> : static_packet_base {
  uint64_t spawn_id_;
  thread_id tid_;
  timestamp_t timestamp_;
  uint8_t num_threads;
};
template <> struct packet<packet_type::spawn_continue> : static_packet_base {
  uint64_t spawn_id_;
  thread_id tid_;
  timestamp_t timestamp_;
};
template <> struct packet<packet_type::spawn_ending> : static_packet_base {
  uint64_t spawn_id_;
  thread_id tid_;
  timestamp_t timestamp_;
};
template <> struct packet<packet_type::spawn_done> : static_packet_base {
  uint64_t spawn_id_;
  thread_id tid_;
  timestamp_t timestamp_;
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
  case packet_type::thread_name:            return typed_packet_size<packet_type::thread_name>(pckt);
  case packet_type::counter_track:          return typed_packet_size<packet_type::counter_track>(pckt);
  case packet_type::zone_start:             return typed_packet_size<packet_type::zone_start>(pckt);
  case packet_type::zone_end:               return typed_packet_size<packet_type::zone_end>(pckt);
  case packet_type::zone_dynamic_name:      return typed_packet_size<packet_type::zone_dynamic_name>(pckt);
  case packet_type::zone_param_bool:        return typed_packet_size<packet_type::zone_param_bool>(pckt);
  case packet_type::zone_param_int:         return typed_packet_size<packet_type::zone_param_int>(pckt);
  case packet_type::zone_param_uint:        return typed_packet_size<packet_type::zone_param_uint>(pckt);
  case packet_type::zone_param_double:      return typed_packet_size<packet_type::zone_param_double>(pckt);
  case packet_type::zone_param_string:      return typed_packet_size<packet_type::zone_param_string>(pckt);
  case packet_type::zone_flow:              return typed_packet_size<packet_type::zone_flow>(pckt);
  case packet_type::zone_category:          return typed_packet_size<packet_type::zone_category>(pckt);
  case packet_type::counter_value_int:      return typed_packet_size<packet_type::counter_value_int>(pckt);
  case packet_type::counter_value_double:   return typed_packet_size<packet_type::counter_value_double>(pckt);
  case packet_type::thread_switch_start:    return typed_packet_size<packet_type::thread_switch_start>(pckt);
  case packet_type::thread_switch_end:      return typed_packet_size<packet_type::thread_switch_end>(pckt);
  case packet_type::spawn:                  return typed_packet_size<packet_type::spawn>(pckt);
  case packet_type::spawn_continue:         return typed_packet_size<packet_type::spawn_continue>(pckt);
  case packet_type::spawn_ending:           return typed_packet_size<packet_type::spawn_ending>(pckt);
  case packet_type::spawn_done:             return typed_packet_size<packet_type::spawn_done>(pckt);
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
      : size_(size), data_(new uint8_t[size]), packet_limit_(data_ + size - 1024) {
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

    writer_thread_ = std::thread(&Profiler::thread_func, this);
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
timestamp_t get_time() {
  auto t = std::chrono::steady_clock::now().time_since_epoch();
  auto now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(t).count();
  return static_cast<timestamp_t>(now_ns);
}

void set_thread_name(thread_id tid, const char* name) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_dynamic<detail::packet_type::thread_name>(strlen(name));
  p->tid_ = tid;
  p->name_size_ = strlen(name);
  memcpy(to_uint8_ptr(p) + sizeof(*p), name, p->name_size_);
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

void emit_zone_start(thread_id tid, timestamp_t timestamp, const location* static_location) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_start>();
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  p->location_id_ = reinterpret_cast<uint64_t>(static_location);
  commit(p);
}
void emit_zone_end(thread_id tid, timestamp_t timestamp) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_end>();
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  commit(p);
}
void emit_zone_dynamic_name(thread_id tid, const char* dyn_name) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_dynamic<detail::packet_type::zone_dynamic_name>(strlen(dyn_name));
  p->tid_ = tid;
  p->name_size_ = strlen(dyn_name);
  memcpy(to_uint8_ptr(p) + sizeof(*p), dyn_name, p->name_size_);
  commit(p);
}
void emit_zone_param(thread_id tid, const char* static_name, bool value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_param_bool>();
  p->tid_ = tid;
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_ = value;
  commit(p);
}
void emit_zone_param(thread_id tid, const char* static_name, int64_t value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_param_int>();
  p->tid_ = tid;
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_ = value;
  commit(p);
}
void emit_zone_param(thread_id tid, const char* static_name, uint64_t value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_param_uint>();
  p->tid_ = tid;
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_ = value;
  commit(p);
}
void emit_zone_param(thread_id tid, const char* static_name, double value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_param_double>();
  p->tid_ = tid;
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_ = value;
  commit(p);
}
void emit_zone_param(thread_id tid, const char* static_name, const char* dyn_value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_dynamic<detail::packet_type::zone_param_string>(strlen(dyn_value));
  p->tid_ = tid;
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  p->value_size_ = strlen(dyn_value);
  memcpy(to_uint8_ptr(p) + sizeof(*p), dyn_value, p->value_size_);
  commit(p);
}
void emit_zone_flow(thread_id tid, uint64_t flow_id) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_flow>();
  p->tid_ = tid;
  p->flow_id_ = flow_id;
  commit(p);
}
void emit_zone_category(thread_id tid, const char* static_name) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::zone_category>();
  p->tid_ = tid;
  p->static_name_ = reinterpret_cast<uint64_t>(static_name);
  commit(p);
}

void emit_counter_value(thread_id tid, timestamp_t timestamp, int64_t value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::counter_value_int>();
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  p->value_ = value;
  commit(p);
}
void emit_counter_value(thread_id tid, timestamp_t timestamp, double value) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::counter_value_double>();
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  p->value_ = value;
  commit(p);
}

void emit_thread_switch_start(thread_id tid, uint64_t switch_id) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::thread_switch_start>();
  p->tid_ = tid;
  p->switch_id_ = switch_id;
  commit(p);
}
void emit_thread_switch_end(thread_id tid, timestamp_t timestamp, uint64_t switch_id) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::thread_switch_end>();
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  p->switch_id_ = switch_id;
  commit(p);
}

void emit_spawn(uint64_t spawn_id, thread_id tid, timestamp_t timestamp, uint8_t num_threads) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::spawn>();
  p->spawn_id_ = spawn_id;
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  p->num_threads = num_threads;
  commit(p);
}
void emit_spawn_continue(uint64_t spawn_id, thread_id tid, timestamp_t timestamp) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::spawn_continue>();
  p->spawn_id_ = spawn_id;
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  commit(p);
}
void emit_spawn_ending(uint64_t spawn_id, thread_id tid, timestamp_t timestamp) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::spawn_ending>();
  p->spawn_id_ = spawn_id;
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  commit(p);
}
void emit_spawn_done(uint64_t spawn_id, thread_id tid, timestamp_t timestamp) {
  auto& buffer = detail::Profiler::instance().buffer();
  auto p = buffer.acquire_packet_static<detail::packet_type::spawn_done>();
  p->spawn_id_ = spawn_id;
  p->tid_ = tid;
  p->timestamp_ = timestamp;
  commit(p);
}

} // namespace profiling_lite
