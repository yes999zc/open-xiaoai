use std::future::Future;
use std::process::Stdio;
use std::sync::{Arc, LazyLock};
use std::time::Duration;
use tokio::io::AsyncReadExt;
use tokio::process::{Child, Command};
use tokio::sync::Mutex;
use tokio::task::JoinHandle;
use tokio::time::timeout;

use crate::base::AppError;

use super::config::{AudioConfig, AUDIO_CONFIG};

#[derive(PartialEq)]
enum State {
    Idle,
    Recording,
}

const A113_CAPTURE_BITS_PER_SAMPLE: u16 = 32;

pub struct AudioRecorder {
    state: Arc<Mutex<State>>,
    arecord_thread: Arc<Mutex<Option<Child>>>,
    read_thread: Arc<Mutex<Option<JoinHandle<()>>>>,
}

static INSTANCE: LazyLock<AudioRecorder> = LazyLock::new(AudioRecorder::new);

impl AudioRecorder {
    fn new() -> Self {
        Self {
            state: Arc::new(Mutex::new(State::Idle)),
            arecord_thread: Arc::new(Mutex::new(None)),
            read_thread: Arc::new(Mutex::new(None)),
        }
    }

    pub fn instance() -> &'static Self {
        &INSTANCE
    }

    pub async fn stop_recording(&self) -> Result<(), AppError> {
        let mut state = self.state.lock().await;
        if *state == State::Idle {
            return Ok(());
        }

        if let Some(read_thread) = self.read_thread.lock().await.take() {
            read_thread.abort();
        }

        if let Some(mut arecord_thread) = self.arecord_thread.lock().await.take() {
            let _ = timeout(Duration::from_millis(100), arecord_thread.kill()).await;
        }

        *state = State::Idle;
        Ok(())
    }

    pub async fn start_recording<F, Fut>(
        &self,
        on_stream: F,
        config: Option<AudioConfig>,
    ) -> Result<(), AppError>
    where
        F: Fn(Vec<u8>) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = Result<(), AppError>> + Send + 'static,
    {
        let mut state = self.state.lock().await;
        if *state == State::Recording {
            return Ok(());
        }

        let requested_config = config.unwrap_or_else(|| (*AUDIO_CONFIG).clone());
        let capture_config = capture_config_for_recording(&requested_config);
        let mut arecord_thread = spawn_arecord(&capture_config)?;

        let mut stdout = arecord_thread.stdout.take().unwrap();
        let read_thread = tokio::spawn(async move {
            let bytes_per_sample = (capture_config.bits_per_sample.max(8) / 8) as usize;
            let bytes_per_frame = bytes_per_sample * capture_config.channels.max(1) as usize;
            let target_frames = capture_config.buffer_size.max(1) as usize;
            let read_frames = capture_config.period_size.max(1) as usize;
            let target_size = target_frames * bytes_per_frame;
            let read_size = read_frames * bytes_per_frame;

            let mut accumulated_data = Vec::with_capacity(target_size * 2);
            let mut buffer = vec![0u8; read_size];
            let mut starved = 0u32;

            loop {
                match timeout(Duration::from_millis(500), stdout.read(&mut buffer)).await {
                    Ok(Ok(size)) if size > 0 => {
                        starved = 0;
                        accumulated_data.extend_from_slice(&buffer[..size]);
                        while accumulated_data.len() >= target_size {
                            let data_to_send =
                                accumulated_data.drain(..target_size).collect::<Vec<u8>>();
                            let data_to_send =
                                transform_stream_chunk(data_to_send, &requested_config, &capture_config);
                            if !data_to_send.is_empty() {
                                let _ = on_stream(data_to_send).await;
                            }
                        }
                    }
                    Ok(Ok(_)) => break,      // arecord exited: nothing left to read
                    Ok(Err(e)) => {
                        eprintln!("[record] read error: {}", e);
                        break;
                    }
                    Err(_) => {
                        // A 500 ms gap is a scheduling hiccup, not the end of the
                        // session. The old code broke out here, so one stall left
                        // the assistant deaf until it was restarted.
                        starved += 1;
                        if starved % 4 == 0 {
                            eprintln!("[record] no audio for {} s", starved / 2);
                        }
                        if starved >= 20 {
                            eprintln!("[record] arecord stalled 10 s, giving up");
                            break;
                        }
                    }
                }
            }

            let _ = AudioRecorder::instance().stop_recording().await;
        });

        self.arecord_thread.lock().await.replace(arecord_thread);
        self.read_thread.lock().await.replace(read_thread);

        *state = State::Recording;
        Ok(())
    }
}

fn capture_config_for_recording(requested: &AudioConfig) -> AudioConfig {
    let mut capture = requested.clone();
    if requested.bits_per_sample == 16 {
        capture.bits_per_sample = A113_CAPTURE_BITS_PER_SAMPLE;
    }
    capture
}

fn transform_stream_chunk(
    chunk: Vec<u8>,
    requested: &AudioConfig,
    capture: &AudioConfig,
) -> Vec<u8> {
    if requested.bits_per_sample != 16 || capture.bits_per_sample != A113_CAPTURE_BITS_PER_SAMPLE {
        return chunk;
    }
    convert_a113_s32_to_s16(
        &chunk,
        capture.channels as usize,
        capture.mic_shift,
        capture.ref_shift,
    )
}

/// Number of PDM microphones on the 8-channel array; everything above is reference.
const A113_MIC_CHANNELS: usize = 6;

/// Per-channel scale for the S32_LE capture.
///
/// The two halves of the stream do not share a full scale, and both of them move
/// with the box's `mysoftvol`:
///   ch0-5  PDM microphones      peak 4.4e7 at 70% volume, 6.8e7 at 80%
///   ch6-7  playback reference   peak 4.9e8 at 70%, 8.6e8 at 80%
///
/// Fixed shifts of 8 / 13 were calibrated at 110 (~43%) and clipped **48-56% of
/// the mic samples** at 70-80%: half the waveform became a square wave, so the
/// echo canceller fell to 1.6 dB and barge-in stopped working exactly when the
/// music got loud. 12 / 16 keep the full range in hand (mic to 1.3e8, ref to
/// 2.1e9) and measured 11 dB on the same recording.
fn a113_channel_shift(channels: usize, index: usize, mic_shift: u32, ref_shift: u32) -> u32 {
    if channels > A113_MIC_CHANNELS && index % channels >= A113_MIC_CHANNELS {
        ref_shift
    } else {
        mic_shift
    }
}

fn convert_a113_s32_to_s16(chunk: &[u8], channels: usize, mic_shift: u32, ref_shift: u32) -> Vec<u8> {
    if chunk.len() % 4 != 0 {
        return Vec::new();
    }

    let channels = channels.max(1);
    let frame_count = chunk.len() / 4;
    let mut out = vec![0u8; frame_count * 2];

    for frame in 0..frame_count {
        let base = frame * 4;
        let sample = i32::from_le_bytes([
            chunk[base],
            chunk[base + 1],
            chunk[base + 2],
            chunk[base + 3],
        ]);
        // The shift is a headroom decision, not a bit-depth one: the same
        // channels get louder as `mysoftvol` goes up, so it must not clip at 80%.
        let shift = a113_channel_shift(channels, frame, mic_shift, ref_shift);
        let mapped = (sample >> shift).clamp(i16::MIN as i32, i16::MAX as i32) as i16;
        let out_base = frame * 2;
        out[out_base..out_base + 2].copy_from_slice(&mapped.to_le_bytes());
    }

    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn samples(v: &[i32], channels: usize) -> Vec<i16> {
        let mut bytes = Vec::new();
        for s in v {
            bytes.extend_from_slice(&s.to_le_bytes());
        }
        convert_a113_s32_to_s16(&bytes, channels, 12, 16)
            .chunks_exact(2)
            .map(|c| i16::from_le_bytes([c[0], c[1]]))
            .collect()
    }

    #[test]
    fn shifts_microphones_with_headroom() {
        // 2^27 is what a mic channel reaches at ~80% volume; >>8 would clamp it
        assert_eq!(samples(&[1 << 26, -(1 << 25)], 1), vec![1 << 14, -(1 << 13)]);
    }

    #[test]
    fn loud_microphone_does_not_clip() {
        // 6.8e7 (measured peak at mysoftvol 204) must fit after the shift
        let out = samples(&[68_000_000, -68_000_000], 1);
        assert!(out[0] < i16::MAX && out[1] > i16::MIN, "{out:?}");
    }

    #[test]
    fn reference_channels_keep_their_own_scale() {
        // 8 channels: two frames, ch6/7 at 2^30 (measured 8.6e8 at 80%)
        let frame = [1 << 22, 1 << 22, 1 << 22, 1 << 22, 1 << 22, 1 << 22, 1 << 30, 1 << 30];
        let mut v = Vec::new();
        v.extend_from_slice(&frame);
        v.extend_from_slice(&frame);
        let out = samples(&v, 8);
        assert_eq!(&out[..6], &[1 << 10, 1 << 10, 1 << 10, 1 << 10, 1 << 10, 1 << 10]); // 2^22 >> 12
        assert_eq!(&out[6..8], &[1 << 14, 1 << 14]); // 2^30 >> 16
    }
}

fn spawn_arecord(config: &AudioConfig) -> Result<Child, AppError> {
    let child = Command::new("arecord")
        .args([
            "--quiet",
            "-t",
            "raw",
            "-D",
            &config.pcm,
            "-f",
            &format!("S{}_LE", config.bits_per_sample),
            "-r",
            &config.sample_rate.to_string(),
            "-c",
            &config.channels.to_string(),
            "--buffer-size",
            &config.buffer_size.to_string(),
            "--period-size",
            &config.period_size.to_string(),
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()?;
    Ok(child)
}
