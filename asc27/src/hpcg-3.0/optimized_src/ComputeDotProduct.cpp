#include "ComputeDotProduct.hpp"
#ifndef HPCG_NO_MPI
#include <mpi.h>
#include "mytimer.hpp"
#endif

int ComputeDotProduct(const local_int_t n, const Vector &x, const Vector &y,
                      double &result, double &time_allreduce,
                      bool &isOptimized) {
  const double *xv = x.values;
  const double *yv = y.values;
  double local = 0.0;
  if (xv == yv) {
    for (local_int_t i = 0; i < n; ++i) local += xv[i] * xv[i];
  } else {
    for (local_int_t i = 0; i < n; ++i) local += xv[i] * yv[i];
  }
#ifndef HPCG_NO_MPI
  const double t0 = mytimer();
  MPI_Allreduce(&local, &result, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);
  time_allreduce += mytimer() - t0;
#else
  result = local;
#endif
  isOptimized = true;
  return 0;
}