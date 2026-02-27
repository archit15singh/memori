mod common;

use criterion::{black_box, criterion_group, criterion_main, Criterion};
use memori_core::embed;
use memori_core::Memori;
use rand::rngs::StdRng;
use rand::SeedableRng;

fn bench_embed_text(c: &mut Criterion) {
    let mut group = c.benchmark_group("embed_text");
    group.sample_size(20);
    group.measurement_time(std::time::Duration::from_secs(30));
    group.warm_up_time(std::time::Duration::from_secs(5));

    let mut rng = StdRng::seed_from_u64(42);
    let content = common::random_content(&mut rng);

    group.bench_function("single", |bencher| {
        bencher.iter(|| embed::embed_text(black_box(&content)))
    });

    group.finish();
}

fn bench_embed_batch(c: &mut Criterion) {
    let mut group = c.benchmark_group("embed_batch");
    group.sample_size(20);
    group.measurement_time(std::time::Duration::from_secs(30));
    group.warm_up_time(std::time::Duration::from_secs(5));

    let mut rng = StdRng::seed_from_u64(42);

    for &batch_size in &[10usize, 100] {
        let texts: Vec<String> = (0..batch_size).map(|_| common::random_content(&mut rng)).collect();
        let text_refs: Vec<&str> = texts.iter().map(|s| s.as_str()).collect();

        group.bench_function(format!("{}", batch_size), |bencher| {
            bencher.iter(|| embed::embed_batch(black_box(&text_refs)))
        });
    }

    group.finish();
}

fn bench_insert_with_auto_embed(c: &mut Criterion) {
    let mut group = c.benchmark_group("insert_with_auto_embed");
    group.sample_size(20);
    group.measurement_time(std::time::Duration::from_secs(30));
    group.warm_up_time(std::time::Duration::from_secs(5));

    let db = Memori::open(":memory:").expect("failed to open in-memory DB");
    let mut rng = StdRng::seed_from_u64(42);

    group.bench_function("single", |bencher| {
        bencher.iter(|| {
            let content = common::random_content(&mut rng);
            let meta = common::random_metadata(&mut rng);
            db.insert(
                black_box(&content),
                None,
                Some(meta),
                None,  // no dedup
                false, // auto-embed enabled
            )
            .unwrap()
        })
    });

    group.finish();
}

criterion_group!(
    benches,
    bench_embed_text,
    bench_embed_batch,
    bench_insert_with_auto_embed,
);
criterion_main!(benches);
