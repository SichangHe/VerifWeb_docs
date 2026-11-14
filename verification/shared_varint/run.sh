#!/usr/bin/env bash
# Reproduce: quinn and quiche varint code match upstream text and verify against spec.rs;
# a one-constant mutation of quiche's mask fails verification.
set -eu
: "${VERUS:?set VERUS to the verifier executable}"
dir=$(cd -- "$(dirname -- "$0")" && pwd)
s=$(mktemp -d); trap 'rm -rf "$s"' EXIT
git clone -q -b verus-varint --depth 50 https://github.com/SichangHe/quinn "$s/quinn"
git clone -q -b verus-varint --depth 50 https://github.com/SichangHe/quiche "$s/quiche"
git -C "$s/quinn" fetch -q --depth 1 origin c7b46a969cd315398b504792e9e9af6a15a7dcc6 2>/dev/null || git -C "$s/quinn" fetch -q https://github.com/quinn-rs/quinn c7b46a969cd315398b504792e9e9af6a15a7dcc6
git -C "$s/quiche" fetch -q https://github.com/cloudflare/quiche da28c7a42718f4e8353a09687dd6efbdfe0a5db1
git -C "$s/quinn" show c7b46a969cd315398b504792e9e9af6a15a7dcc6:quinn-proto/src/varint.rs >"$s/up_quinn.rs"
git -C "$s/quiche" show da28c7a42718f4e8353a09687dd6efbdfe0a5db1:octets/src/lib.rs >"$s/up_octets.rs"
mkdir "$s/v"; cp "$dir/spec.rs" "$s/quinn/verus/varint/quinn.rs" "$s/quiche/verus/varint/quiche.rs" "$s/v/"
python3 -I "$dir/conform.py" "$s/v/quinn.rs" "$s/up_quinn.rs" 'fn decode<B: Buf>' 'fn encode<B: BufMut>'
python3 -I "$dir/conform.py" "$s/v/quiche.rs" "$s/up_octets.rs" 'macro_rules! static_assert' 'macro_rules! peek_u' 'macro_rules! get_u' \
  '    pub fn get_u8' '    pub fn peek_u8' '    pub fn get_u16' '    pub fn get_u32' '    pub fn get_u64' '    pub fn cap(' '    pub fn get_varint' 'pub const fn varint_parse_len'
cd "$s/v"
timeout 600 "$VERUS" --num-threads 1 --edition 2018 quinn.rs 2>&1 | grep -q 'verification results:: 27 verified, 0 errors'; echo "quinn: 27 verified, 0 errors"
timeout 600 "$VERUS" --num-threads 1 --edition 2018 quiche.rs 2>&1 | grep -q 'verification results:: 25 verified, 0 errors'; echo "quiche: 25 verified, 0 errors"
sed 's/0x3fffffff)/0x3ffffffe)/' quiche.rs >mutant.rs
if timeout 600 "$VERUS" --num-threads 1 --edition 2018 mutant.rs >m.log 2>&1; then echo "mutant unexpectedly verified"; exit 1; fi
grep -q 'verification results:: 24 verified, 1 errors' m.log; echo "quiche mutant (4-byte mask off by one bit): rejected"
