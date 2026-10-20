#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
  // A controlled fixture defect: native corpus injection makes it reproducible.
  constexpr char trigger[] = "NDDev controlled ClusterFuzzLite negative acceptance seed";
  if (size == sizeof(trigger) - 1 && std::memcmp(data, trigger, size) == 0) {
    std::abort();
  }
  return 0;
}
