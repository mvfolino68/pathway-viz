use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use tokio::sync::broadcast;
use tokio::sync::oneshot;

mod server;
mod state;

/// Global state to hold the broadcast sender and runtime handle
static GLOBAL_STATE: OnceLock<Arc<GlobalState>> = OnceLock::new();

struct GlobalState {
    tx: broadcast::Sender<String>,
    server_handle: Mutex<Option<thread::JoinHandle<()>>>,
    shutdown_tx: Mutex<Option<oneshot::Sender<()>>>,
}

/// Start the dashboard server in a background thread
/// Returns immediately so Python can continue sending data
#[pyfunction]
fn start_server(port: u16) -> PyResult<()> {
    let state = GLOBAL_STATE.get_or_init(|| {
        let (tx, _) = broadcast::channel::<String>(1000);
        Arc::new(GlobalState {
            tx,
            server_handle: Mutex::new(None),
            shutdown_tx: Mutex::new(None),
        })
    });

    let mut handle_guard = state.server_handle.lock().unwrap();
    if handle_guard.is_some() {
        return Err(PyRuntimeError::new_err("Server is already running"));
    }

    let tx = state.tx.clone();
    let (shutdown_tx, shutdown_rx) = oneshot::channel::<()>();
    {
        let mut shutdown_guard = state.shutdown_tx.lock().unwrap();
        *shutdown_guard = Some(shutdown_tx);
    }

    let handle = thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            server::start_server(port, tx, shutdown_rx).await;
        });
    });

    *handle_guard = Some(handle);
    println!("PathwayViz server started on http://localhost:{}", port);
    Ok(())
}

#[pyfunction]
fn stop_server() -> PyResult<()> {
    let state = GLOBAL_STATE
        .get()
        .ok_or_else(|| PyRuntimeError::new_err("Server not started"))?;

    let shutdown = {
        let mut guard = state.shutdown_tx.lock().unwrap();
        guard.take()
    };
    if let Some(tx) = shutdown {
        let _ = tx.send(());
    }

    let handle = {
        let mut guard = state.server_handle.lock().unwrap();
        guard.take()
    };
    if let Some(h) = handle {
        let _ = h.join();
    }

    Ok(())
}

/// Send data to all connected WebSocket clients
/// Data should be a JSON string or will be converted to JSON
#[pyfunction]
fn send_data(data: &str) -> PyResult<()> {
    let state = GLOBAL_STATE.get()
        .ok_or_else(|| PyRuntimeError::new_err("Server not started. Call start_server() first."))?;

    // Ignore send errors (no receivers connected yet)
    let _ = state.tx.send(data.to_string());
    Ok(())
}

/// Send a data point with timestamp and value (convenience function)
#[pyfunction]
fn send_point(timestamp: u64, value: f64) -> PyResult<()> {
    let data = serde_json::json!({
        "timestamp": timestamp,
        "value": value
    });
    send_data(&data.to_string())
}

#[pymodule]
fn _pathway_viz(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(start_server, m)?)?;
    m.add_function(wrap_pyfunction!(stop_server, m)?)?;
    m.add_function(wrap_pyfunction!(send_data, m)?)?;
    m.add_function(wrap_pyfunction!(send_point, m)?)?;
    Ok(())
}
