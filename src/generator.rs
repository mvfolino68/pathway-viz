use tokio::sync::broadcast;
use tokio::time::{self, Duration};
use serde_json::json;
use rand::Rng;
use std::time::{SystemTime, UNIX_EPOCH};

/// Spawns a background task that generates demo data
/// This runs in a separate tokio task within the server's runtime
pub fn spawn_demo_generator(tx: broadcast::Sender<String>) {
    std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            let mut interval = time::interval(Duration::from_millis(50));
            loop {
                interval.tick().await;

                let timestamp = SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_millis() as u64;

                let value: f64 = rand::thread_rng().gen_range(0.0..100.0);

                let data = json!({
                    "timestamp": timestamp,
                    "value": value
                });

                // Ignore errors (no receivers)
                let _ = tx.send(data.to_string());
            }
        });
    });
}
