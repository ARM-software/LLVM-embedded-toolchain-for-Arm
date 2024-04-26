#include <iostream>

int main(void) {
  try {
    throw "error";
  } catch(...) {
    std::cout << "Exception caught." << std::endl;
    return 0;
  }
  std::cout << "Exception skipped." << std::endl;
  return 1;
}
