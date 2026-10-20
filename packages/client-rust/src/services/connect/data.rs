use base64::{engine::general_purpose::STANDARD as B64, Engine as _};
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::Value;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
pub enum AppMessage {
    Request(Request),
    Response(Response),
    Event(Event),
    Stream(Stream),
}

/// PCM used to travel as a JSON array of integers: 8 ch * 16 kHz meant ~770 KB/s
/// of text for 128 KB of audio, and the phone-class CPU spent real time parsing
/// it. The server now sends base64; this accepts both so an old server (or a
/// rollback) still works.
fn de_bytes<'de, D>(d: D) -> Result<Vec<u8>, D::Error>
where
    D: Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum Raw {
        List(Vec<u8>),
        Text(String),
    }
    match Raw::deserialize(d)? {
        Raw::List(v) => Ok(v),
        Raw::Text(t) => B64.decode(t.as_bytes()).map_err(serde::de::Error::custom),
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Stream {
    pub id: String,
    pub tag: String,
    #[serde(deserialize_with = "de_bytes")]
    pub bytes: Vec<u8>,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub data: Option<Value>,
}

impl Stream {
    pub fn new(tag: &str, bytes: Vec<u8>, data: Option<Value>) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            tag: tag.to_string(),
            bytes,
            data,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub id: String,
    pub event: String,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub data: Option<Value>,
}

impl Event {
    pub fn new(event: &str, data: Option<Value>) -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            event: event.to_string(),
            data,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Request {
    pub id: String,
    pub command: String,
    pub payload: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Response {
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub code: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub msg: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none", default)]
    pub data: Option<Value>,
}

impl Response {
    pub fn success() -> Self {
        Self {
            id: 0.to_string(),
            code: Some(0),
            msg: Some("success".to_string()),
            data: None,
        }
    }

    pub fn from_data(data: Value) -> Self {
        Self {
            id: 0.to_string(),
            code: None,
            msg: None,
            data: Some(data),
        }
    }

    pub fn from_error(id: &str, e: impl std::fmt::Display) -> Self {
        Self {
            id: id.to_string(),
            code: Some(-1),
            msg: Some(e.to_string()),
            data: None,
        }
    }
}
