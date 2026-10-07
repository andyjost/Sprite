#include <stdio.h>
#include "shape.h"
#include "vec.h"
int main(void)
{
  struct vec a = { 0, 0 }, b = { 4, 0 }, c = { 0, 3 };
  report("c", c);
  printf("area = %g\n", triangle_area(a, b, c));
#ifdef WITH_PLOT
  plot(a, b, c);
#endif
  return 0;
}
