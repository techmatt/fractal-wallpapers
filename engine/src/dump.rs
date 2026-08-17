//! A field on disk, and the record that says what it is.
//!
//! Iterating is the expensive stage and coloring is not, so the question "what
//! would this look like in another palette?" should not cost another render. A
//! dumped field is the answer: the raw scalars, before any normalization, at
//! supersampled resolution, exactly as the coloring stage would have received
//! them. Recoloring one reproduces the render it came from bit for bit, which is
//! the property that makes the dump worth trusting rather than merely fast.
//!
//! Two files, and both are needed:
//!
//! * **`<name>.f32`** — little-endian `f32`, row-major, one value per
//!   supersample, `NaN` where the field has nothing to say. Nothing else: no
//!   header, no compression, no framing. A bare array is the one format that
//!   every tool in every language can already read.
//! * **`<name>.json`** — the record. What field this is, the curve it is read
//!   through, the grid it was sampled on, and the location's decimal strings.
//!   Without it the binary is an anonymous pile of floats.
//!
//! This is an exploration tool, and deliberately no more than that: dump, look,
//! recolor, throw away. There is no cache, no key, no index of what has been
//! dumped — those would make the dump a thing to maintain, and the field is
//! cheap enough to make again.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::coloring::Transform;
use crate::field::{Field, FieldSpec};
use crate::spec::Location;

/// The sidecar record written beside a dumped field.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pub schema: u32,
    /// The mode this field was dumped for, when it was asked for by name.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mode: Option<String>,
    pub field: FieldSpec,
    /// The curve the render would have read this field through. A recolor that
    /// is not told otherwise uses it, so dump → recolor is a round trip.
    pub transform: Transform,
    /// The colormap the field was dumped alongside — the recolor default.
    pub colormap: String,
    pub location: Location,
    pub maxiter: u32,
    /// Output image size in pixels.
    pub resolution: [u32; 2],
    pub supersample: u32,
    /// Size of the array in the binary: `resolution × supersample`.
    pub samples: [u32; 2],
    pub interior_fraction: f64,
    /// How to read the binary. Stated rather than implied, because a field read
    /// with the wrong element type produces a picture rather than an error.
    pub dtype: String,
    pub layout: String,
    /// The binary's file name, so the record names its own other half.
    pub field_file: String,
}

/// How the values are stored.
pub const DTYPE: &str = "f32_le";
/// Row 0 first, left to right.
pub const LAYOUT: &str = "row_major";

/// The record path that goes with a field path.
pub fn record_path(field_path: &Path) -> PathBuf {
    field_path.with_extension("json")
}

/// Refuse a dump path that would collide with its own record.
pub fn check_path(field_path: &Path) -> Result<(), String> {
    if field_path.extension().is_some_and(|e| e == "json") {
        return Err(format!(
            "{}: a dumped field cannot be named '.json' — that is where its record goes",
            field_path.display()
        ));
    }
    Ok(())
}

/// Write a field and its record.
pub fn write(field_path: &Path, field: &Field, record: &Record) -> Result<PathBuf, String> {
    check_path(field_path)?;
    if let Some(parent) = field_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }

    let mut bytes = Vec::with_capacity(field.values.len() * 4);
    for value in &field.values {
        bytes.extend_from_slice(&value.to_le_bytes());
    }
    std::fs::write(field_path, &bytes)
        .map_err(|e| format!("write field {}: {e}", field_path.display()))?;

    let record_path = record_path(field_path);
    let text = serde_json::to_string(record).map_err(|e| format!("record: {e}"))?;
    std::fs::write(&record_path, text)
        .map_err(|e| format!("write record {}: {e}", record_path.display()))?;
    Ok(record_path)
}

/// Read a field and its record back.
pub fn read(field_path: &Path) -> Result<(Field, Record), String> {
    let record_path = record_path(field_path);
    let text = std::fs::read_to_string(&record_path)
        .map_err(|e| format!("read record {}: {e}", record_path.display()))?;
    let record: Record = serde_json::from_str(&text)
        .map_err(|e| format!("parse record {}: {e}", record_path.display()))?;
    if record.schema != 1 {
        return Err(format!(
            "record {} has schema {}, expected 1",
            record_path.display(),
            record.schema
        ));
    }
    if record.dtype != DTYPE || record.layout != LAYOUT {
        return Err(format!(
            "record {} describes a {} {} field, which this engine cannot read",
            record_path.display(),
            record.dtype,
            record.layout
        ));
    }

    let bytes = std::fs::read(field_path)
        .map_err(|e| format!("read field {}: {e}", field_path.display()))?;
    let [width, height] = record.samples;
    let expected = width as usize * height as usize;
    if bytes.len() != expected * 4 {
        return Err(format!(
            "{} holds {} bytes, but its record describes {width}×{height} f32 values ({} bytes)",
            field_path.display(),
            bytes.len(),
            expected * 4
        ));
    }
    let values = bytes
        .chunks_exact(4)
        .map(|chunk| f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]))
        .collect();

    Ok((
        Field {
            values,
            width,
            height,
        },
        record,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn record() -> Record {
        Record {
            schema: 1,
            mode: Some("stripe".into()),
            field: FieldSpec::Stripe { density: 6.0 },
            transform: Transform::Linear,
            colormap: "twilight_shifted".into(),
            location: Location {
                family: "mandelbrot".into(),
                degree: crate::spec::Degree::Integer(2),
                center_re: "-0.5".into(),
                center_im: "0.0".into(),
                width: "3.0".into(),
                c: None,
                p: None,
                z_prev: None,
            },
            maxiter: 4000,
            resolution: [2, 2],
            supersample: 2,
            samples: [4, 4],
            interior_fraction: 0.25,
            dtype: DTYPE.into(),
            layout: LAYOUT.into(),
            field_file: "field.f32".into(),
        }
    }

    fn field() -> Field {
        Field {
            values: (0..16)
                .map(|i| {
                    if i % 5 == 0 {
                        f32::NAN
                    } else {
                        i as f32 * 0.25
                    }
                })
                .collect(),
            width: 4,
            height: 4,
        }
    }

    /// The dump has to survive the round trip exactly — including the `NaN`s,
    /// which are the mask, not missing data.
    #[test]
    fn a_field_round_trips_through_disk_bit_for_bit() {
        let directory = std::env::temp_dir().join("fractal_engine_dump_round_trip");
        let path = directory.join("field.f32");
        let _ = std::fs::remove_dir_all(&directory);

        let written = write(&path, &field(), &record()).unwrap();
        assert_eq!(written, directory.join("field.json"));

        let (back, record_back) = read(&path).unwrap();
        assert_eq!(record_back, record());
        assert_eq!(back.width, 4);
        assert_eq!(back.height, 4);
        for (a, b) in field().values.iter().zip(&back.values) {
            assert_eq!(a.to_bits(), b.to_bits());
        }
        std::fs::remove_dir_all(&directory).unwrap();
    }

    #[test]
    fn a_field_and_its_record_cannot_be_the_same_file() {
        assert!(check_path(Path::new("artifacts/field.f32")).is_ok());
        let message = check_path(Path::new("artifacts/field.json")).unwrap_err();
        assert!(message.contains("record"), "{message}");
    }

    #[test]
    fn a_truncated_field_is_refused_rather_than_read_short() {
        let directory = std::env::temp_dir().join("fractal_engine_dump_truncated");
        let path = directory.join("field.f32");
        let _ = std::fs::remove_dir_all(&directory);
        write(&path, &field(), &record()).unwrap();
        std::fs::write(&path, [0u8; 12]).unwrap();

        let message = read(&path).err().expect("a short file must be refused");
        assert!(message.contains("12 bytes"), "{message}");
        std::fs::remove_dir_all(&directory).unwrap();
    }
}
