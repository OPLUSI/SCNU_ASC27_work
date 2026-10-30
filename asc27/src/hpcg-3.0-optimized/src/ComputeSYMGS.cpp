#include "ComputeSYMGS.hpp"
#include "ComputeSYMGS_ref.hpp"
#include "OptimizedData.hpp"
#ifndef HPCG_NO_MPI
#include "ExchangeHalo.hpp"
#endif

static bool MatrixDiagonalsMatch(const SparseMatrix &A, HPCGOptimizedMatrix *d) {
  for (local_int_t i = 0; i < d->nrow; ++i)
    if (A.matrixDiagonal[i][0] != d->diagValues[i]) return false;
  return true;
}

int ComputeSYMGS(const SparseMatrix &A, const Vector &r, Vector &x) {
  HPCGOptimizedMatrix *d = GetOptimizedMatrix(A);
  if (d == 0) return ComputeSYMGS_ref(A, r, x);
  if (!d->fastPath) {
    if (!MatrixDiagonalsMatch(A, d)) return ComputeSYMGS_ref(A, r, x);
    d->fastPath = true;
  }
#ifndef HPCG_NO_MPI
  ExchangeHalo(A, x);
#endif
  const double *rv = r.values;
  double *xv = x.values;
  for (local_int_t i = 0; i < d->nrow; ++i) {
    double sum = rv[i];
    for (local_int_t k = d->rowptr[i]; k < d->rowptr[i + 1]; ++k)
      sum -= d->values[k] * xv[d->col[k]];
    const double diag = d->diagValues[i];
    sum += xv[i] * diag;
    xv[i] = sum / diag;
  }
  for (local_int_t i = d->nrow; i-- > 0;) {
    double sum = rv[i];
    for (local_int_t k = d->rowptr[i]; k < d->rowptr[i + 1]; ++k)
      sum -= d->values[k] * xv[d->col[k]];
    const double diag = d->diagValues[i];
    sum += xv[i] * diag;
    xv[i] = sum / diag;
  }
  return 0;
}