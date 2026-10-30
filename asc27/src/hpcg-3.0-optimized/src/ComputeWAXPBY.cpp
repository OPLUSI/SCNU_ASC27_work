#include "ComputeWAXPBY.hpp"

int ComputeWAXPBY(const local_int_t n, const double alpha, const Vector &x,
                  const double beta, const Vector &y, Vector &w,
                  bool &isOptimized) {
  const double *xv = x.values;
  const double *yv = y.values;
  double *wv = w.values;
  if (alpha == 1.0) {
    for (local_int_t i = 0; i < n; ++i) wv[i] = xv[i] + beta * yv[i];
  } else if (beta == 1.0) {
    for (local_int_t i = 0; i < n; ++i) wv[i] = alpha * xv[i] + yv[i];
  } else {
    for (local_int_t i = 0; i < n; ++i) wv[i] = alpha * xv[i] + beta * yv[i];
  }
  isOptimized = true;
  return 0;
}