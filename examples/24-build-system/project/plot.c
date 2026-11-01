#include <stdio.h>
#include "shape.h"
void plot(struct vec a, struct vec b, struct vec c)
{
  printf("plot: (%g,%g) (%g,%g) (%g,%g)\n", a.x, a.y, b.x, b.y, c.x, c.y);
}
