use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use std::sync::{Arc, Mutex, OnceLock};
use std::thread;
use tokio::sync::broadcast;

mod generator;
mod server;

/// Global state to hold the broadcast sender and runtime handle
static GLOBAL_STATE: OnceLock<Arc<GlobalState>> = OnceLock::new();

struct GlobalState {
    tx: broadcast::Sender<String>,
    server_handle: Mutex<Option<thread::JoinHandle<()>>>,
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
        })
    });

    let mut handle_guard = state.server_handle.lock().unwrap();
    if handle_guard.is_some() {
        return Err(PyRuntimeError::new_err("Server is already running"));
    }

    let tx = state.tx.clone();
    
    let handle = thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(async {
            server::start_server(port, tx).await;
        });
    });

    *handle_guard = Some(handle);
    println!("StreamViz server started on http://localhost:{}", port);
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

/// Start the demo mode with auto-generated random data
#[pyfunction]
fn start_demo(port: u16) -> PyResult<()> {
    start_server(port)?;

    let state = GLOBAL_STATE.get().unwrap();
    generator::spawn_demo_generator(state.tx.clone());

    // Block forever in demo mode (like original behavior)
    loop {
        thread::sleep(std::time::Duration::from_secs(60));
    }
}

/// Start the dashboard (legacy function, now an alias for start_demo)
#[pyfunction]
fn start_dashboard(port: u16) -> PyResult<()> {
    start_demo(port)
}

#[pymodule]
fn _stream_viz(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(start_server, m)?)?;
    m.add_function(wrap_pyfunction!(send_data, m)?)?;
    m.add_function(wrap_pyfunction!(send_point, m)?)?;
    m.add_function(wrap_pyfunction!(start_demo, m)?)?;
    m.add_function(wrap_pyfunction!(start_dashboard, m)?)?;
    Ok(())
}
