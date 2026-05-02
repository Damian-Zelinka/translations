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

//  ERROR 1: invalid symbol (@)
int bad@var = 10;

//  ERROR 2: malformed number (two dots)
int wrongNumber = 12..5;

//  ERROR 3: unclosed string literal
cout << "This string is not closed << endl;

if (result > 10) {
cout << "Result is large: " << result << endl;
} else {
cout << "Result is small: " << result << endl;
}

int direct = multiply(x, y);
cout << "Direct multiply: " << direct << endl;

return 0;
}