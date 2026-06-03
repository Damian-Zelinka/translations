#include <iostream>
using namespace std;

// function example
int multiply(int a, int b) {
    return a * b;  // multiplication
}

int main() {
    int x = 3;
    int y = 4;
    int result = 0;

    // for loop
    for (int i = 0; i < y; i++) {
        result = result + x;
    }

    // if-else example
    if (result > 10) {
        cout << "Result is large: " << result << endl;
    } else {
        cout << "Result is small: " << result << endl;
    }

    // function call
    int direct = multiply(x, y);
    cout << "Direct multiply: " << direct << endl;

    return 0;
}

/* multi-line
   comment */