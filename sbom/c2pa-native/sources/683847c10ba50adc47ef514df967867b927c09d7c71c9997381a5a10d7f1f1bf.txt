# extfmt

[![](http://meritbadge.herokuapp.com/extfmt)](https://crates.io/crates/extfmt)

A crate with additional formatting options for Rust types

## Usage

Add the dependency to your `Cargo.toml`:

```toml
[dependencies]
extfmt = "0.1"
```

```rust
extern crate extfmt;

use extfmt::*;

fn main() {
	// Wrapper types for prettier printing of slices.
	//
	// The string is formatted in a "slice" form, and supports most 
	// format specifiers as long as the underlying type implements them
	//
	// This prints "[01, 02, ff, 40]"
	println!("{:02x}", CommaSeparated(&[1, 2, 255, 64]));

	// Compact formatting of byte slices:
	// This prints "0102ff40".
	println!("{}", Hexlify(&[1, 2, 255, 64]));

	// Pretty buffer printing using `hexdump`.
	println!("{}", hexdump!(&[1u8, 2, 255, 64]));
	// 	 => 00000000	01 02 ff 40

	// Hexdump can also be used as a memory view for Sized types.
	println!("{}", hexdump!(64));
	//   => 00000000	40 00 00 00

	// Further hexdump options
	println!("{}", hexdump!(64, show_index: false));
	//   => 40 00 00 00
}
```
