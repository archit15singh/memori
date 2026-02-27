mod common;

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use memori_core::util::{cosine_similarity, vec_to_blob, blob_to_vec};
use memori_core::storage::find_duplicate;
use memori_core::schema;
use rand::rngs::StdRng;
use rand::SeedableRng;

fn bench_cosine_similarity(c: &mut Criterion) {
    let mut rng = StdRng::seed_from_u64(42);
    let a = common::random_unit_vector(&mut rng);
    let b = common::random_unit_vector(&mut rng);

    c.bench_function("cosine_similarity/384", |bencher| {
        bencher.iter(|| cosine_similarity(black_box(&a), black_box(&b)))
    });
}

fn bench_vec_to_blob(c: &mut Criterion) {
    let mut rng = StdRng::seed_from_u64(42);
    let v = common::random_unit_vector(&mut rng);

    c.bench_function("vec_to_blob/384", |bencher| {
        bencher.iter(|| vec_to_blob(black_box(&v)))
    });
}

fn bench_blob_to_vec(c: &mut Criterion) {
    let mut rng = StdRng::seed_from_u64(42);
    let v = common::random_unit_vector(&mut rng);
    let blob = vec_to_blob(&v).to_vec();

    c.bench_function("blob_to_vec/384", |bencher| {
        bencher.iter(|| blob_to_vec(black_box(&blob)))
    });
}

fn bench_find_duplicate(c: &mut Criterion) {
    let mut group = c.benchmark_group("find_duplicate");
    group.sample_size(50);

    for &scale in &[1_000usize, 10_000] {
        // Build a standalone Connection + schema since Memori.conn is private
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        schema::init_db(&conn).unwrap();

        let mut rng = StdRng::seed_from_u64(42);
        let base_ts = 1700000000.0;

        for i in 0..scale {
            let id = uuid::Uuid::new_v4().to_string();
            let content = common::random_content(&mut rng);
            let vec = common::random_unit_vector(&mut rng);
            let meta = common::random_metadata(&mut rng);
            let blob = vec_to_blob(&vec);
            let meta_str = meta.to_string();
            let ts = base_ts + (i as f64);

            conn.execute(
                "INSERT INTO memories (id, content, vector, metadata, created_at, updated_at) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                rusqlite::params![id, content, blob, meta_str, ts, ts],
            ).unwrap();
        }

        let query_vec = common::random_unit_vector(&mut rng);

        group.bench_with_input(BenchmarkId::from_parameter(scale), &scale, |bencher, _| {
            bencher.iter(|| {
                find_duplicate(black_box(&conn), black_box(&query_vec), None, 0.92).unwrap()
            })
        });
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_cosine_similarity,
    bench_vec_to_blob,
    bench_blob_to_vec,
    bench_find_duplicate,
);
criterion_main!(benches);
