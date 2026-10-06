#include "shape.h"
double triangle_area(struct vec a, struct vec b, struct vec c)
{
  struct vec ab = { b.x - a.x, b.y - a.y };
  struct vec ac = { c.x - a.x, c.y - a.y };
  double cross = vec_cross(ab, ac);
  return (cross < 0 ? -cross : cross) / 2;
}
