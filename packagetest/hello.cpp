// RUN: %clangxx --target=armv6m-none-eabi -mfloat-abi=soft -march=armv6m -mfpu=none -lcrt0-semihost -lsemihost -fno-exceptions -fno-rtti -T %S/Inputs/microbit.ld %s -o %t.out
// RUN: qemu-system-arm -M microbit -semihosting -nographic -device loader,file=%t.out 2>&1 | FileCheck %s

// Include as many C++17 headers as possible.
// Unsupported headers are commented out.
#include <algorithm>
#include <any>
#include <array>
#include <atomic>
#include <bitset>
#include <chrono>
#include <codecvt>
#include <complex>
#include <condition_variable>
#include <deque>
#include <exception>
#include <execution>
//#include <filesystem>
#include <forward_list>
#include <fstream>
#include <functional>
//#include <future>
#include <initializer_list>
#include <iomanip>
#include <ios>
#include <iosfwd>
#include <iostream>
#include <istream>
#include <iterator>
#include <limits>
#include <list>
#include <locale>
#include <map>
#include <memory>
#include <memory_resource>
//#include <mutex>
#include <new>
#include <numeric>
#include <optional>
#include <ostream>
#include <queue>
#include <random>
#include <ratio>
#include <regex>
#include <scoped_allocator>
#include <set>
//#include <shared_mutex>
#include <sstream>
#include <stack>
#include <stdexcept>
#include <streambuf>
#include <string>
#include <string_view>
#include <strstream>
#include <system_error>
//#include <thread>
#include <tuple>
#include <type_traits>
#include <typeindex>
#include <typeinfo>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <valarray>
#include <variant>
#include <vector>

#include <cassert>
#include <cinttypes>
#include <csignal>
#include <cstdio>
//#include <cwchar>
#include <ccomplex>
#include <ciso646>
//#include <cstdalign> // removed in C++20
#include <cstdlib>
//#include <cwctype>
#include <cctype>
#include <climits>
#include <cstdarg>
#include <cstring>
#include <cerrno>
#include <clocale>
#include <cstdbool>
#include <ctgmath>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <ctime>
#include <cfloat>
#include <csetjmp>
#include <cstdint>
#include <cuchar>

int main(void) {
    std::string str = "Hello World!";
    std::cout << str << std::endl; // CHECK: Hello World!
    return 0;
}
