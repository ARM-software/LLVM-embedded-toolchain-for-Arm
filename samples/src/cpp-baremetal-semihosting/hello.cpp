#include <vector>
#include <iostream>

int main(void) {
  std::vector<int> v = {1, 2, 3};
  v.push_back(4);
  v.insert(v.end(), 5);

  for (int elem: v) {
    std::cout << elem << " ";
  }
  std::cout << std::endl;

  return 0;
}
