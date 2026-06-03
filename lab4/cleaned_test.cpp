#include <iostream>
using namespace std;
int multiply(int a, int b) {
return a * b;
}
int main() {
int x = 3;
int y = 4;
int result = 0;
for (int i = 0; i < y; i++) {
result = result + x;
}
if (result > 10) {
cout << "Result is large: " << result << endl;
} else {
cout << "Result is small: " << result << endl;
}
int direct = multiply(x, y);
cout << "Direct multiply: " << direct << endl;
return 0;
}