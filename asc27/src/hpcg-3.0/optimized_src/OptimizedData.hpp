#ifndef HPCG_OPTIMIZED_DATA_HPP
#define HPCG_OPTIMIZED_DATA_HPP

#include "SparseMatrix.hpp"

struct HPCGOptimizedMatrix {
  local_int_t nrow;
  local_int_t nnz;
  local_int_t *rowptr;
  local_int_t *col;
  double *values;
  local_int_t *diag;
  double *diagValues;
  bool fastPath;
};

inline HPCGOptimizedMatrix *GetOptimizedMatrix(const SparseMatrix &A) {
  return static_cast<HPCGOptimizedMatrix *>(A.optimizationData);
}

#endif