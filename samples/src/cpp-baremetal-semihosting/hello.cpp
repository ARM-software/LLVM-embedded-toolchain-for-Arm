#include <vector>
#include <cstdio>

int main(void) {
  std::vector<int> v = {1, 2, 3};
  v.push_back(4);
  v.insert(v.end(), 5);

  for (int elem: v) {
    printf("%d ", elem);
  }
  printf("\n");

  return 0;
}

extern "C" {
void SystemInit() {}
}
