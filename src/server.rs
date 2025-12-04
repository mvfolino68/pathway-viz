use axum::{
    extract::{ws::{Message, WebSocket, WebSocketUpgrade}, State},
    response::{Html, IntoResponse},
    routing::get,
    Router,
};
use tokio::sync::{broadcast, RwLock};
use std::net::SocketAddr;
use std::sync::Arc;

pub struct AppState {
    pub tx: broadcast::Sender<String>,
    /// Stores the last config message to send to new connections
    pub last_config: RwLock<Option<String>>,
}

// Embed the frontend HTML directly in the binary - no external files needed!
const FRONTEND_HTML: &str = include_str!("../frontend/index.html");

pub async fn start_server(port: u16, tx: broadcast::Sender<String>) {
    let app_state = Arc::new(AppState {
        tx: tx.clone(),
        last_config: RwLock::new(None),
    });

    // Spawn a background task that listens for config messages and caches them
    // This ensures config sent before any WebSocket connects is still captured
    let config_state = Arc::clone(&app_state);
    let mut config_rx = tx.subscribe();
    tokio::spawn(async move {
        while let Ok(msg) = config_rx.recv().await {
            if msg.contains("\"type\":\"config\"") {
                let mut config = config_state.last_config.write().await;
                *config = Some(msg);
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
    // Send the last config to new connections immediately
    {
        let config = state.last_config.read().await;
        if let Some(ref cfg) = *config {
            if socket.send(Message::Text(cfg.clone())).await.is_err() {
                return;
            }
        }
    }

    let mut rx = state.tx.subscribe();

    while let Ok(msg) = rx.recv().await {
        // Also cache config here as backup (in case background task missed it)
        if msg.contains("\"type\":\"config\"") {
            let mut config = state.last_config.write().await;
            *config = Some(msg.clone());
        }
        
        if socket.send(Message::Text(msg)).await.is_err() {
            break;
        }
    }
}
