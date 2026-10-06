#include <stdio.h>
#include "vec.h"
void report(const char *label, struct vec v)
{
  printf("%s = (%g, %g)\n", label, v.x, v.y);
}
