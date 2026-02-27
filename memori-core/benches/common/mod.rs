use memori_core::Memori;
use rand::Rng;
use rand::rngs::StdRng;
use rand::SeedableRng;

const VOCAB: &[&str] = &[
    "algorithm", "binary", "cache", "database", "embedding", "function", "graph",
    "hashmap", "index", "json", "kernel", "lambda", "memory", "network", "optimizer",
    "parser", "query", "runtime", "schema", "thread", "unicode", "vector", "webhook",
    "yaml", "async", "batch", "cluster", "daemon", "encoder", "framework", "gateway",
    "handler", "interface", "journal", "kafka", "latency", "middleware", "namespace",
    "orchestrator", "pipeline", "queue", "replica", "shard", "token", "upstream",
    "validator", "worker", "proxy", "circuit", "breakpoint", "debugger", "profiler",
    "allocator", "garbage", "collector", "semaphore", "mutex", "channel", "buffer",
    "iterator", "closure", "trait", "generic", "lifetime", "borrow", "ownership",
    "reference", "pointer", "stack", "heap", "register", "instruction", "compiler",
    "linker", "loader", "assembler", "bytecode", "interpreter", "virtual", "machine",
    "container", "sandbox", "isolation", "process", "signal", "socket", "protocol",
    "handshake", "encryption", "certificate", "session", "cookie", "header", "payload",
    "request", "response", "endpoint", "route", "controller", "service", "repository",
    "migration", "transaction", "rollback", "commit", "branch", "merge", "conflict",
    "resolution", "deployment", "staging", "production", "monitoring", "alerting",
    "dashboard", "metric", "trace", "span", "context", "propagation", "sampling",
    "aggregate", "window", "partition", "offset", "consumer", "producer", "topic",
    "subscription", "notification", "webhook", "callback", "promise", "future", "stream",
    "backpressure", "throttle", "debounce", "retry", "timeout", "fallback", "circuit",
    "breaker", "bulkhead", "rate", "limiter", "load", "balancer", "health", "check",
    "discovery", "registry", "configuration", "feature", "flag", "experiment", "variant",
    "hypothesis", "inference", "gradient", "descent", "epoch", "batch", "layer", "neuron",
    "activation", "softmax", "attention", "transformer", "embedding", "tokenizer",
    "vocabulary", "corpus", "document", "sentence", "paragraph", "chapter", "section",
    "heading", "footnote", "citation", "bibliography", "appendix", "glossary",
    "sqlite", "postgres", "redis", "elasticsearch", "mongodb", "cassandra", "dynamodb",
    "kubernetes", "docker", "terraform", "ansible", "prometheus", "grafana", "datadog",
    "python", "rust", "typescript", "golang", "java", "kotlin", "swift", "ruby",
];

const MEMORY_TYPES: &[&str] = &[
    "debugging", "decision", "architecture", "preference",
    "fact", "pattern", "workflow", "observation",
];

/// Generate a random 384-dim unit-normalized vector.
pub fn random_unit_vector(rng: &mut StdRng) -> Vec<f32> {
    let mut v: Vec<f32> = (0..384).map(|_| rng.gen::<f32>() - 0.5).collect();
    let norm: f32 = v.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm > 0.0 {
        for x in &mut v {
            *x /= norm;
        }
    }
    v
}

/// Generate random content string of 50-150 words from the vocabulary.
pub fn random_content(rng: &mut StdRng) -> String {
    let word_count = rng.gen_range(50..=150);
    let words: Vec<&str> = (0..word_count)
        .map(|_| VOCAB[rng.gen_range(0..VOCAB.len())])
        .collect();
    words.join(" ")
}

/// Generate random metadata cycling through the 8 known types.
pub fn random_metadata(rng: &mut StdRng) -> serde_json::Value {
    let type_val = MEMORY_TYPES[rng.gen_range(0..MEMORY_TYPES.len())];
    let topic = VOCAB[rng.gen_range(0..VOCAB.len())];
    serde_json::json!({
        "type": type_val,
        "topic": topic,
    })
}

/// Seed an in-memory DB with N memories using insert_with_id (bypasses embedding + dedup).
/// Returns (Memori, Vec<id>, Vec<vector>).
pub fn seed_db(n: usize) -> (Memori, Vec<String>, Vec<Vec<f32>>) {
    let mut rng = StdRng::seed_from_u64(42);
    let db = Memori::open(":memory:").expect("failed to open in-memory DB");

    let mut ids = Vec::with_capacity(n);
    let mut vectors = Vec::with_capacity(n);

    let base_ts = 1700000000.0; // fixed base timestamp

    for i in 0..n {
        let id = uuid::Uuid::new_v4().to_string();
        let content = random_content(&mut rng);
        let vec = random_unit_vector(&mut rng);
        let meta = random_metadata(&mut rng);
        let ts = base_ts + (i as f64);

        db.insert_with_id(&id, &content, Some(&vec), Some(meta), ts, ts)
            .expect("seed insert failed");

        ids.push(id);
        vectors.push(vec);
    }

    (db, ids, vectors)
}

/// Generate a set of diverse text queries for search benchmarks.
pub fn text_queries() -> Vec<&'static str> {
    vec![
        "database query optimization",
        "memory allocation garbage collector",
        "kubernetes deployment monitoring",
        "rust ownership borrow checker",
        "sqlite fts5 full text search",
    ]
}
