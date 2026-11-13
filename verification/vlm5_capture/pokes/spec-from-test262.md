# Poke: specs from test262 / verified ECMAScript builtins (new, 6/6 and 4/6 samplers)
(authored by agents unless marked 🧑)
Method: one web search.

- Fact: ESMeta (github.com/es-meta/esmeta) "extracts a mechanized specification from ... ECMA-262". It has run in ECMA-262 and Test262 CI since Nov 2022 and includes a "conformance test synthesizer" (JEST, ICSE 2021) and type analysis (JSTAR, ASE 2021).
- Fact: the search found nothing linking ESMeta to Boa, and no verified Boa builtins.
- Inference: there is a strong combined direction. Use ESMeta's mechanized algorithm steps as the spec source, translate them into Verus specs for the Rust builtins in Boa, and use test262 to validate the specs. This addresses the "what is the spec?" question the advisors raised (WRITEUP 2). A cheap first step: one builtin (e.g. Array.prototype.indexOf) with its ESMeta IR transcribed into Verus.
