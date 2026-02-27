mod common;

use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion};
use memori_core::SearchQuery;

fn bench_vector_search(c: &mut Criterion) {
    let mut group = c.benchmark_group("vector_search");

    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, _ids, vecs) = common::seed_db(scale);
        // Use a vector from the pool as the query
        let query_vec = vecs[0].clone();

        if scale >= 500_000 {
            group.sample_size(15);
            group.measurement_time(std::time::Duration::from_secs(10));
        } else if scale >= 100_000 {
            group.sample_size(30);
            group.measurement_time(std::time::Duration::from_secs(5));
        } else {
            group.sample_size(50);
            group.measurement_time(std::time::Duration::from_secs(10));
        }

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                db.search(SearchQuery {
                    vector: Some(query_vec.clone()),
                    limit: 10,
                    ..Default::default()
                })
                .unwrap()
            })
        });
    }

    group.finish();
}

fn bench_text_search(c: &mut Criterion) {
    let mut group = c.benchmark_group("text_search");
    let queries = common::text_queries();

    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, _ids, _vecs) = common::seed_db(scale);
        let mut query_idx = 0usize;

        if scale >= 500_000 {
            group.sample_size(15);
            group.measurement_time(std::time::Duration::from_secs(10));
        } else if scale >= 100_000 {
            group.sample_size(30);
            group.measurement_time(std::time::Duration::from_secs(5));
        } else {
            group.sample_size(50);
            group.measurement_time(std::time::Duration::from_secs(10));
        }

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                let text = queries[query_idx % queries.len()];
                query_idx += 1;
                db.search(SearchQuery {
                    text: Some(text.to_string()),
                    text_only: true,
                    limit: 10,
                    ..Default::default()
                })
                .unwrap()
            })
        });
    }

    group.finish();
}

fn bench_hybrid_search(c: &mut Criterion) {
    let mut group = c.benchmark_group("hybrid_search");
    let queries = common::text_queries();

    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, _ids, vecs) = common::seed_db(scale);
        let query_vec = vecs[0].clone();
        let mut query_idx = 0usize;

        if scale >= 500_000 {
            group.sample_size(15);
            group.measurement_time(std::time::Duration::from_secs(10));
        } else if scale >= 100_000 {
            group.sample_size(30);
            group.measurement_time(std::time::Duration::from_secs(5));
        } else {
            group.sample_size(50);
            group.measurement_time(std::time::Duration::from_secs(10));
        }

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                let text = queries[query_idx % queries.len()];
                query_idx += 1;
                db.search(SearchQuery {
                    vector: Some(query_vec.clone()),
                    text: Some(text.to_string()),
                    limit: 10,
                    ..Default::default()
                })
                .unwrap()
            })
        });
    }

    group.finish();
}

fn bench_filtered_search(c: &mut Criterion) {
    let mut group = c.benchmark_group("filtered_search");

    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, _ids, vecs) = common::seed_db(scale);
        let query_vec = vecs[0].clone();

        if scale >= 500_000 {
            group.sample_size(15);
            group.measurement_time(std::time::Duration::from_secs(10));
        } else if scale >= 100_000 {
            group.sample_size(30);
            group.measurement_time(std::time::Duration::from_secs(5));
        } else {
            group.sample_size(50);
            group.measurement_time(std::time::Duration::from_secs(10));
        }

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                db.search(SearchQuery {
                    vector: Some(query_vec.clone()),
                    filter: Some(serde_json::json!({"type": "debugging"})),
                    limit: 10,
                    ..Default::default()
                })
                .unwrap()
            })
        });
    }

    group.finish();
}

criterion_group! {
    name = benches;
    config = Criterion::default();
    targets = bench_vector_search, bench_text_search, bench_hybrid_search, bench_filtered_search
}
criterion_main!(benches);
