#ifndef PID_MODULE_H
#define PID_MODULE_H

// Wrapper header to present a single PIDModule type while reusing the
// existing asymmetric implementation. This keeps the rest of the codebase
// aligned with the classic naming without duplicating functionality.
#include "pid_module_asymmetric.h"

using PIDModule = AsymmetricPIDModule;

#endif // PID_MODULE_H
