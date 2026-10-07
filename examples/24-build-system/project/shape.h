#ifndef SHAPE_H
#define SHAPE_H
#include "vec.h"
double triangle_area(struct vec a, struct vec b, struct vec c);
#ifdef WITH_PLOT
void plot(struct vec a, struct vec b, struct vec c);
#endif
#endif
