# vlm42_config: validator/consumer disagreement in Pingora
(authored by agents unless marked 🧑)

Takeaway: Pingora's `ServerConf::validate` accepts a config that makes `ConnectorOptions::from_server_conf` panic. This is the Cloudflare shape: the validator accepts, the consumer calls `.unwrap()` on an `Err`. Verus proves the intended theorem false, and proves it true for a strengthened validator.

Chosen program (fact)
- Pingora, commit 3f87e92c982ee27c714506e16ae362776faea4aa (shallow clone in src/pingora, never built or run).
- Validator: `pingora-core/src/server/configuration/mod.rs:366` `ServerConf::validate`, called from `from_yaml` (line 352).
- Consumer: `pingora-core/src/connectors/mod.rs:124` `ConnectorOptions::from_server_conf`. It does `v4.parse().unwrap()` on each `client_bind_to_ipv4` string, and the same for ipv6 (lines 125-143). `HttpProxy::new` (`pingora-proxy/src/lib.rs:230`) calls it.
- Why this one (inference): validator and consumer are separate code paths, and the consumer has a plain `unwrap` on a value the validator never looks at. `validate` checks only `max_blocking_threads`, the two histogram fields, and the bucket maximum.
- Rejected: `threads == 0` is not validated, but it is caught later with an error rather than a panic (`runtime_group.rs:273`; `ShardedNotify::new` uses `.max(1)`). `upstream_keepalive_pool_size` is handled with `saturating_mul` and `.max(1)`. I read these only to the extent shown; I did not audit all of Pingora.

Theorem as intended (false)
For every ServerConf `c`, `validate(c)` is Ok implies `from_server_conf(c)` does not panic.

Result: counterexample (fact, by source reading and Verus)
- Input YAML: `client_bind_to_ipv4: ["x"]`, all other fields default. `validate` returns Ok. `"x".parse::<IpAddr>()` is Err, so `unwrap` panics.
- Verus (`verus/pingora_conf.rs`, 9 verified, 0 errors) proves:
  - `counterexample`: for any model conf with ipv4 = ["x"] and the optional fields None, `accepts(c)` holds and `all_ip` fails.
  - `from_server_conf` verifies with precondition `all_ip(ipv4) && all_ip(ipv6)`. This is exactly the no-panic condition, since each `unwrap` needs `is_some`.
  - `validate` in the model is proved equal to its spec `accepts`.
  - Fixed validator (add the parse check) gives the consumer's precondition. This lemma is trivial by construction.
- Not checked (assumption): that the conf reaches `from_server_conf` unchanged in a real deployment. I did not run Pingora, as instructed. Whether a given Pingora user's config path includes these unstable fields is unknown to me.
- Opinion: severity is low. The fields are marked "unstable" in the docs, and the config is loaded at startup, so the panic is at boot, not mid-traffic. Cloudflare's was a hot-reload.

Modeled vs trusted
- Copied or modeled: the four checks in `validate` (the real error messages dropped); the two `parse().unwrap()` loops (unwrap turned into a precondition on `is_some`).
- Replaced: `ServerConf` shrunk to the 5 relevant fields; `IpAddr` is `u32`; `MAXB` is arbitrary (real constant not used).
- Trusted (two axioms): `is_ip` is an uninterpreted predicate standing for std `IpAddr::from_str`, and `x_is_not_ip` is `admit()`ed ("x" is not an IP literal). `parse_ip` is `external_body`.
- Not modeled: serde_yaml deserialization (the YAML-to-struct step), `Result`/`Error`, logging, `format!`.

Effort (fact, approximate)
- About 25 min agent time including candidate search: clone and read about 12 min, write the model and proof about 13 min.
- 6 verify runs; 5 failed on syntax (`to_string` not allowed in spec context, missing `decreases`, my sed edits), 1 passed.
- Code vs spec: `pingora_conf.rs` is about 105 lines. The copied code is about 45 lines and the spec, proof and trusted lines about 40. The remainder is comments and blank lines.

Blockers (fact unless marked)
- No Verus support for `str::parse` or `IpAddr`; had to use an uninterpreted predicate. So "the consumer does not panic" is proved relative to that axiom, not to std.
- No serde: the real theorem about YAML input needs a model of serde_yaml's `Deserialize`. I don't know how to do this short of treating it as an axiom.
- `String` literals in specs: `"x".to_string()` is rejected in spec context; use `"x"@` (view).
- Verus binary prints a GLIBC_2.39 warning on this host but runs (the warning is harmless here; the z3 was already replaced per vlm_servo/SUMMARY.md).
- I did not try Linkerd2-proxy, Vector, or Quickwit. I don't know whether they have a better (more Cloudflare-like, hot-reload) pair.

## Follow-up: Pingora real flow, and closer matches

Takeaway: the Pingora panic is reachable from a YAML file via the normal startup flow. The closest match I found is river (memorysafety/river, built on Pingora): its config validator accepts filter entries that its consumer then `unwrap`s, and even `--validate-configs` panics. I found no hot-reload example. Vector, sozu and linkerd2-proxy look defended against this pattern in the parts I read.

Pingora flow check (fact, by source reading; nothing run)
- `Server::new(Some(opt))` with `-c conf.yaml` calls `ServerConf::load_yaml_with_opt_override` (`pingora-core/src/server/mod.rs:507`), which calls `from_yaml` and then `validate`. The result is `server.configuration`.
- The documented pattern `http_proxy_service(&server.configuration, app)` (`pingora-proxy/src/lib.rs:2244-2262`) calls `HttpProxy::new(inner, conf.clone())`, which calls `ConnectorOptions::from_server_conf(&conf)` (lib.rs:233).
- So the YAML strings in `client_bind_to_ipv4/6` reach the `parse().unwrap()` unchanged; the panic is at proxy-service construction, before `run_forever`. Only that path in the repo's non-test code calls `from_server_conf` (the only other call is lib.rs:265 in `new_custom`, with the same input).
- Caveat: I did not run it. This is startup, not hot reload.

river (fact, by source reading), commit 0b09036f16d8a2bfe4c6965e3f7acb7f245b509f
- (`cloudflare/river` does not exist on GitHub; I used `memorysafety/river`, a Pingora-based proxy. I don't know whether it is related to Cloudflare's internal proxy.)
- Validator: `config/kdl/mod.rs:169` `collect_filters` copies every `filter k=v` node into a `BTreeMap<String,String>` with no check of keys or values. `Config::validate` (`config/internal.rs:79`) checks only pid-file and upgrade-socket paths; its own comment says "mostly ad-hoc checks".
- Consumer: `Modifiers::from_conf` (`proxy/mod.rs:90-240`) does `filter.remove("kind").unwrap()` and `...::from_settings(filter).unwrap()`. For an unknown kind it returns `Err`, and `from_basic_conf` (proxy/mod.rs:93) then calls `.unwrap()` on that.
- Counterexamples (the validator accepts, the consumer panics), all in the KDL `request-filters` block:
  - a `filter` node with no `kind` argument: `remove("kind").unwrap()` on None
  - `filter kind="block-cidr-range"` with no `addrs`: `from_settings` returns Err, unwrap panics
  - `filter kind="block-cidr-range" addrs="bad"`: the CIDR parse fails, unwrap panics
  - `filter kind="x"`: unknown kind, outer unwrap panics
- Order in `main.rs:18-45`: services are built (the panic site) before `bootstrap()` and `run_forever()`. Pingora's test mode (`--validate-configs`, `internal.rs:43`) exits only inside Pingora, so `river --validate-configs` panics on these inputs instead of reporting them. I read this order; I did not run it.
- Verus `verus/river_filters.rs`: 4 verified, 0 errors.
  - `cex_missing_kind`, `cex_missing_addrs`, `cex_unknown_kind` prove `validator_accepts(f) && !consumer_ok(f)`. These need no axioms.
  - Trusted: `cidr_list_ok` is uninterpreted (std/ipnet parsing); it is used in `consumer_ok` but none of the counterexamples depend on it. The `addrs="bad"` case is not proved, only read.
  - Modeled: `Filter` has only `kind` and `addrs`; `validator_accepts` is the constant `true`, which I read off the code for the map contents but did not prove from a copied `collect_filters`.
- Effort: about 10 min for river, 2 verify runs (one failure: string-literal lengths need `reveal_strlit`). File is about 45 lines, nearly all spec; there is no real code copied this time.
- Opinion: this is a real validator/consumer gap, but still startup-only and operator-written config, so it is a usability bug, not a Cloudflare-class outage.

Candidates read and found defended or unsuitable (inference; shallow reads, not audits)
- sozu 072b610e: `validate_max_connection_attempts` is applied at config load and re-applied by the consumer (`lib/src/server.rs:1476`, falls back to default and logs). The code comments show the authors deliberately re-validate at the consumer.
- linkerd2-proxy 16d3717b: the policy proto conversion (`local_rate_limit.rs:135-190`) uses `NonZeroU32::new(..).and_then` and `.ok()`, dropping bad entries instead of panicking. The `expect("non-zero RPS")` sites are `#[cfg(test)]`. `meta.rs:112` `splitn(2,..).next().unwrap()` cannot fail (first item of `splitn` always exists).
- vector 515e87d9: `topology/builder.rs:107-120` has `expect` and "double initialization" panics, but those are set once from CLI args at startup (`app.rs:633`) with `checked_mul` guards, not from reloaded config. I did not examine the reload path itself or `vector validate`; I don't know whether they diverge.
- Not tried: Quickwit, rama.
- Hot reload: none of the programs examined has a pushed-config path where I found a validator/consumer gap. I don't know whether one exists in Vector or Quickwit.
