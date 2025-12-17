# PathwayViz Production Roadmap

This document serves as a guide for future enhancements to make PathwayViz production-ready. It focuses on improving reliability, persistence, and observability without adding heavy external dependencies.

## 1. Core Package Enhancements

These improvements focus on making the single-instance experience robust and stable.

### A. Persistence & Recovery
The most critical requirement for production is ensuring data survives restarts and crashes.

*   **Enable Pathway Checkpointing**: Leverage Pathway's built-in engine persistence to save the state of aggregations and windows.
*   **Persistent Ring Buffers**: Save the Rust WebSocket server's in-memory ring buffers to disk (JSON or SQLite) so new clients can still see historical context after a restart.
*   **Stable Kafka Consumer Groups**: Use fixed consumer group IDs instead of random ones to ensure the pipeline resumes from the last known offset after a crash.

### B. Networking & Reliability
*   **WebSocket Heartbeats**: Implement standard ping/pong frames to detect and prune "zombie" connections, preventing memory leaks and stale state.
*   **Remove redundant polling**: Replace the periodic 2-second config broadcast with a more efficient "on-connect" delivery and "on-change" broadcast.
*   **Configurable Backpressure**: Allow users to tune the broadcast channel capacity to prevent data loss for slow consumers in high-throughput environments.

### C. Observability
*   **Health Endpoints**: Add a `/health` REST endpoint that returns the current status of the pipeline, connection counts, and data flow metrics.
*   **Logging Improvements**: Replace panics (`.unwrap()`) with graceful error handling and structured logging to help debug issues in production environments.

---

## 2. Advanced Scaling (Distributed Architecture)

For very large deployments (>10k concurrent clients or multiple servers), PathwayViz can be extended to use a distributed backend like **Redis**.

*   **Redis Streams**: Replace local ring buffers with Redis Streams for shared history across multiple instances.
*   **Redis Pub/Sub**: Sync live data updates across multiple WebSocket server nodes.
*   **Stateless Servers**: Making the WebSocket servers stateless allows them to sit behind a standard load balancer.

---

## 3. Implementation Guide

### Enable Pathway Persistence
**Priority:** High | **Effort:** Minimal

1.  Add `persistence_dir` to `WidgetServer`.
2.  Pass a `pw.persistence.Config` to `pw.run()`.
3.  Ensure Kafka readers have a stable `name` for recovery.

```python
# Implementation snippet
persistence_backend = pw.persistence.Backend.filesystem("./data/state")
pw.run(persistence_config=pw.persistence.Config(persistence_backend))
```

### Stable Kafka Consumer Groups
**Priority:** High | **Effort:** Minimal

Avoid random group IDs in production. Use a stable ID based on the hostname or an environment variable.

```python
# Recommended pattern
group_id = os.getenv("PATHWAYVIZ_GROUP_ID", f"pv-{socket.gethostname()}")
```

### Persist Ring Buffers to Disk
**Priority:** High | **Effort:** Moderate

Use `serde` in Rust to save/load the `DataStore` to a JSON file on startup and shutdown.

```rust
// Implementation snippet (state.rs)
pub fn save_to_file(&self, path: &Path) -> Result<(), Error> {
    let state = self.get_serializable_state();
    let json = serde_json::to_string(&state)?;
    fs::write(path, json)?;
    Ok(())
}
```

### WebSocket Heartbeats
**Priority:** Medium | **Effort:** Small

Use `tokio::time::interval` in the `handle_socket` loop to send pings and monitor for pongs.

```rust
// Implementation snippet (server.rs)
let mut ping_interval = interval(Duration::from_secs(30));
loop {
    tokio::select! {
        _ = ping_interval.tick() => {
            socket.send(Message::Ping(vec![])).await?;
        }
        // ... other handlers
    }
}
```

### Health Endpoint
**Priority:** Medium | **Effort:** Small

Expose internal metrics (client count, buffer sizes) via a JSON endpoint.

```rust
// Implementation snippet (server.rs)
async fn health_handler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    Json(json!({
        "status": "healthy",
        "clients": state.client_count(),
        "widgets": state.widget_count()
    }))
}
```

---

## 4. Future Package Checklist

- [ ] Support for local asset bundling (offline/air-gapped mode)
- [ ] Customizable theme injection (CSS variables)
- [ ] Support for additional chart types (Bar, Heatmap)
- [ ] Automatic Docker image baking for Python pipelines
- [ ] Prometheus metrics exporter

