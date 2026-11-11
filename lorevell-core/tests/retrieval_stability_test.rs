use lorevell_core::{Lorevell, SearchQuery};

#[test]
fn equal_hybrid_scores_have_repeatable_semantic_rank_precedence() {
    let db = Lorevell::open(":memory:").unwrap();
    let keyword_first = db
        .insert("target", Some(&[0.0, 1.0]), None, None, false)
        .unwrap();
    let semantic_first = db
        .insert(
            &format!("target {}", "padding ".repeat(100)),
            Some(&[1.0, 0.0]),
            None,
            None,
            false,
        )
        .unwrap();
    for _ in 0..50 {
        let results = db
            .search(SearchQuery {
                text: Some("target".into()),
                vector: Some(vec![1.0, 0.0]),
                limit: 2,
                ..Default::default()
            })
            .unwrap();
        assert_eq!(results.len(), 2);
        assert_eq!(
            results[0].score, results[1].score,
            "fixture must exercise an actual RRF score tie"
        );
        assert_eq!(results[0].id, semantic_first.id());
        assert_eq!(results[1].id, keyword_first.id());
    }
}
