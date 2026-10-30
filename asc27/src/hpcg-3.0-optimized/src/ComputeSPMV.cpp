#include "ComputeSPMV.hpp"
#include "ComputeSPMV_ref.hpp"
#include "OptimizedData.hpp"
#ifndef HPCG_NO_MPI
#include "ExchangeHalo.hpp"
#endif

static bool MatrixDiagonalsMatch(const SparseMatrix &A, HPCGOptimizedMatrix *d) {
  for (local_int_t i = 0; i < d->nrow; ++i)
    if (A.matrixDiagonal[i][0] != d->diagValues[i]) return false;
  return true;
}

int ComputeSPMV(const SparseMatrix &A, Vector &x, Vector &y) {
  HPCGOptimizedMatrix *d = GetOptimizedMatrix(A);
  if (d == 0) {
    A.isSpmvOptimized = false;
    return ComputeSPMV_ref(A, x, y);
  }
  if (!d->fastPath) {
    if (!MatrixDiagonalsMatch(A, d)) {
      A.isSpmvOptimized = false;
      return ComputeSPMV_ref(A, x, y);
    }
    d->fastPath = true;
  }
#ifndef HPCG_NO_MPI
  ExchangeHalo(A, x);
#endif
  const double *xv = x.values;
  double *yv = y.values;
  for (local_int_t i = 0; i < d->nrow; ++i) {
    double sum = 0.0;
    for (local_int_t k = d->rowptr[i]; k < d->rowptr[i + 1]; ++k)
      sum += d->values[k] * xv[d->col[k]];
    yv[i] = sum;
  }
  A.isSpmvOptimized = true;
  return 0;
}