#[cfg(feature = "embeddings")]
mod inner {
    use std::sync::OnceLock;

    use fastembed::{EmbeddingModel, InitOptions, TextEmbedding};

    static MODEL: OnceLock<TextEmbedding> = OnceLock::new();

    fn get_model() -> &'static TextEmbedding {
        MODEL.get_or_init(|| {
            let options = InitOptions::new(EmbeddingModel::AllMiniLML6V2)
                .with_show_download_progress(false);
            TextEmbedding::try_new(options)
                .expect("failed to initialize embedding model")
        })
    }

    pub fn embed_text(text: &str) -> Vec<f32> {
        let model = get_model();
        let results = model.embed(vec![text], None).expect("embedding failed");
        results.into_iter().next().unwrap()
    }

    pub fn embed_batch(texts: &[&str]) -> Vec<Vec<f32>> {
        let model = get_model();
        model.embed(texts.to_vec(), None).expect("embedding failed")
    }
}

#[cfg(feature = "embeddings")]
pub use inner::*;
