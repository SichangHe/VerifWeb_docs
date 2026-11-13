# CVE mutation evidence
(authored by agents unless marked 🧑)

The unchanged existing Z3 model rejects the CVE-2020-6418-shaped buggy variant and accepts its fixed variant over all sequences of up to four modeled operations: 1/1 model mutant killed, 100%. This is not an upstream executable mutation test. No C++ was compiled or translated automatically, and 396 violating sequences are not 396 mutants.

## V8: exact fix provenance and model result

Project Zero's Samuel Groß and Sergei Glazunov identify “Patch CL:” as https://chromium.googlesource.com/v8/v8.git/+/fb0a60e15695466621cf65932f9152935d859447 in their [CVE-2020-6418 analysis](https://googleprojectzero.github.io/0days-in-the-wild/0day-RCAs/2020/CVE-2020-6418.html), saved in `pz.html`.

Georg Neis's [upstream patch](https://github.com/v8/v8/commit/fb0a60e15695466621cf65932f9152935d859447), saved in `v8-fix.patch`, says:

> JSCreate can have side effects (by looking up the prototype on an
> object), so once we walk past that the analysis result must be marked
> as "unreliable".

Its sole production-code addition is:

```cpp
result = kUnreliableReceiverMaps;  // JSCreate can have side-effect.
```

The existing `out/vlm2_jit/t1_side_effects/model.py` implements this difference as `if fixed: reliable = False` for `JSCreate_other`. Its independent state-transition relation allows that operation to change the receiver map. Therefore its contract asks whether a reliable inferred map can be false in the final heap, and this actual patch difference is represented faithfully for that branch.

Reproduction from workspace root:

```sh
timeout 60s out/vlm2_jit/t2_typer/venv/bin/python out/vlm2_jit/t1_side_effects/model.py 4
```

Saved output (`model-run-length4.txt`):

```text
BUGGY (8.0, no JSCreate marking): maxlen=4 violations=396
   ('CheckMaps_recv', 'JSCreate_other')
   ('StoreMap_recv_const', 'JSCreate_other')
   ('CheckMaps_recv', 'CheckMaps_recv', 'JSCreate_other')
   ('CheckMaps_recv', 'CheckMaps_other', 'JSCreate_other')
   ('CheckMaps_recv', 'StoreMap_recv_const', 'JSCreate_other')
FIXED (main): maxlen=4 violations=0
```

Nine modeled operations give 7,380 sequences of lengths 1–4 per variant. Length 3 independently gave 34 buggy violations and zero fixed violations (`model-run.txt`). The script exits successfully even when violations exist: its output must be interpreted; process success is not acceptance. These checks do not establish unbounded soundness or correctness of the model's omitted V8 operations. No weak spec is demonstrated by this pair; source-to-model correspondence remains an assumption beyond the inspected branch.

## Wasmtime: exact fix provenance for the separately run Verus pair

The [Bytecode Alliance advisory](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-ff4p-7xrq-q5r8), fetched through GitHub's advisory API and saved in `wasmtime-advisory.json`, links “Commit to fix this issue on Wasmtime's `main` branch” to https://github.com/bytecodealliance/wasmtime/commit/63fb30e4b4415455d47b3da5a19d79c12f4f2d1f.

Alex Crichton's patch (`wasmtime-fix.patch`) states:

> This commit removes two incorrect rules as part of the x64 backend's
> computation of addressing modes. These two rules folded a zero-extended
> 32-bit computation into the address mode operand, but this isn't correct
> as the 32-bit computation should be truncated to 32-bits but when folded
> into the address mode computation it happens with 64-bit operands,
> meaning truncation doesn't happen.

The actual change deletes two `amode_add` rules from `cranelift/codegen/src/isa/x64/inst.isle`: the `uextend(ishl(...))` rule and a specialized rule with an `iadd` input. The existing `out/vlm2_iso/sandbox_verus/wasm_mem.rs` models the arithmetic distinction as `(a*k)%2^32 + off` versus `a*k + off`. It does not parse either deleted rule or prove that the backend chooses those expressions. Count this as one CVE-shaped arithmetic model pair, not two tested upstream rule mutants. The parent agent runs that Verus pair; no additional kill count is claimed here.

The model's `RESERVED` is 10 GiB, while the advisory states “Wasmtime's default sandbox settings provide up to 6G of protection from the base of linear memory to guarantee that any memory access in that range will be semantically correct.” Thus its reservation bound is an explicit model choice rather than a checked reconstruction of the affected Wasmtime configuration. The equality-to-Wasm-semantics contract can still reject missing truncation independently of that choice.

## Scope and recommendation

Available memory was 113 GiB before these lightweight checks; no builds were run. System Python lacked Z3, so the already-installed project virtual environment was used. These two linked upstream patches make model mutation results more defensible, but actual source-level kill rate remains unmeasured. Worth pursuing a small corpus only with explicit source-to-model mappings and separate counts for source mutants and abstract mutants; otherwise a high score mostly confirms that bug-aware models encode the known bug.
