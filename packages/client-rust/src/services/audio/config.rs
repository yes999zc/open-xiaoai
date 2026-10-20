use std::sync::LazyLock;

use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct AudioConfig {
    pub pcm: String,
    pub channels: u16,
    pub bits_per_sample: u16,
    pub sample_rate: u32,
    pub period_size: u32,
    pub buffer_size: u32,
    /// Right shift that maps ch0-5 (PDM mics) from S32 to i16.
    /// Default 12: leaves ~24 dB of headroom so 70-80% playback volume does not
    /// turn the mic waveform into a square wave (>>8 clipped 48-56% of samples).
    #[serde(default = "default_mic_shift")]
    pub mic_shift: u32,
    /// Right shift for ch6-7 (playback reference). Its scale is 32x the mic's,
    /// and it moves with `mysoftvol`, so it needs more headroom than the mics.
    #[serde(default = "default_ref_shift")]
    pub ref_shift: u32,
}

fn default_mic_shift() -> u32 {
    12
}

fn default_ref_shift() -> u32 {
    16
}

pub static AUDIO_CONFIG: LazyLock<AudioConfig> = LazyLock::new(|| AudioConfig {
    pcm: "noop".into(),
    channels: 1,
    bits_per_sample: 16,
    sample_rate: 16000,
    period_size: 160,
    buffer_size: 480,
    mic_shift: default_mic_shift(),
    ref_shift: default_ref_shift(),
});
