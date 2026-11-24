# Third-party material

The root LICENSE applies to this example's project-authored material. Dependencies
retain their own terms; the project's Apache-2.0 licence does not replace them.

`make dev-update` prepares the project's licence, this document, and a dependency
attribution archive before building `confai-transport`. The archive records the
locked Cargo graph for the build target and preserves dependency licence and notice files, including
the bundled OpenSSL sources used by the transport. The Confido verifier wheel
carries its own attribution. Both wheels are installed into the demo container.

The Python dependency set is pinned in `requirements.lock`; installed
distributions carry their own licence metadata. Review the final wheel and
container inventories before public distribution. These collected files document
upstream terms; they do not establish ownership or licence compatibility.

The macOS transport graph includes `system-configuration` and
`system-configuration-sys`. Their published crates declare `MIT OR Apache-2.0`
but omit standalone licence files. The reviewed supplements in `third_party/`
record the Apache-2.0 option and bind the notices to the published crate
revisions before packaging.
