# macOS dependency attribution

The `reqwest` transport dependency brings in `system-configuration` and
`system-configuration-sys` on macOS. Their published crates declare
`MIT OR Apache-2.0` but contain no standalone licence files. Each directory
here contains the selected Apache-2.0 text, a short attribution notice, and
provenance recording the published crate revision and file digests.

The pinned Confido attribution collector checks those records when building
the macOS transport wheel. These files belong to this application because
Confido's verifier does not depend on the two crates.
