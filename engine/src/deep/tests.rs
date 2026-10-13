//! **A native deep frame against the explorer's own**, case by case:
//! `fixtures/deep-cases.json` holds what the website's committed `perturb-scalar.wasm`
//! drew and `engine.wasm` coloured for every parity spec at its own grid and every Deep
//! gallery link at a small fixed grid, one sample a pixel, and the generator that wrote
//! it.
//!
//! What is held, and how tightly:
//!
//! - **The spec**, field for field: centre text, width, cap, degree, Julia parameter and
//!   anchor, as [`spec_of`] builds it from the link against what `deepSpecOf` built.
//! - **The interior mask and the iteration counts, exactly.** No `ln` reaches either, so
//!   a difference there is a different picture and not a rounding.
//! - **The lanes, within [`LANE_ULPS`]** units in the last place, where they are not
//!   identical. The smooth count takes three `ln` a sample, and the platform's are not
//!   wasm's; this box measured one unit at most, on a handful of samples.
//! - **The pixels, within [`RGB_LEVELS`]** a channel, where they are not identical, for
//!   every case the explorer shades. The shading reads lanes narrowed to `f32`, which
//!   absorbs a unit in the last place of a double almost always.
//!
//! Every case that is not identical is printed with how far it moved, so the divergence
//! is a reading and not only a pass (`cargo test --release deep -- --nocapture`).

use std::path::PathBuf;

use perturbation::Spec;
use rayon::prelude::*;

use super::{Perturbation, anchor_of, draw, spec_of};
use crate::colormap::Colormap;
use crate::link::{
    Context, DeepBackend, DeepFrame, DeepView, Link, colormap_for, parse, shade_lanes,
};

/// How far a native lane may sit from the explorer's, in units in the last place of the
/// double. Measured at one on Windows; the budget leaves room for another C runtime's `ln`.
const LANE_ULPS: u64 = 4;

/// How far a native pixel may sit from the explorer's, in levels of an 8-bit channel.
/// Measured at zero on Windows: every lane agreed once narrowed to `f32`.
const RGB_LEVELS: u8 = 1;

fn data() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../data")
}

fn context() -> Context {
    Context::from_data(&data()).expect("the checkout's data/")
}

fn fixture() -> serde_json::Value {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fixtures/deep-cases.json");
    crate::exact_json::exactly(&std::fs::read_to_string(&path).expect("deep-cases.json"))
}

fn deep_view(query: &str, context: &Context) -> DeepView {
    match parse(query, context).unwrap_or_else(|why| panic!("{query}: {why}")) {
        Link::Deep(view) => view,
        Link::Shallow(_) => panic!("{query}: not a deep link"),
    }
}

/// Standard base64, as the generator writes it.
fn base64(text: &str) -> Vec<u8> {
    let value = |c: u8| match c {
        b'A'..=b'Z' => c - b'A',
        b'a'..=b'z' => c - b'a' + 26,
        b'0'..=b'9' => c - b'0' + 52,
        b'+' => 62,
        b'/' => 63,
        _ => panic!("not base64: {}", c as char),
    };
    let symbols: Vec<u8> = text.bytes().filter(|&c| c != b'=').map(value).collect();
    let mut out = Vec::with_capacity(symbols.len() * 3 / 4);
    for chunk in symbols.chunks(4) {
        let bits = chunk
            .iter()
            .enumerate()
            .fold(0u32, |acc, (i, &v)| acc | (v as u32) << (18 - 6 * i));
        for byte in 0..chunk.len() - 1 {
            out.push((bits >> (16 - 8 * byte)) as u8);
        }
    }
    out
}

fn fnv(bytes: &[u8]) -> String {
    let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
    for &byte in bytes {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(0x0100_0000_01b3);
    }
    format!("{hash:016x}")
}

/// One case's distance from the explorer's, in the units the tolerances are stated in.
#[derive(Default)]
struct Reading {
    name: String,
    samples: usize,
    lanes_apart: usize,
    worst_ulps: u64,
    narrowed_apart: usize,
    pixels: usize,
    pixels_apart: usize,
    worst_level: u8,
    failures: Vec<String>,
}

/// Hold one drawn frame to its recorded case.
fn read(
    name: String,
    case: &serde_json::Value,
    spec: &Spec,
    shade: Option<(&DeepView, &Colormap)>,
) -> Reading {
    let mut reading = Reading {
        name,
        ..Reading::default()
    };
    let drawn = draw(spec).unwrap_or_else(|why| panic!("{}: {why}", reading.name));
    let recorded: Vec<f64> = base64(case["values"].as_str().expect("values"))
        .chunks_exact(8)
        .map(|bytes| f64::from_le_bytes(bytes.try_into().unwrap()))
        .collect();
    reading.samples = recorded.len();
    if drawn.smooth.len() != recorded.len() {
        reading.failures.push(format!(
            "{} samples against {}",
            drawn.smooth.len(),
            recorded.len()
        ));
        return reading;
    }
    let mut bytes = Vec::with_capacity(recorded.len() * 8);
    for value in &drawn.smooth {
        bytes.extend_from_slice(&value.to_le_bytes());
    }
    let mask: Vec<u8> = drawn.smooth.iter().map(|v| v.is_nan() as u8).collect();
    if fnv(&mask) != case["nan"].as_str().unwrap() {
        reading.failures.push("the interior mask moved".into());
    }
    let counts = (
        case["ran"].as_u64().unwrap(),
        case["saved"].as_u64().unwrap(),
    );
    if (drawn.ran, drawn.saved) != counts {
        reading.failures.push(format!(
            "ran/saved {}/{} against {}/{}",
            drawn.ran, drawn.saved, counts.0, counts.1
        ));
    }
    if fnv(&bytes) != case["lanes"].as_str().unwrap() {
        for (&ours, &theirs) in drawn.smooth.iter().zip(&recorded) {
            if ours.to_bits() == theirs.to_bits() || (ours.is_nan() && theirs.is_nan()) {
                continue;
            }
            reading.lanes_apart += 1;
            reading.worst_ulps = reading
                .worst_ulps
                .max(ours.to_bits().abs_diff(theirs.to_bits()));
            if (ours as f32).to_bits() != (theirs as f32).to_bits() {
                reading.narrowed_apart += 1;
            }
        }
        if reading.worst_ulps > LANE_ULPS {
            reading.failures.push(format!(
                "lanes {} ulps apart, past {LANE_ULPS}",
                reading.worst_ulps
            ));
        }
    }
    if let (Some((view, colormap)), Some(expected)) = (shade, case["pixels"].as_str()) {
        let lanes = crate::link::Lanes {
            width: spec.sample_width(),
            height: spec.sample_height(),
            smooth: drawn.smooth,
        };
        let size = [lanes.width, lanes.height];
        let ours = shade_lanes(&lanes, &view.shade, colormap, size, 1);
        let theirs = base64(expected);
        reading.pixels = theirs.len() / 3;
        if fnv(&ours) != case["rgb"].as_str().unwrap() {
            for (a, b) in ours.chunks_exact(3).zip(theirs.chunks_exact(3)) {
                let level = a.iter().zip(b).map(|(x, y)| x.abs_diff(*y)).max().unwrap();
                if level > 0 {
                    reading.pixels_apart += 1;
                    reading.worst_level = reading.worst_level.max(level);
                }
            }
            if reading.worst_level > RGB_LEVELS || ours.len() != theirs.len() {
                reading.failures.push(format!(
                    "pixels {} levels apart, past {RGB_LEVELS}",
                    reading.worst_level
                ));
            }
        }
    }
    reading
}

/// The spec as the page built it, against the one built here, field by field.
fn same_spec(ours: &Spec, theirs: &serde_json::Value) -> Result<(), String> {
    let text = |key: &str| theirs[key].as_str().map(str::to_string);
    let julia = match (text("julia_re"), text("julia_im")) {
        (Some(re), Some(im)) => Some((re, im)),
        _ => None,
    };
    let anchor = match theirs["anchor"].as_str() {
        Some("origin") => Some(perturbation::Anchor::Origin),
        Some(_) => Some(perturbation::Anchor::Parameter),
        None => None,
    };
    let checks = [
        (
            "center_re",
            Some(ours.center_re.clone()) == text("center_re"),
        ),
        (
            "center_im",
            Some(ours.center_im.clone()) == text("center_im"),
        ),
        ("width", Some(ours.width) == theirs["width"].as_f64()),
        (
            "resolution",
            theirs["resolution"] == serde_json::json!(ours.resolution),
        ),
        (
            "maxiter",
            ours.maxiter.map(u64::from) == theirs["maxiter"].as_u64(),
        ),
        (
            "degree",
            u64::from(ours.degree) == theirs["degree"].as_u64().unwrap_or(2),
        ),
        ("julia", ours.julia == julia),
        (
            "anchor",
            anchor.is_none_or(|anchor| anchor == ours.anchor)
                && (anchor.is_some() == julia.is_some()),
        ),
    ];
    let wrong: Vec<_> = checks
        .iter()
        .filter(|(_, ok)| !ok)
        .map(|(key, _)| *key)
        .collect();
    if wrong.is_empty() {
        Ok(())
    } else {
        Err(format!("spec differs in {wrong:?}"))
    }
}

#[test]
fn a_deep_frame_is_the_explorers_within_the_stated_tolerance() {
    let fixture = fixture();
    let context = context();
    let shade_view = deep_view(fixture["shade_link"].as_str().unwrap(), &context);
    let shade_map =
        colormap_for(&context, &shade_view.palette, None, shade_view.shade.bake).unwrap();
    let cases = fixture["cases"].as_array().expect("cases");

    let readings: Vec<Reading> = cases
        .par_iter()
        .enumerate()
        .map(|(at, case)| match case["source"].as_str() {
            Some("parity") => {
                let spec = Spec::parse(&case["spec"].to_string()).unwrap();
                let name = format!("parity {}", case["label"].as_str().unwrap());
                read(name, case, &spec, Some((&shade_view, &shade_map)))
            }
            Some("gallery") => {
                let query = case["query"].as_str().unwrap();
                let view = deep_view(query, &context);
                let resolution = &case["spec"]["resolution"];
                let samples = [0, 1].map(|i| resolution[i].as_u64().unwrap() as u32);
                let spec = spec_of(&view, samples);
                let subject = case["subject"].as_str().unwrap_or(query);
                let name = format!("gallery case {at} ({subject})");
                let map = colormap_for(
                    &context,
                    &view.palette,
                    view.level.as_ref(),
                    view.shade.bake,
                )
                .unwrap();
                let mut reading = read(name, case, &spec, Some((&view, &map)));
                if let Err(why) = same_spec(&spec, &case["spec"]) {
                    reading.failures.push(why);
                }
                reading
            }
            other => panic!("a case from {other:?}"),
        })
        .collect();

    let (parity, gallery) = readings
        .iter()
        .partition::<Vec<_>, _>(|r| r.name.starts_with("parity"));
    assert_eq!(parity.len(), 142, "every parity spec");
    assert_eq!(gallery.len(), 105, "every Deep gallery link");
    let mut moved = 0;
    for reading in &readings {
        if reading.lanes_apart > 0 || reading.pixels_apart > 0 || !reading.failures.is_empty() {
            moved += 1;
            println!(
                "{}: {} of {} lanes apart (worst {} ulps, {} once narrowed to f32), {} of {} \
                 pixels apart (worst {} levels){}",
                reading.name,
                reading.lanes_apart,
                reading.samples,
                reading.worst_ulps,
                reading.narrowed_apart,
                reading.pixels_apart,
                reading.pixels,
                reading.worst_level,
                if reading.failures.is_empty() {
                    String::new()
                } else {
                    format!(" — {}", reading.failures.join("; "))
                }
            );
        }
    }
    println!("{moved} of {} cases not identical", readings.len());
    let failed: Vec<_> = readings.iter().filter(|r| !r.failures.is_empty()).collect();
    assert!(
        failed.is_empty(),
        "{} cases past the tolerance: {}",
        failed.len(),
        failed
            .iter()
            .map(|r| format!("{}: {}", r.name, r.failures.join("; ")))
            .collect::<Vec<_>>()
            .join("\n")
    );
}

/// `render-link`'s backend is the same draw: its lanes for a gallery link are the ones
/// [`draw`] hands the fixture test, in the [`crate::link::Lanes`] layout.
#[test]
fn the_backend_hands_render_link_the_drawn_lanes() {
    let context = context();
    let view = deep_view(
        "dv=3&x=-0.74937053247003823168823992075369&y=0.041472667068168900034718746387049\
         &w=3.4869054402668363e-12&n=4000&p=glowdon&scale=absolute&period=400",
        &context,
    );
    let frame = DeepFrame {
        view: &view,
        samples: [32, 18],
    };
    let lanes = Perturbation.lanes(&frame).unwrap();
    assert_eq!((lanes.width, lanes.height), (32, 18));
    let drawn = draw(&spec_of(&view, [32, 18])).unwrap();
    assert_eq!(
        lanes.smooth.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
        drawn.smooth.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
    );
}

/// `anchorOf`'s rule: the nearer of the two anchors to the centre, ties to the parameter.
#[test]
fn a_julia_view_is_anchored_where_the_page_anchors_it() {
    let context = context();
    let at = |x: &str, y: &str| {
        deep_view(
            &format!(
                "dv=3&f=julia&cx=-0.75&cy=0.1&x={x}&y={y}&w=1e-6&n=500&p=viridis&scale=absolute&period=40"
            ),
            &context,
        )
    };
    assert_eq!(
        anchor_of(&at("-0.75", "0.1")),
        Some(perturbation::Anchor::Parameter)
    );
    assert_eq!(
        anchor_of(&at("0.01", "0")),
        Some(perturbation::Anchor::Origin)
    );
    // Equidistant: `z = 0` and `z = c` are both 0.375 away in the larger axis.
    assert_eq!(
        anchor_of(&at("-0.375", "0")),
        Some(perturbation::Anchor::Parameter)
    );
    let mandelbrot = deep_view("dv=3&x=-0.75&y=0.1&w=1e-6&n=500&p=viridis", &context);
    assert_eq!(anchor_of(&mandelbrot), None);
}

/// The exact decimal difference `anchorOf` reads, where a double would lose it.
#[test]
fn a_decimal_difference_is_taken_before_it_is_rounded() {
    let a = crate::link::Decimal::parse("-0.74501772828532335842941892835857434").unwrap();
    let b = crate::link::Decimal::parse("-0.74501772828532335842941892835857400").unwrap();
    assert_eq!(a.difference(&b), -3.4e-34);
    assert_eq!(b.difference(&a), 3.4e-34);
    let c = crate::link::Decimal::parse("0.25").unwrap();
    // Opposite signs add, and the sum is rounded once, from its exact text.
    let sum: f64 = "0.99501772828532335842941892835857434".parse().unwrap();
    assert_eq!(c.difference(&a), sum);
    assert_eq!(a.difference(&c), -sum);
    assert_eq!(a.difference(&a), 0.0);
    assert_eq!(
        crate::link::Decimal::parse("12.5").unwrap().difference(&c),
        12.25
    );
}
