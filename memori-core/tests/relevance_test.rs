use memori_core::{Memori, MemoriError, SearchQuery};

#[test]
fn threshold_is_applied_before_popularity_and_limit() {
    let db = Memori::open(":memory:").unwrap();
    let best = db
        .insert("best", Some(&[1.0, 0.0]), None, None, true)
        .unwrap();
    let weak = db
        .insert("weak", Some(&[0.6, 0.8]), None, None, true)
        .unwrap();
    db.set_access_stats(weak.id(), Some(2_000_000_000.0), 1_000_000)
        .unwrap();
    let query = SearchQuery {
        vector: Some(vec![1.0, 0.0]),
        limit: 1,
        ..Default::default()
    };
    assert_eq!(db.search(query.clone()).unwrap()[0].id, weak.id());
    assert_eq!(
        db.search(SearchQuery {
            min_similarity: Some(0.9),
            ..query
        })
        .unwrap()[0]
            .id,
        best.id()
    );
}

#[test]
fn hybrid_gates_semantic_candidates_and_preserves_literal_matches() {
    let db = Memori::open(":memory:").unwrap();
    let exact = db
        .insert(
            "PostgreSQL architecture",
            Some(&[0.0, 1.0]),
            None,
            None,
            true,
        )
        .unwrap();
    db.insert("unrelated", Some(&[0.0, 1.0]), None, None, true)
        .unwrap();
    let query = SearchQuery {
        vector: Some(vec![1.0, 0.0]),
        text: Some("PostgreSQL".into()),
        min_similarity: Some(0.9),
        ..Default::default()
    };
    let results = db.search(query.clone()).unwrap();
    assert_eq!(results.len(), 1);
    assert_eq!(results[0].id, exact.id());
    assert!(db
        .search(SearchQuery {
            text: Some("bananas".into()),
            ..query
        })
        .unwrap()
        .is_empty());
}

#[test]
fn invalid_threshold_and_unsupported_modes_are_errors() {
    let db = Memori::open(":memory:").unwrap();
    for threshold in [f32::NAN, f32::INFINITY, -1.1, 1.1] {
        assert!(matches!(
            db.search(SearchQuery {
                vector: Some(vec![1.0]),
                min_similarity: Some(threshold),
                ..Default::default()
            }),
            Err(MemoriError::InvalidSimilarity(_))
        ));
    }
    assert!(matches!(
        db.search(SearchQuery {
            min_similarity: Some(0.5),
            ..Default::default()
        }),
        Err(MemoriError::InvalidSimilarity(_))
    ));
    assert!(db
        .search(SearchQuery {
            text: Some("hello".into()),
            text_only: true,
            min_similarity: Some(0.5),
            ..Default::default()
        })
        .is_err());
    #[cfg(not(feature = "embeddings"))]
    assert!(db
        .search(SearchQuery {
            text: Some("hello".into()),
            min_similarity: Some(0.5),
            ..Default::default()
        })
        .is_err());
}

#[test]
fn inclusive_boundaries_related_prefixes_and_invalid_vectors() {
    let db = Memori::open(":memory:").unwrap();
    let source = db
        .insert("source", Some(&[1.0, 0.0]), None, None, true)
        .unwrap();
    let same = db
        .insert("same", Some(&[1.0, 0.0]), None, None, true)
        .unwrap();
    db.insert("opposite", Some(&[-1.0, 0.0]), None, None, true)
        .unwrap();
    for (content, vector) in [
        ("zero", vec![0.0, 0.0]),
        ("dimension", vec![1.0]),
        ("nan", vec![f32::NAN, 1.0]),
    ] {
        db.insert(content, Some(&vector), None, None, true).unwrap();
    }
    let results = db
        .search(SearchQuery {
            vector: Some(vec![1.0, 0.0]),
            min_similarity: Some(-1.0),
            ..Default::default()
        })
        .unwrap();
    assert_eq!(results.len(), 3);
    let related = db
        .related_with_min_similarity(&source.id()[..8], 5, Some(1.0))
        .unwrap();
    assert_eq!(related.len(), 1);
    assert_eq!(related[0].id, same.id());
    assert!(db
        .search(SearchQuery {
            vector: Some(vec![0.0, 0.0]),
            min_similarity: Some(0.5),
            ..Default::default()
        })
        .is_err());
}
