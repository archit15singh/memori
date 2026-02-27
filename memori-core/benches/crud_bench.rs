mod common;

use criterion::{black_box, criterion_group, criterion_main, BatchSize, BenchmarkId, Criterion};
use memori_core::SortField;
use rand::rngs::StdRng;
use rand::SeedableRng;

fn bench_insert(c: &mut Criterion) {
    let mut group = c.benchmark_group("insert");

    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, _ids, _vecs) = common::seed_db(scale);
        let mut rng = StdRng::seed_from_u64(99);

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                let content = common::random_content(&mut rng);
                let meta = common::random_metadata(&mut rng);
                db.insert(
                    black_box(&content),
                    None,
                    Some(meta),
                    None,       // no dedup
                    true,       // no_embed
                )
                .unwrap()
            })
        });
    }

    group.finish();
}

fn bench_get(c: &mut Criterion) {
    let mut group = c.benchmark_group("get");

    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, ids, _vecs) = common::seed_db(scale);
        let mut idx = 0usize;

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                let id = &ids[idx % ids.len()];
                idx += 1;
                db.get(black_box(id)).unwrap()
            })
        });
    }

    group.finish();
}

fn bench_get_prefix(c: &mut Criterion) {
    let mut group = c.benchmark_group("get_prefix");

    // 8-char prefixes collide at 500K+ (birthday paradox on hex chars).
    // Use 12-char prefixes at large scales to avoid AmbiguousPrefix errors.
    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, ids, _vecs) = common::seed_db(scale);
        let prefix_len = if scale >= 500_000 { 12 } else { 8 };
        let prefixes: Vec<String> = ids.iter().map(|id| id[..prefix_len].to_string()).collect();
        let mut idx = 0usize;

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                let prefix = &prefixes[idx % prefixes.len()];
                idx += 1;
                db.get(black_box(prefix)).unwrap()
            })
        });
    }

    group.finish();
}

fn bench_delete(c: &mut Criterion) {
    let mut group = c.benchmark_group("delete");
    group.sample_size(50);

    for &scale in &[1_000usize, 10_000] {
        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, &s| {
            bencher.iter_batched(
                || {
                    // Setup: create a fresh DB for each iteration since delete is destructive
                    let (db, ids, _vecs) = common::seed_db(s);
                    (db, ids[0].clone())
                },
                |(db, id)| {
                    db.delete(black_box(&id)).unwrap()
                },
                BatchSize::LargeInput,
            )
        });
    }

    group.finish();
}

fn bench_list(c: &mut Criterion) {
    let mut group = c.benchmark_group("list");

    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, _ids, _vecs) = common::seed_db(scale);

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                db.list(None, &SortField::Created, 20, 0, None, None).unwrap()
            })
        });
    }

    group.finish();
}

fn bench_count(c: &mut Criterion) {
    let mut group = c.benchmark_group("count");

    for &scale in &[1_000usize, 10_000, 100_000, 500_000] {
        let (db, _ids, _vecs) = common::seed_db(scale);

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| db.count().unwrap())
        });
    }

    group.finish();
}

criterion_group! {
    name = benches;
    config = Criterion::default().sample_size(100);
    targets = bench_insert, bench_get, bench_get_prefix, bench_delete, bench_list, bench_count
}
criterion_main!(benches);
