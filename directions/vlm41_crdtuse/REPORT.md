# vlm41_crdtuse: are the Rust CRDT sync libraries widely used?
(authored by agents unless marked 🧑)

Ramesh's test: "find a problem where we have code in Rust, but that's also widely used ... if it turns out that the auto-merge and LORO stuff are widely used, like, for example, they're used in some widely used product, then that might be fine."

Answer: Automerge and Loro pass the test only weakly, while Yrs (the Rust port of Yjs) passes it. The widely used library is Yjs, and Yjs is JavaScript (npm `yjs` had 53M downloads in 30 days, against 0.37M for `@automerge/automerge` and 0.81M for `loro-crdt`). The strongest Rust-in-a-real-product case is Yrs: Jupyter real-time collaboration uses Yrs through pycrdt on the server, and AppFlowy uses Yrs directly. Automerge's npm package wraps Rust compiled to WASM, so its JS users do run Rust code. But its known users are GoodNotes and Bowtie, named only as funders, and I don't know how they ship it. Loro has no large public user, and Marimo removed it on 2026-11-04. Details and quotes are in adoption.md. These are inferences from download counts and dependency files; active-user numbers are unknown for every product.

Only Automerge and Yrs have a dedicated sync module, and both are small:
- automerge: about 1.3k non-test lines of sync code in a 48k-line crate, with no unsafe code and no async
- yrs: 1.2k lines in `sync/`, or 7.1k including state vectors and update encoding, in a 32k-line crate; 2 unsafe uses in the sync and update files; the sync handlers are async
- loro and diamond-types: no sync protocol; peers exchange version vectors and export/import blobs; the encoding layer is about 9.2k lines in loro and about 4.9k in diamond-types (which files count is a judgment call)

Details are in code_size.md, and the clones are in src/.

Products hit real sync bugs, but their root causes are not established. Examples: AppFlowy #9032 "Data is not synced from another device", AFFiNE #14846 (sync fails silently and the document reverts), and jupyter-collaboration #219 (data loss). The full list with links is in adoption.md, and library-level bugs are in ../vlm29_crdt/bugs.md. I did not check which of these are library bugs and which are app bugs.

Implication (opinion): if this direction goes ahead, Yrs's sync protocol is the target that best fits "Rust + widely used", with Jupyter as the product to cite. Automerge's sync is the cleanest to verify (small, synchronous, no unsafe code), but its adoption story is weak.

Gaps: no papers were used, so nothing was added to paper_collection. GitHub dependents counts could not be scraped. Several sources were seen only as search snippets; adoption.md marks them for re-checking before anyone cites them.
