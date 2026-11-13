# Snapshot JavaScript checker
(authored by agents unless marked 🧑)

contract
- conditional checks of a small sequential JavaScript subset
  - no uncaught exception
  - no read of the snapshot document's cookie property
  - each invocation of each while loop performs at most 8 body iterations
- snapshot describes ordinary JSON data with pristine built-in prototypes
  - no getters, proxies, mutation by outside code, browser callbacks, or custom prototypes
  - document and window are fixed objects
  - window is separate from the JavaScript global object; script var bindings do not change it
  - document.getElementById is a fixed pure lookup in document.ids, returning null when absent
  - this models an environment contract, not a captured browser DOM
- symbolic input descriptors denote finite sets of integer Number values
  - safe-integer endpoints, at most 256 values per field
  - exact binary64 encodings, including positive zero for integer input zero
  - ordinary JSON numbers preserve negative zero

execution
- Acorn parses source; validation hoists var and rejects unsupported syntax
- Z3 Float64 arithmetic uses round-to-nearest, ties-to-even
  - comparisons use IEEE equality/order, including NaN and signed zero
  - undefined converts to NaN in numeric operations
  - null and booleans have numeric conversions
- array numeric reads split by index; absent elements yield undefined and execution continues
- undeclared reads report ReferenceError; null/undefined property reads report TypeError
- getElementById returning null is not itself an exception
- while explores exits and reports paths needing a ninth iteration
  - behavior after a loop-bound violation is not explored
  - an alarm-free result establishes all three properties only under this contract
- unsupported executed operations and solver unknown/timeout return INCONCLUSIVE, exit 2
  - state-agnostic mode is rejected
  - inherited/missing ordinary-object properties, string coercion, nonnumeric equality, arbitrary calls, member writes, let/const, and builtin shadowing are rejected
  - parseInt supports only safe-integer Number arguments
    - decimal string conversion and parsing preserve value, except negative zero becomes positive zero
  - nonfinite source literals lost by the AST JSON transport are rejected
- this implementation has regression tests, not a machine-checked proof of its own correctness

reproduction
- `bash run.sh` from this directory runs original snapshots
- `python3 test_symx.py` runs Node comparisons and regression tests
- dependencies are the existing node_modules and pylib directories
- corrected observations and evidence: ../../cx_dynstate/REPORT.md
