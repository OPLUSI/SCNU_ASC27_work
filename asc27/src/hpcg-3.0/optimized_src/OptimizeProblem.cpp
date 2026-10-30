#include "OptimizeProblem.hpp"
#include "OptimizedData.hpp"

static void BuildOptimizedMatrix(SparseMatrix &A) {
  HPCGOptimizedMatrix *d = new HPCGOptimizedMatrix;
  d->nrow = A.localNumberOfRows;
  d->nnz = A.localNumberOfNonzeros;
  d->rowptr = new local_int_t[d->nrow + 1];
  d->col = new local_int_t[d->nnz];
  d->values = new double[d->nnz];
  d->diag = new local_int_t[d->nrow];
  d->diagValues = new double[d->nrow];
  d->fastPath = false;

  local_int_t offset = 0;
  d->rowptr[0] = 0;
  for (local_int_t i = 0; i < d->nrow; ++i) {
    const int nnz = static_cast<int>(A.nonzerosInRow[i]);
    const local_int_t *cols = A.mtxIndL[i];
    const double *vals = A.matrixValues[i];
    const double *diagptr = A.matrixDiagonal[i];
    d->diag[i] = offset + static_cast<local_int_t>(diagptr - vals);
    d->diagValues[i] = *diagptr;
    for (int j = 0; j < nnz; ++j) {
      d->col[offset + j] = cols[j];
      d->values[offset + j] = vals[j];
    }
    offset += nnz;
    d->rowptr[i + 1] = offset;
  }
  A.optimizationData = d;

  if (A.Ac != 0) BuildOptimizedMatrix(*A.Ac);
}

int OptimizeProblem(SparseMatrix &A, CGData &, Vector &, Vector &, Vector &) {
  BuildOptimizedMatrix(A);
  return 0;
}

double OptimizeProblemMemoryUse(const SparseMatrix &A) {
  double bytes = 0.0;
  const HPCGOptimizedMatrix *d = GetOptimizedMatrix(A);
  if (d != 0) {
    bytes += (d->nrow + 1) * sizeof(local_int_t);
    bytes += d->nnz * (sizeof(local_int_t) + sizeof(double));
    bytes += d->nrow * (sizeof(local_int_t) + sizeof(double));
  }
  if (A.Ac != 0) bytes += OptimizeProblemMemoryUse(*A.Ac);
  return bytes;
}