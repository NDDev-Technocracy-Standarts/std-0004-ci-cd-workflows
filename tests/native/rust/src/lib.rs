//! Smallest crate that still exercises a real Rust toolchain: it builds, it
//! tests, and it is `rustfmt`- and `clippy`-clean, so one tree can prove
//! rust-ci's build, test, fmt and clippy lanes without a dependency.

/// Sums the bytes of `text` modulo 256.
///
/// ```
/// assert_eq!(ciwf_fixture::checksum("ci"), 204);
/// ```
#[must_use]
pub fn checksum(text: &str) -> u8 {
    text.bytes().fold(0u8, u8::wrapping_add)
}

#[cfg(test)]
mod tests {
    use super::checksum;

    #[test]
    fn checksum_is_stable() {
        assert_eq!(checksum("ci"), 204);
        assert_eq!(checksum(""), 0);
    }
}
