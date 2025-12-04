use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::{Html, IntoResponse},
    routing::get,
    Router,
};
use serde::Deserialize;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::sync::broadcast;

use crate::state::DataStore;

pub struct AppState {
    pub tx: broadcast::Sender<String>,
    pub data_store: DataStore,
}

// Embed the frontend HTML directly in the binary - no external files needed!
const FRONTEND_HTML: &str = include_str!("../frontend/index.html");

/// Message types we might receive from Python
#[derive(Debug, Deserialize)]
struct IncomingMessage {
    #[serde(rename = "type")]
    msg_type: String,
    #[serde(default)]
    widget: Option<String>,
    #[serde(default)]
    metric: Option<String>, // Legacy field name
    #[serde(default)]
    timestamp: Option<i64>,
    #[serde(default)]
    value: Option<f64>,
}

pub async fn start_server(port: u16, tx: broadcast::Sender<String>) {
    let app_state = Arc::new(AppState {
        tx: tx.clone(),
        data_store: DataStore::new(),
    });

    // Spawn a background task that processes all messages
    // - Caches config messages
    // - Stores data points in ring buffers
    let store_state = Arc::clone(&app_state);
    let mut store_rx = tx.subscribe();
    tokio::spawn(async move {
        while let Ok(msg) = store_rx.recv().await {
            // Try to parse the message
            if let Ok(parsed) = serde_json::from_str::<IncomingMessage>(&msg) {
                match parsed.msg_type.as_str() {
                    "config" => {
                        store_state.data_store.set_config(msg);
                    }
                    "data" => {
                        // Get widget ID (support both "widget" and legacy "metric")
                        let widget_id = parsed
                            .widget
                            .or(parsed.metric)
                            .unwrap_or_default();

                        if let (Some(ts), Some(val)) = (parsed.timestamp, parsed.value) {
                            store_state.data_store.store_point(&widget_id, ts, val);
                        }
                    }
                    _ => {}
                }
            }
        }
    });

    let app = Router::new()
        .route("/", get(serve_frontend))
        .route("/ws", get(ws_handler))
        .with_state(app_state);

    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    println!("Listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn serve_frontend() -> impl IntoResponse {
    Html(FRONTEND_HTML)
}

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<Arc<AppState>>,
) -> impl IntoResponse {
    ws.on_upgrade(|socket| handle_socket(socket, state))
}

async fn handle_socket(mut socket: WebSocket, state: Arc<AppState>) {
    // 1. Send the cached config first (so client knows what widgets exist)
    if let Some(config) = state.data_store.get_config() {
        if socket.send(Message::Text(config)).await.is_err() {
            return;
        }
    }

    // 2. Send history for all widgets
    let all_history = state.data_store.get_all_history();
    if !all_history.is_empty() {
        let history_msg = serde_json::json!({
            "type": "history",
            "widgets": all_history.iter().map(|(id, points)| {
                serde_json::json!({
                    "widget": id,
                    "data": points.iter().map(|p| (p.timestamp, p.value)).collect::<Vec<_>>()
                })
            }).collect::<Vec<_>>()
        });

        if socket
            .send(Message::Text(history_msg.to_string()))
            .await
            .is_err()
        {
            return;
        }
    }

    // 3. Subscribe to live updates
    let mut rx = state.tx.subscribe();

    while let Ok(msg) = rx.recv().await {
        if socket.send(Message::Text(msg)).await.is_err() {
            break;
        }
    }
}
