// Hardware key monitor for the XiaoAi keypad.
//
// The vendor keypad shows up as an evdev device named "adc_keypad". We only
// read it (no EVIOCGRAB), so the stock firmware keeps handling volume keys
// exactly as before while the server gets to see every press.
use std::future::Future;
use std::path::PathBuf;
use std::sync::Arc;

use serde::{Deserialize, Serialize};
use tokio::io::AsyncReadExt;
use tokio::task::JoinHandle;

use crate::base::AppError;

#[derive(Debug, Serialize, Deserialize)]
pub struct KeyEvent {
    pub code: u16,
    pub value: i32,
}

pub struct KeyMonitor {
    task_holder: Option<JoinHandle<()>>,
}

impl Default for KeyMonitor {
    fn default() -> Self {
        Self::new()
    }
}

impl KeyMonitor {
    pub fn new() -> Self {
        Self { task_holder: None }
    }

    pub async fn start<F, Fut>(&mut self, on_update: F)
    where
        F: Fn(KeyEvent) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = Result<(), AppError>> + Send + 'static,
    {
        let Some(path) = find_keypad_device() else {
            eprintln!("no keypad device found, key events disabled");
            return;
        };
        println!("listening for keys on {}", path.display());

        let on_update = Arc::new(on_update);
        let task = tokio::spawn(async move {
            let mut file = match tokio::fs::File::open(&path).await {
                Ok(f) => f,
                Err(e) => {
                    eprintln!("cannot open {}: {}", path.display(), e);
                    return;
                }
            };

            // struct input_event is 16 bytes on 32-bit ARM and 24 bytes on
            // 64-bit; the device runs 32-bit userspace, but stay portable.
            let event_size = if cfg!(target_pointer_width = "64") { 24 } else { 16 };
            let mut buf = vec![0u8; event_size];

            loop {
                if file.read_exact(&mut buf).await.is_err() {
                    break;
                }
                let (type_, code, value) = parse_event(&buf);
                if type_ != 1 {
                    continue; // EV_KEY only
                }
                let _ = on_update(KeyEvent { code, value }).await;
            }
        });

        if let Some(old) = self.task_holder.replace(task) {
            old.abort();
        }
    }

    pub async fn stop(&mut self) {
        if let Some(handle) = self.task_holder.take() {
            handle.abort();
        }
    }
}

fn parse_event(buf: &[u8]) -> (u16, u16, i32) {
    // timeval occupies the first 8 bytes on 32-bit, 16 on 64-bit.
    let base = buf.len() - 8;
    let type_ = u16::from_le_bytes([buf[base], buf[base + 1]]);
    let code = u16::from_le_bytes([buf[base + 2], buf[base + 3]]);
    let value = i32::from_le_bytes([buf[base + 4], buf[base + 5], buf[base + 6], buf[base + 7]]);
    (type_, code, value)
}

/// Read /proc/bus/input/devices and return the event node of "adc_keypad".
fn find_keypad_device() -> Option<PathBuf> {
    let table = std::fs::read_to_string("/proc/bus/input/devices").ok()?;
    let mut matched = false;
    for line in table.lines() {
        if line.starts_with("N: Name=") {
            matched = line.contains("adc_keypad");
            continue;
        }
        if matched && line.starts_with("H: Handlers=") {
            for token in line["H: Handlers=".len()..].split_whitespace() {
                if token.starts_with("event") {
                    return Some(PathBuf::from("/dev/input").join(token));
                }
            }
        }
        if line.trim().is_empty() {
            matched = false;
        }
    }
    None
}
