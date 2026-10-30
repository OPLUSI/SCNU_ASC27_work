#include "ComputeMG.hpp"
#include "ComputeSYMGS.hpp"
#include "ComputeSPMV.hpp"
#include "ComputeRestriction_ref.hpp"
#include "ComputeProlongation_ref.hpp"

int ComputeMG(const SparseMatrix &A, const Vector &r, Vector &x) {
  ZeroVector(x);
  int ierr = 0;
  if (A.mgData != 0) {
    for (int i = 0; i < A.mgData->numberOfPresmootherSteps; ++i)
      ierr += ComputeSYMGS(A, r, x);
    if (ierr) return ierr;
    ierr = ComputeSPMV(A, x, *A.mgData->Axf);
    if (ierr) return ierr;
    ierr = ComputeRestriction_ref(A, r);
    if (ierr) return ierr;
    ierr = ComputeMG(*A.Ac, *A.mgData->rc, *A.mgData->xc);
    if (ierr) return ierr;
    ierr = ComputeProlongation_ref(A, x);
    if (ierr) return ierr;
    for (int i = 0; i < A.mgData->numberOfPostsmootherSteps; ++i)
      ierr += ComputeSYMGS(A, r, x);
  } else {
    ierr = ComputeSYMGS(A, r, x);
  }
  A.isMgOptimized = true;
  return ierr;
}