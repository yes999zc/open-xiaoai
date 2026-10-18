use std::process::Stdio;
use std::sync::{Arc, LazyLock};
use std::time::Duration;
use tokio::io::AsyncWriteExt;
use tokio::process::{Child, ChildStdin, Command};
use tokio::sync::{mpsc, Mutex};
use tokio::task::JoinHandle;
use tokio::time::timeout;

use crate::base::AppError;

use super::config::{AudioConfig, AUDIO_CONFIG};

pub struct AudioPlayer {
    aplay_thread: Arc<Mutex<Option<Child>>>,
    write_thread: Arc<Mutex<Option<ChildStdin>>>,
    sender: Arc<Mutex<Option<mpsc::Sender<Vec<u8>>>>>,
    player_task: Arc<Mutex<Option<JoinHandle<()>>>>,
}

static INSTANCE: LazyLock<AudioPlayer> = LazyLock::new(AudioPlayer::new);

impl AudioPlayer {
    fn new() -> Self {
        Self {
            aplay_thread: Arc::new(Mutex::new(None)),
            write_thread: Arc::new(Mutex::new(None)),
            sender: Arc::new(Mutex::new(None)),
            player_task: Arc::new(Mutex::new(None)),
        }
    }

    pub fn instance() -> &'static Self {
        &INSTANCE
    }

    pub async fn stop(&self) -> Result<(), AppError> {
        let mut sender_guard = self.sender.lock().await;
        if let Some(sender) = sender_guard.take() {
            drop(sender);
        }

        if let Some(task) = self.player_task.lock().await.take() {
            task.abort();
        }

        if let Some(mut write_thread) = self.write_thread.lock().await.take() {
            let _ = timeout(Duration::from_millis(100), write_thread.shutdown()).await;
            drop(write_thread);
        }

        if let Some(mut aplay_thread) = self.aplay_thread.lock().await.take() {
            let _ = aplay_thread.kill().await;
        }

        Ok(())
    }

    pub async fn start(&self, config: Option<AudioConfig>) -> Result<(), AppError> {
        let is_started = self.sender.lock().await.is_some();
        if is_started {
            self.stop().await?;
        }

        let config = config.unwrap_or_else(|| (*AUDIO_CONFIG).clone());

        // honor the requested PCM: the default route goes through the vendor's
        // DTS processor, which level-matches everything we send. Naming a plain
        // PCM (e.g. plug:dmixer) is the only way out of that chain without a
        // firmware change. "noop" is the capture alias the config defaults to,
        // so treat it as "no -D".
        let mut args: Vec<String> = vec![
            "--quiet".into(),
            "-t".into(),
            "raw".into(),
            "-f".into(),
            format!("S{}_LE", config.bits_per_sample),
            "-r".into(),
            config.sample_rate.to_string(),
            "-c".into(),
            config.channels.to_string(),
            "--buffer-size".into(),
            config.buffer_size.to_string(),
            "--period-size".into(),
            config.period_size.to_string(),
        ];
        if !config.pcm.is_empty() && config.pcm != "noop" {
            args.push("-D".into());
            args.push(config.pcm.clone());
        }
        args.push("-".into());

        let mut aplay_thread = Command::new("aplay")
            .args(&args)
            .stdin(Stdio::piped())
            .spawn()?;

        let stdin = aplay_thread.stdin.take().unwrap();
        self.aplay_thread.lock().await.replace(aplay_thread);
        self.write_thread.lock().await.replace(stdin);

        // 4 chunks = 400 ms of cushion. A deep queue lets the server run seconds
        // ahead of the speaker, which is what starved aplay: it consumed at
        // 1.0x while the timer-fed stream arrived at 1.04x.
        let (tx, mut rx) = mpsc::channel::<Vec<u8>>(4);

        let write_thread_clone = self.write_thread.clone();
        let player_task = tokio::spawn(async move {
            // arrival timeline: one line per second of audio shows whether chunks
            // reach aplay evenly or in bursts
            let t0 = std::time::Instant::now();
            let mut idx: u64 = 0;
            while let Some(bytes) = rx.recv().await {
                idx += 1;
                if idx % 10 == 1 {
                    eprintln!("[aplay] chunk {} at {} ms", idx, t0.elapsed().as_millis());
                }
                let mut write_guard = write_thread_clone.lock().await;
                if let Some(write_thread) = write_guard.as_mut() {
                    // silent drops here are invisible from the server: a chunk
                    // that blocks for 100 ms is thrown away and the sentence
                    // loses a piece. Log both outcomes so the gap is measurable.
                    let t0 = std::time::Instant::now();
                    match timeout(Duration::from_millis(500), write_thread.write_all(&bytes)).await {
                        Ok(Ok(())) => {
                            let ms = t0.elapsed().as_millis();
                            if ms >= 80 {
                                eprintln!("[aplay] slow write {} ms ({} bytes)", ms, bytes.len());
                            }
                        }
                        Ok(Err(e)) => eprintln!("[aplay] write error: {}", e),
                        Err(_) => eprintln!(
                            "[aplay] WRITE TIMEOUT dropped {} bytes (aplay blocked 500 ms)",
                            bytes.len()
                        ),
                    }
                } else {
                    break;
                }
            }
        });

        self.player_task.lock().await.replace(player_task);
        self.sender.lock().await.replace(tx);

        Ok(())
    }

    pub async fn play(&self, bytes: Vec<u8>) -> Result<(), AppError> {
        let sender_guard = self.sender.lock().await;
        if let Some(sender) = sender_guard.as_ref() {
            // the channel holds 50 chunks; if it is full the websocket reader is
            // blocked, which shows up on the server as a slow send
            let t0 = std::time::Instant::now();
            let n = bytes.len();
            sender.send(bytes).await?;
            let ms = t0.elapsed().as_millis();
            if ms >= 80 {
                eprintln!("[play] queue full, enqueue blocked {} ms ({} bytes)", ms, n);
            }
        }

        Ok(())
    }
}
