use serde::{Deserialize, Serialize};
use std::future::Future;
use tokio::task::JoinHandle;
use tokio::time::{sleep, Duration};

use crate::base::AppError;
use crate::utils::shell::run_shell;

#[derive(Debug, Serialize, Deserialize, PartialEq, Clone)]
pub enum PlayingMonitorEvent {
    Playing,
    Paused,
    Idle,
}

pub struct PlayingMonitor {
    task_holder: Option<JoinHandle<()>>,
}

impl Default for PlayingMonitor {
    fn default() -> Self {
        Self::new()
    }
}

impl PlayingMonitor {
    pub fn new() -> Self {
        Self { task_holder: None }
    }

    pub async fn start<F, Fut>(&mut self, on_update: F)
    where
        F: Fn(PlayingMonitorEvent) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = Result<(), AppError>> + Send + 'static,
    {
        let monitor = tokio::spawn(async move {
            let _ = PlayingMonitor::start_monitor(on_update).await;
        });

        if let Some(old_task) = self.task_holder.replace(monitor) {
            println!("Aborting old playing monitor task");
            old_task.abort();
        };
    }

    pub async fn stop(&mut self) {
        if let Some(handle) = self.task_holder.take() {
            handle.abort();
        }
    }

    async fn start_monitor<F, Fut>(on_update: F) -> Result<(), AppError>
    where
        F: Fn(PlayingMonitorEvent) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = Result<(), AppError>> + Send + 'static,
    {
        // Polling spawns a shell + mphelper each round. At 10 ms that is 100
        // processes per second on a 4-core A53, which steals time from the
        // audio path. Playback state does not need sub-second resolution.
        let poll_ms = std::env::var("OPEN_XIAOAI_PLAYING_POLL_MS")
            .ok()
            .and_then(|v| v.parse::<u64>().ok())
            .unwrap_or(300)
            .max(100);

        let mut last_status = PlayingMonitorEvent::Idle;
        loop {
            let res = run_shell("mphelper mute_stat").await?;
            // `contains("1")` treated any output carrying a 1 as playing: a
            // "0" with a stray 1 elsewhere, or a future "10", flipped the state
            // and the session stopped believing the speaker was silent.
            let status = match res.stdout.split_whitespace().next().and_then(|t| t.parse::<u8>().ok()) {
                Some(1) => PlayingMonitorEvent::Playing,
                Some(2) => PlayingMonitorEvent::Paused,
                Some(0) => PlayingMonitorEvent::Idle,
                other => {
                    // unknown code: say so once instead of guessing a state
                    println!("unexpected mute_stat output {:?} ({:?})", res.stdout, other);
                    PlayingMonitorEvent::Idle
                }
            };

            if last_status != status {
                last_status = status.clone();
                let _ = on_update(status).await;
            }

            sleep(Duration::from_millis(poll_ms)).await;
        }
    }
}
