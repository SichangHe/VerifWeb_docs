# One RFC 9000 varint spec, two real implementations: pilot
(authored by agents unless marked 🧑)

As of 2026-11-14, one Verus specification of the QUIC variable-length integer (RFC 9000 §16) is proved against the real decoding code of quinn-proto and of quiche's `octets` crate, and against quinn-proto's real encoder. Run `bash run.sh` with `VERUS` set (Verus `0.2026.11.13.6ae5f7b`): quinn "27 verified, 0 errors", quiche "25 verified, 0 errors"; changing quiche's 4-byte mask `0x3fffffff` to `0x3ffffffe` gives "24 verified, 1 errors".

## What is proved

[spec.rs](spec.rs) defines `decode(bytes)`: None if too short, else the big-endian value of the first `len` bytes modulo 2^(8·len−2), where `len` comes from the top two bits of byte 0. This transcribes RFC 9000: "reserves the two most significant bits of the first byte to encode the base-2 logarithm of the integer encoding length in bytes. The integer value is encoded on the remaining bits, in network byte order."

- quinn-proto `VarInt::decode` (main `c7b46a96`): for every input, the result equals `decode(input)`, the cursor advances by exactly the consumed length, and the value is < 2^62.
- quinn-proto `VarInt::encode`: for every value < 2^62, the appended bytes decode back to the value and have the minimal length.
- quiche `octets::Octets::get_varint` and `varint_parse_len` (master `da28c7a4`): same decode theorem.
- Not done: quiche's encoder `put_varint_with_len`. It mutates the buffer through the `&mut [u8]` that `put_u16` etc. return; we did not model that returned borrow.

Real code: proof files live in public fork branches [SichangHe/quinn verus-varint](https://github.com/SichangHe/quinn/tree/verus-varint/verus/varint) and [SichangHe/quiche verus-varint](https://github.com/SichangHe/quiche/tree/verus-varint/verus/varint). [conform.py](conform.py) checks that every listed upstream function and macro appears verbatim after stripping Verus annotations. As in [bounded_memory](../bounded_memory/REPORT.md), this is a textual link; the proof is not compiled as part of either crate.

Trusted base: `from_be_bytes`/`to_be_bytes` specs; a stand-in `TryInto` for slice→array (vstd gives std's blanket `try_into` no usable contract for arrays and the orphan rule forbids adding one, so the files are checked with `--edition 2018` and import the stand-in); quinn's `bytes::Buf`/`BufMut` as traits with cursor specs; quiche's `get_u8/u16/u32/u64/peek_u8` bodies are upstream text but marked `external_body` (their `static_assert!` const blocks call `mem::size_of`, which Verus rejects in exec mode), so their big-endian contracts are assumed.

## What was reused (the measurement)

Non-blank, non-comment lines: spec.rs 132 (definitions ~25, trusted std specs ~30, lemmas ~75). quinn.rs: 49 upstream code, 110 proof and stand-in lines. quiche.rs: 67 upstream code, 96 proof and stand-in lines (about 45 of them the assumed primitive contracts).

- Reused fully: the specification `decode`, `be`, `min_len`, and the buffer view (“unread bytes”) both theorems are stated in.
- Reused by quinn only: the lemmas. quinn clears the tag bits before assembling bytes, so it needs `lemma_be_mod_first` (“masking byte 0 = value mod 2^(8n−2)”). quiche assembles first and masks after, which a per-width `bit_vector` fact closes; it used none of the shared lemmas.
- Reusable but used once: `lemma_encoded` (“bytes whose value is tag·cap + x decode to x”) does not mention quinn; any encoder that writes the tag into the top bits needs only it plus one bit fact per width.

Inference: the spec and the encoding-direction lemma carry over; decode lemmas carry over only between implementations that take the same arithmetic route. Per-implementation cost was dominated by Verus plumbing (buffer-trait stand-ins, std conversion specs, `unreachable!`), not by the standard.

## Side observation (not checked)

quiche callers write frame lengths with `put_varint_with_len(length, 2)` (frame.rs `encode_crypto_header`, `encode_stream_header`, `encode_dgram_header`). If `length` ≥ 16384 the value is truncated and `buf[0] |= 0x40` produces a different tag. Whether any configuration lets a frame length reach 16384 was not checked.
