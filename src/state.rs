//! State management for StreamViz
//! 
//! Handles ring buffers for widget data, allowing new connections
//! to receive historical data immediately.

use std::collections::{HashMap, VecDeque};
use std::sync::RwLock;
use serde::{Deserialize, Serialize};

/// Maximum points to keep per widget in the ring buffer
const DEFAULT_BUFFER_SIZE: usize = 1000;

/// A single data point with timestamp and value
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataPoint {
    pub timestamp: i64,  // Unix timestamp in milliseconds
    pub value: f64,
}

/// Ring buffer for a single widget's data
#[derive(Debug)]
pub struct WidgetBuffer {
    pub data: VecDeque<DataPoint>,
    pub max_size: usize,
}

impl WidgetBuffer {
    pub fn new(max_size: usize) -> Self {
        Self {
            data: VecDeque::with_capacity(max_size),
            max_size,
        }
    }

    pub fn push(&mut self, point: DataPoint) {
        if self.data.len() >= self.max_size {
            self.data.pop_front();
        }
        self.data.push_back(point);
    }

    pub fn get_all(&self) -> Vec<DataPoint> {
        self.data.iter().cloned().collect()
    }
    
    pub fn len(&self) -> usize {
        self.data.len()
    }
}

/// Manages all widget buffers and dashboard configuration
pub struct DataStore {
    /// Ring buffers for each widget, keyed by widget ID
    pub buffers: RwLock<HashMap<String, WidgetBuffer>>,
    /// Last known dashboard config (to send to new connections)
    pub last_config: RwLock<Option<String>>,
    /// Default buffer size for new widgets
    pub default_buffer_size: usize,
}

impl DataStore {
    pub fn new() -> Self {
        Self {
            buffers: RwLock::new(HashMap::new()),
            last_config: RwLock::new(None),
            default_buffer_size: DEFAULT_BUFFER_SIZE,
        }
    }

    /// Store a data point for a widget
    pub fn store_point(&self, widget_id: &str, timestamp: i64, value: f64) {
        let mut buffers = self.buffers.write().unwrap();
        let buffer = buffers
            .entry(widget_id.to_string())
            .or_insert_with(|| WidgetBuffer::new(self.default_buffer_size));
        buffer.push(DataPoint { timestamp, value });
    }

    /// Get all buffered data for a widget
    pub fn get_widget_history(&self, widget_id: &str) -> Option<Vec<DataPoint>> {
        let buffers = self.buffers.read().unwrap();
        buffers.get(widget_id).map(|b| b.get_all())
    }

    /// Get history for all widgets (for sending to new connections)
    pub fn get_all_history(&self) -> HashMap<String, Vec<DataPoint>> {
        let buffers = self.buffers.read().unwrap();
        buffers
            .iter()
            .map(|(id, buf)| (id.clone(), buf.get_all()))
            .collect()
    }

    /// Update the cached config
    pub fn set_config(&self, config: String) {
        let mut cfg = self.last_config.write().unwrap();
        *cfg = Some(config);
    }

    /// Get the cached config
    pub fn get_config(&self) -> Option<String> {
        let cfg = self.last_config.read().unwrap();
        cfg.clone()
    }
}

impl Default for DataStore {
    fn default() -> Self {
        Self::new()
    }
}
