#include <iostream>

class Base {
  public:
    virtual ~Base() {}
    virtual void print_type() {
      std::cout << "Base" << std::endl;
    }
};

class Good: public Base {
  public:
    void print_type() override {
      std::cout << "Good" << std::endl;
    }
};

class Bad { // not derived from Base
  public:
    virtual ~Bad() {}
    virtual void print_type() {
      std::cout << "Bad" << std::endl;
    }
};

int main(void) {
  Base* base_ptr = reinterpret_cast<Good*>(new Bad());
  base_ptr->print_type();

  std::cout << "C++ CFI sample" << std::endl;

  return 0;
}
