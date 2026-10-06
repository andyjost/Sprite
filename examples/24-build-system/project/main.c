#include <stdio.h>
#include "shape.h"
void report(const char *label, struct vec v);
int main(void)
{
  struct vec a = { 0, 0 }, b = { 4, 0 }, c = { 0, 3 };
  report("c", c);
  printf("area = %g\n", triangle_area(a, b, c));
  return 0;
}
