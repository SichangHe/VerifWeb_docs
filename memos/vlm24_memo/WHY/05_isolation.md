# Isolation: tabs or tenants sharing one process
(authored by agents unless marked 🧑)

Who is hurt. Browsers and edge platforms pay memory for one process per tab or customer. Sharing a process is cheaper but trusts the JS engine to keep tenants apart. When it fails, one tenant reads another's data: the vm2 sandbox escape (CVE-2023-29017).

Why testing does not fix it. Escapes come from rare engine bugs. Cloudflare Workers already share processes but state "we assume that the attacker does not have the ability to execute arbitrary machine code".

Why a proof helps. Rather than verifying the whole engine (2M+ lines; no verified engine exists), check a few boundary rules: each tenant's objects stay separate, and JIT output (machine code the engine generates while running) touches only its tenant's memory.

Contribution (opinion). A checker for every piece of JIT output, with many tenants. Closest work checks fixed code (VeriWasm, LFI) or verifies JIT parts once (Icarus).

Evidence. We proved separation on a two-tenant heap model only. Spectre stays out of any such proof.

Opinion. Weakest fit: specialist machine-code proofs, and a strong group (RLBox, Icarus) owns the area.

Questions
- must the JS engine be verified for process sharing to be acceptable?
- is "memory savings" a strong enough why?
