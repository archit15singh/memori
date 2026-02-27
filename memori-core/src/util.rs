/// Shared low-level utilities for vector serialization and similarity.

/// Convert a float vector to a raw byte slice for SQLite BLOB storage.
///
/// # Safety
/// Reinterprets the f32 slice as raw bytes. The resulting slice borrows
/// from the input and must not outlive it. This is safe because f32 has
/// no alignment requirements stricter than u8, and the byte representation
/// is deterministic on a given platform.
pub fn vec_to_blob(v: &[f32]) -> &[u8] {
    // SAFETY: f32 is 4 bytes, no padding, no invalid bit patterns.
    // The returned slice borrows from `v` and has lifetime tied to it.
    unsafe { std::slice::from_raw_parts(v.as_ptr() as *const u8, v.len() * 4) }
}

/// Convert a raw byte blob back to a float vector.
///
/// # Panics
/// Panics if `b.len()` is not a multiple of 4.
pub fn blob_to_vec(b: &[u8]) -> Vec<f32> {
    assert!(b.len() % 4 == 0, "blob length must be a multiple of 4");
    let mut v = vec![0.0f32; b.len() / 4];
    // SAFETY: We verified the length is a multiple of 4. copy_nonoverlapping
    // is safe here because src (b) and dst (v) don't overlap (v is freshly
    // allocated), and both are valid for the given length.
    unsafe {
        std::ptr::copy_nonoverlapping(b.as_ptr(), v.as_mut_ptr() as *mut u8, b.len());
    }
    v
}

/// Compute cosine similarity between two float vectors.
/// Returns 0.0 for empty vectors, mismatched lengths, or zero-norm vectors.
pub fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }

    let mut dot = 0.0f32;
    let mut norm_a = 0.0f32;
    let mut norm_b = 0.0f32;

    for i in 0..a.len() {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    let denom = norm_a.sqrt() * norm_b.sqrt();
    if denom == 0.0 {
        0.0
    } else {
        dot / denom
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vec_blob_roundtrip() {
        let original = vec![1.0f32, -2.5, 3.14, 0.0];
        let blob = vec_to_blob(&original);
        let restored = blob_to_vec(blob);
        assert_eq!(original, restored);
    }

    #[test]
    fn test_empty_vec_roundtrip() {
        let original: Vec<f32> = vec![];
        let blob = vec_to_blob(&original);
        let restored = blob_to_vec(blob);
        assert_eq!(original, restored);
    }

    #[test]
    #[should_panic(expected = "blob length must be a multiple of 4")]
    fn test_blob_to_vec_bad_length() {
        blob_to_vec(&[1, 2, 3]);
    }

    #[test]
    fn test_cosine_identical() {
        let v = vec![1.0, 2.0, 3.0];
        let sim = cosine_similarity(&v, &v);
        assert!((sim - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_cosine_orthogonal() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![0.0, 1.0, 0.0];
        let sim = cosine_similarity(&a, &b);
        assert!(sim.abs() < 1e-6);
    }

    #[test]
    fn test_cosine_empty() {
        assert_eq!(cosine_similarity(&[], &[]), 0.0);
    }

    #[test]
    fn test_cosine_mismatched_lengths() {
        assert_eq!(cosine_similarity(&[1.0], &[1.0, 2.0]), 0.0);
    }
}
