# c2pa_raw_crypto

[![CI](https://github.com/contentauth/c2pa-raw-crypto/actions/workflows/ci.yml/badge.svg)](https://github.com/contentauth/c2pa-raw-crypto/actions/workflows/ci.yml) [![Latest Version](https://img.shields.io/crates/v/c2pa-raw-crypto.svg)](https://crates.io/crates/c2pa-raw-crypto) [![docs.rs](https://img.shields.io/docsrs/c2pa_raw_crypto)](https://docs.rs/c2pa_raw_crypto/) [![codecov](https://codecov.io/gh/contentauth/c2pa-raw-crypto/branch/main/graph/badge.svg?token=z1yA0Y6HZK)](https://codecov.io/gh/contentauth/c2pa-raw-crypto)

Raw cryptographic signing and validation primitives for [C2PA](https://c2pa.org).

**IMPORTANT:** This crate is an implemementation detail for the [`c2pa`](https://crates.io/crates/c2pa) crate and not generally designed for independent use.

This crate provides the `RawSigner` and `RawSignatureValidator` traits together with built-in implementations of the digital signature algorithms required by the C2PA specification.
It deliberately stays narrow: it knows nothing about COSE framing, RFC 3161 time stamping, or OCSP — those concerns are handled by the calling code (today, the `c2pa` crate).

## Cryptography backend / Crate features

Two cryptography backends are available via Cargo feature flags:

- **`rust_native_crypto`** (enabled by default) — pure-Rust crates.
- **`openssl`** — a vendored OpenSSL implementation.

**`rust_native_crypto` takes precedence.** If both features end up enabled (which can happen through Cargo feature unification in a workspace), the rust-native backend is selected at runtime and the OpenSSL backend, while compiled, is not used.
This is not considered an error.

Enabling neither is allowed (e.g. when only the type definitions are needed, or when signing is delegated to a remote service and no validation is performed); in that case the built-in signer/validator constructors report an error / return `None` at runtime.

## Contributions and feedback

We welcome contributions to this project. For information on contributing, providing feedback, and about ongoing work, see [Contributing](./CONTRIBUTING.md).

## Requirements

The toolkit requires **Rust version 1.88.0** or newer. When a newer version of Rust becomes required, a new minor (1.x.0) version of this crate will be released.

### Supported platforms

This crate's [CI workflow](./.github/workflows/ci.yml) builds and tests against the platforms that the [`c2pa-rs` support tiers](https://github.com/contentauth/c2pa-rs/blob/main/docs/support-tiers.md) cover (Tiers 1A, 1B, and 2). Unlike `c2pa-rs`, this crate does not split those platforms across separate tier workflows — because it evolves more slowly, every platform below is exercised on every commit.

The crate is built and tested on the following platforms:

* Windows (`x86_64-pc-windows-msvc` and `aarch64-pc-windows-msvc`)
  * Only the MSVC build chain is supported on Windows. As discussed in [#155](https://github.com/adobe/xmp-toolkit-rs/issues/155), we would welcome a PR to enable GNU build chain support on Windows.

* macOS on Apple silicon (`aarch64-apple-darwin`)

* Linux on x86 (`x86_64-unknown-linux-gnu`) and ARM v8 (`aarch64-unknown-linux-gnu`)

* Wasm in the browser (`wasm32-unknown-unknown`)

* WASI (`wasm32-wasip2`)

The crate is also verified on the following platforms. CI runs the full test suite on the iOS simulator and confirms that the remaining targets build, but does not run tests on physical devices:

* iOS (tested on the `aarch64-apple-ios-sim` simulator; `aarch64-apple-ios` and `x86_64-apple-ios` are build-verified)

* Android (`aarch64-linux-android`, `armv7-linux-androideabi`, `i686-linux-android`, and `x86_64-linux-android` are build-verified)

## License

The `c2pa_raw_crypto` crate is distributed under the terms of both the MIT license and the Apache License (Version 2.0).

See [LICENSE-APACHE](./LICENSE-APACHE) and [LICENSE-MIT](./LICENSE-MIT).

Note that some components and dependent crates are licensed under different terms; please check the license terms for each crate and component for details.
