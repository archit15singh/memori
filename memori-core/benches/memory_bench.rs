//! Memory efficiency benchmark -- measures DB file size and write throughput.
//!
//! Not a criterion benchmark; prints a markdown table directly.
//! Run: cargo bench --bench memory_bench

mod common;

use memori_core::Memori;
use rand::rngs::StdRng;
use rand::SeedableRng;
use std::time::Instant;

fn file_size_bytes(path: &str) -> u64 {
    std::fs::metadata(path).map(|m| m.len()).unwrap_or(0)
}

fn format_bytes(bytes: u64) -> String {
    if bytes < 1024 {
        format!("{} B", bytes)
    } else if bytes < 1024 * 1024 {
        format!("{:.1} KB", bytes as f64 / 1024.0)
    } else if bytes < 1024 * 1024 * 1024 {
        format!("{:.1} MB", bytes as f64 / (1024.0 * 1024.0))
    } else {
        format!("{:.2} GB", bytes as f64 / (1024.0 * 1024.0 * 1024.0))
    }
}

fn format_count(n: usize) -> String {
    match n {
        n if n >= 1_000_000 => format!(
            "{},{:03},{:03}",
            n / 1_000_000,
            (n % 1_000_000) / 1_000,
            n % 1_000
        ),
        n if n >= 1_000 => format!("{},{:03}", n / 1_000, n % 1_000),
        _ => format!("{}", n),
    }
}

fn format_rate(n: usize, d: std::time::Duration) -> String {
    let per_sec = n as f64 / d.as_secs_f64();
    if per_sec >= 1_000.0 {
        format!("{:.1}K/s", per_sec / 1_000.0)
    } else {
        format!("{:.0}/s", per_sec)
    }
}

fn cleanup(path: &str) {
    let _ = std::fs::remove_file(path);
    let _ = std::fs::remove_file(format!("{}-wal", path));
    let _ = std::fs::remove_file(format!("{}-shm", path));
}

fn measure_scale(n: usize) {
    let path = format!("/tmp/memori-bench-memory-{}.db", n);
    cleanup(&path);

    eprint!("  Seeding {} memories ... ", format_count(n));

    let db = Memori::open(&path).expect("open failed");

    let insert_start = Instant::now();
    {
        let mut rng = StdRng::seed_from_u64(42);
        let base_ts = 1_700_000_000.0;

        for i in 0..n {
            let id = uuid::Uuid::new_v4().to_string();
            let content = common::random_content(&mut rng);
            let vec = common::random_unit_vector(&mut rng);
            let meta = common::random_metadata(&mut rng);
            let ts = base_ts + (i as f64);

            db.insert_with_id(&id, &content, Some(&vec), Some(meta), ts, ts)
                .expect("insert failed");
        }
    }
    let insert_time = insert_start.elapsed();

    db.vacuum().unwrap();
    drop(db);

    let db_size = file_size_bytes(&path);
    let per_memory = db_size / n as u64;

    eprintln!("{:.1}s", insert_time.as_secs_f64());

    println!(
        "| {} | {} | {} | {} |",
        format_count(n),
        format_bytes(db_size),
        format_bytes(per_memory),
        format_rate(n, insert_time),
    );

    cleanup(&path);
}

fn main() {
    println!("### Memory Efficiency\n");
    println!("| Memories | DB Size | Per-Memory | Write Throughput |");
    println!("|---|---|---|---|");

    for &scale in &[1_000, 10_000, 100_000, 500_000, 1_000_000] {
        measure_scale(scale);
    }

    println!();
    println!(
        "*Each memory includes ~100 words of content + 384-dim embedding vector + JSON metadata.*"
    );
    println!("*DB Size measured after VACUUM. Write throughput = inserts/sec including content + vector + FTS5 indexing.*");
}
