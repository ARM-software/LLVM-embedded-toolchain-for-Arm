#include <iostream>
#include <limits>

int main(void) {
  int max_int = std::numeric_limits<int>::max();
  [[maybe_unused]] int invoke_ubsan = max_int + max_int;

  std::cout << "C++ UBSan sample" << std::endl;

  return 0;
}
