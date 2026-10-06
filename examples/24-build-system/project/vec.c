#include "vec.h"
double vec_cross(struct vec a, struct vec b) { return a.x * b.y - a.y * b.x; }
