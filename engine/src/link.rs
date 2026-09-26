//! An explorer link, read into something the engine can draw.
//!
//! The explorer on the website is addressed by a query string, and two contracts say
//! what one means: **`explorer/permalink.js`** for the shallow view (`v=1`–`4`, drawn in
//! `f64` by this engine's own code compiled to wasm) and **`explorer/deep-link.js`** for
//! the Deep tab (`dv=1`–`3`, drawn by perturbation). Both are JavaScript, both live in
//! the `fractal-website` checkout, and **they are the authority**: this module follows
//! their `parse` rule for rule and is held to them by `fixtures/link-cases.json`, a
//! record of what the site's own modules answered for 528 real and hand-made links —
//! see [`tests::the_parsers_are_the_sites`]. Where the two disagree, this file is wrong.
//!
//! What each parse needs from outside the link is the same thing the page hands its own
//! parser, and here every piece of it is this repository's:
//!
//! ```text
//! home views     family::home_view, written as JavaScript would write the double
//! constants      data/anchors.jsonl — the anchors the site's catalog.js is baked from
//! settled        mode::params_of over the catalog, for a v1/v2 link's derived parameter
//! the width cap  maxiter::for_width, which is what the page's own module answers
//! palettes       data/palettes/<name>.json, the library the site's palettes.bin is baked from
//! ```
//!
//! **Numbers are written the way JavaScript writes them**, because a canonical link is
//! compared as a string: [`js_number`] is ECMAScript's `Number::toString` laid over
//! Rust's shortest round-trip digits, which are the same digits.
//!
//! **A deep link is parsed and not drawn.** Its centre is an exact decimal
//! ([`Decimal`]), kept as the text the Deep tab would write back, and a
//! [`DeepView`] goes to a [`DeepBackend`] — the seam a perturbation renderer plugs into,
//! lanes in and shading out. The only backend today is [`NotBuilt`], which says so.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

use crate::autolevel::{self, Curve};
use crate::coloring::{self, Palette, Rolloff, Scale, Transfer};
use crate::colormap::{Bake, Colormap};
use crate::field::Field;
use crate::maxiter;
use crate::mode;
use crate::resample;
use crate::spec::{FamilySpec, RenderSpec, ViewportSpec};

/// The shallow contract version this module emits, and the versions it reads.
pub const VERSION: u32 = 4;
const READS: [u32; 4] = [1, 2, 3, 4];

/// The deep contract's, and the key that marks a query as deep.
pub const DEEP_VERSION: u32 = 3;
const DEEP_READS: [u32; 3] = [1, 2, 3];
pub const DEEP_MARKER: &str = "dv";

/// Where an explorer link opens, for the absolute URL a file's metadata carries.
pub const EXPLORER_URL: &str = "https://techmatt.github.io/fractals/explorer/";

/// The families a shallow link names, in `permalink.js`'s order; the first is the default.
const FAMILIES: [&str; 12] = [
    "mandelbrot",
    "multibrot3",
    "multibrot4",
    "multibrot5",
    "multibrot6",
    "julia",
    "julia3",
    "julia4",
    "julia5",
    "julia6",
    "phoenix",
    "phoenix_plane",
];

/// The modes a shallow link names — the explorer's roster, not the whole catalog.
const MODES: [&str; 17] = [
    "smooth",
    "tia",
    "stripe",
    "gaussian_int",
    "trap_circle",
    "curvature",
    "smooth_mean_angle",
    "smooth_angle_min",
    "smooth_trap_circle",
    "smooth_stripe",
    "smooth_curvature",
    "direct_trap_ring",
    "direct_trap_screen",
    "direct_trap_multiply",
    "direct_trap_lines",
    "threads",
    "itinerary",
];

/// Each family's constants, in emit order. Every one is half of a pair.
fn constant_keys(family: &str) -> &'static [&'static str] {
    match family {
        "julia" | "julia3" | "julia4" | "julia5" | "julia6" => &["cx", "cy"],
        "phoenix" => &["cx", "cy", "px", "py", "zx", "zy"],
        "phoenix_plane" => &["px", "py"],
        _ => &[],
    }
}
const CONSTANT_KEYS: [&str; 6] = ["cx", "cy", "px", "py", "zx", "zy"];
const CONSTANT_PAIRS: [(&str, &str); 3] = [("cx", "cy"), ("px", "py"), ("zx", "zy")];

/// Each mode's parameters, in emit order.
fn mode_parameters(mode: &str) -> &'static [&'static str] {
    match mode {
        "stripe" => &["density"],
        "trap_circle" => &["radius"],
        "smooth_mean_angle" | "smooth_angle_min" | "smooth_curvature" => &["weight"],
        "smooth_trap_circle" => &["radius", "weight"],
        "smooth_stripe" => &["density", "weight"],
        "direct_trap_ring" => &["radius", "threshold", "opacity"],
        "direct_trap_screen" | "direct_trap_multiply" | "direct_trap_lines" => {
            &["threshold", "opacity"]
        }
        "threads" => &["sigma", "weight"],
        "itinerary" => &["shift"],
        _ => &[],
    }
}
const PARAMETER_KEYS: [&str; 7] = [
    "density",
    "radius",
    "sigma",
    "threshold",
    "weight",
    "opacity",
    "shift",
];

/// The parameter a v3+ link means "derive from the view" by leaving out, by mode.
pub fn derived_parameter(mode: &str) -> Option<&'static str> {
    match mode {
        "smooth_mean_angle" | "smooth_angle_min" | "smooth_curvature" => Some("weight"),
        "direct_trap_screen" | "direct_trap_multiply" | "direct_trap_lines" => Some("opacity"),
        _ => None,
    }
}

/// The keys the page carries and the picture ignores.
const UI_KEYS: [&str; 5] = ["panel", "every", "collection", "modes", "hue"];

const SHADE_KEYS: [&str; 10] = [
    "gamma", "cycles", "phase", "reverse", "mirror", "transfer", "rolloff", "scale", "lambda",
    "period",
];

const COORDINATE_LIMIT: usize = 64;
const CAP_FLOOR: u64 = 50;
const CAP_LIMIT: u64 = 2_000_000;
const ASPECT_LIMIT: u32 = 10000;
const DEFAULT_ASPECT: (u32, u32) = (16, 9);
const DEFAULT_PALETTE: &str = "twilight_shifted";

// ------------------------------------------------------------------- the context

/// What a parse needs from outside the link: the palettes and the anchors, from `data/`.
pub struct Context {
    palettes: PathBuf,
    names: BTreeSet<String>,
    /// `anchor name → family constants`, as `data/anchors.jsonl` writes them.
    anchors: BTreeMap<String, serde_json::Value>,
}

impl Context {
    /// Read the context out of a checkout's `data/` directory.
    pub fn from_data(data: &Path) -> Result<Context, String> {
        let palettes = data.join("palettes");
        let listing = std::fs::read_dir(&palettes)
            .map_err(|e| format!("read the colormap library {}: {e}", palettes.display()))?;
        let mut names = BTreeSet::new();
        for entry in listing.flatten() {
            let path = entry.path();
            if path.is_file() && path.extension().is_some_and(|ext| ext == "json") {
                if let Some(stem) = path.file_stem().and_then(|stem| stem.to_str()) {
                    names.insert(stem.to_string());
                }
            }
        }
        let path = data.join("anchors.jsonl");
        let text = std::fs::read_to_string(&path)
            .map_err(|e| format!("read the anchors {}: {e}", path.display()))?;
        let mut anchors = BTreeMap::new();
        for line in text.lines().filter(|line| !line.trim().is_empty()) {
            let row: serde_json::Value =
                serde_json::from_str(line).map_err(|e| format!("parse {}: {e}", path.display()))?;
            if let Some(name) = row["anchor"].as_str() {
                anchors.insert(name.to_string(), row["family"].clone());
            }
        }
        Ok(Context {
            palettes,
            names,
            anchors,
        })
    }

    /// The colormap library the palette names are files of.
    pub fn palettes(&self) -> &Path {
        &self.palettes
    }

    fn has_palette(&self, name: &str) -> bool {
        self.names.contains(name)
    }

    fn cyclic(&self, name: &str) -> Result<bool, String> {
        let (kind, _) = Colormap::read_stops(&self.palettes, name)?;
        Ok(kind == crate::colormap::Kind::Cyclic)
    }

    /// A family's constants when a link names none: the site's `catalog.js`
    /// `CONSTANTS`, which `builder/explorer.py` bakes from the same anchors.
    fn seeds(&self, family: &str) -> Result<BTreeMap<&'static str, Coordinate>, String> {
        let keys = constant_keys(family);
        if keys.is_empty() {
            return Ok(BTreeMap::new());
        }
        let anchor = if family.starts_with("julia") {
            "julia"
        } else {
            "phoenix"
        };
        let row = self
            .anchors
            .get(anchor)
            .ok_or_else(|| format!("data/anchors.jsonl has no {anchor} anchor"))?;
        let pair = |key: &str, default: [&str; 2]| -> [String; 2] {
            match row[key].as_array() {
                Some(pair) if pair.len() == 2 => [
                    pair[0].as_str().unwrap_or_default().to_string(),
                    pair[1].as_str().unwrap_or_default().to_string(),
                ],
                _ => [default[0].to_string(), default[1].to_string()],
            }
        };
        let c = pair("c", ["", ""]);
        let p = pair("p", ["", ""]);
        let z = pair("z_prev", ["0", "0"]);
        let mut seeds = BTreeMap::new();
        for &key in keys {
            let text = match key {
                "cx" => &c[0],
                "cy" => &c[1],
                "px" => &p[0],
                "py" => &p[1],
                "zx" => &z[0],
                _ => &z[1],
            };
            seeds.insert(
                key,
                Coordinate {
                    text: text.clone(),
                    value: text.parse().unwrap_or(f64::NAN),
                },
            );
        }
        Ok(seeds)
    }

    /// Where a family comes home to, as the page's own `coordinateOf` spells it.
    fn home(&self, family: &str) -> Result<[Coordinate; 3], String> {
        let constants = self.seeds(family)?;
        let spec = family_spec(family, &constants);
        let home = spec
            .resolve()?
            .family
            .home_view()
            .ok_or_else(|| format!("{family} has no home view"))?;
        Ok([
            Coordinate::of(home.center.re),
            Coordinate::of(home.center.im),
            Coordinate::of(home.width),
        ])
    }
}

/// The engine family a link's family name and constants are, as the site's
/// `render.js` `familySpecOf` maps them.
fn family_spec(family: &str, constants: &BTreeMap<&'static str, Coordinate>) -> FamilySpec {
    let text = |key: &str| {
        constants
            .get(key)
            .map(|c| c.text.clone())
            .unwrap_or_default()
    };
    let pair = |re: &str, im: &str| [text(re), text(im)];
    let degree = |name: &str| {
        name.chars()
            .last()
            .and_then(|d| d.to_digit(10))
            .unwrap_or(2)
    };
    match family {
        "mandelbrot" => FamilySpec::Mandelbrot,
        "multibrot3" | "multibrot4" | "multibrot5" | "multibrot6" => FamilySpec::Multibrot {
            degree: degree(family),
        },
        "julia" => FamilySpec::Julia {
            degree: 2,
            c: pair("cx", "cy"),
        },
        "julia3" | "julia4" | "julia5" | "julia6" => FamilySpec::Julia {
            degree: degree(family),
            c: pair("cx", "cy"),
        },
        "phoenix" => FamilySpec::Phoenix {
            c: pair("cx", "cy"),
            p: pair("px", "py"),
            z_prev: pair("zx", "zy"),
        },
        _ => FamilySpec::PhoenixM {
            p: pair("px", "py"),
        },
    }
}

// ------------------------------------------------------------------- the numbers

/// A number as JavaScript's `String(number)` writes it: the contract's `shortest`.
///
/// Rust's `{:e}` gives the shortest digits that read back as the same double, which is
/// the digit string ECMAScript's `Number::toString` chooses too; what differs is the
/// layout, and this is ECMAScript's: plain from 1e-6 up to 1e21, exponent outside it,
/// `e+` for a positive exponent and no trailing `.0`.
pub fn js_number(value: f64) -> String {
    if value == 0.0 {
        return "0".into();
    }
    if !value.is_finite() {
        return if value.is_nan() {
            "NaN".into()
        } else if value > 0.0 {
            "Infinity".into()
        } else {
            "-Infinity".into()
        };
    }
    let scientific = format!("{:e}", value.abs());
    let (mantissa, exponent) = scientific.split_once('e').expect("{:e} writes an exponent");
    let digits: String = mantissa.chars().filter(char::is_ascii_digit).collect();
    let k = digits.len() as i64;
    let n = exponent.parse::<i64>().expect("an exponent") + 1;
    let body = if k <= n && n <= 21 {
        format!("{digits}{}", "0".repeat((n - k) as usize))
    } else if 0 < n && n <= 21 {
        format!("{}.{}", &digits[..n as usize], &digits[n as usize..])
    } else if -6 < n && n <= 0 {
        format!("0.{}{digits}", "0".repeat((-n) as usize))
    } else {
        let e = n - 1;
        let sign = if e < 0 { '-' } else { '+' };
        if k == 1 {
            format!("{digits}e{sign}{}", e.abs())
        } else {
            format!("{}.{}e{sign}{}", &digits[..1], &digits[1..], e.abs())
        }
    };
    if value < 0.0 {
        format!("-{body}")
    } else {
        body
    }
}

/// A coordinate: the text a link carries, and the double it reads as.
#[derive(Clone, Debug, PartialEq)]
pub struct Coordinate {
    pub text: String,
    pub value: f64,
}

impl Coordinate {
    fn of(value: f64) -> Coordinate {
        Coordinate {
            text: js_number(value),
            value,
        }
    }
}

/// `permalink.js`'s `DECIMAL`: a sign, digits and a point, and an optional exponent.
fn is_decimal(text: &str) -> bool {
    let bytes = text.as_bytes();
    let mut at = 0;
    if matches!(bytes.first(), Some(b'+' | b'-')) {
        at += 1;
    }
    let whole = bytes[at..]
        .iter()
        .take_while(|b| b.is_ascii_digit())
        .count();
    at += whole;
    let mut fraction = 0;
    if bytes.get(at) == Some(&b'.') {
        at += 1;
        fraction = bytes[at..]
            .iter()
            .take_while(|b| b.is_ascii_digit())
            .count();
        at += fraction;
    }
    if whole == 0 && fraction == 0 {
        return false;
    }
    if matches!(bytes.get(at), Some(b'e' | b'E')) {
        at += 1;
        if matches!(bytes.get(at), Some(b'+' | b'-')) {
            at += 1;
        }
        let digits = bytes[at..]
            .iter()
            .take_while(|b| b.is_ascii_digit())
            .count();
        if digits == 0 {
            return false;
        }
        at += digits;
    }
    at == bytes.len()
}

/// `Number(text)` for a text [`is_decimal`] accepted: correctly rounded, like the JS one.
fn number(text: &str) -> f64 {
    text.trim().parse().unwrap_or(f64::NAN)
}

/// `permalink.js`'s `finite`.
fn finite(text: &str, key: &str) -> Result<f64, String> {
    if !is_decimal(text) {
        return Err(format!("{key} has to be a number; the link says {text}."));
    }
    let value = number(text);
    if !value.is_finite() {
        return Err(format!(
            "{key} is not a number this arithmetic can hold: {text}."
        ));
    }
    Ok(value)
}

fn positive(text: &str, key: &str) -> Result<f64, String> {
    let value = finite(text, key)?;
    if value.is_nan() || value <= 0.0 {
        return Err(format!("{key} has to be positive; the link says {text}."));
    }
    Ok(value)
}

fn utf16_len(text: &str) -> usize {
    text.encode_utf16().count()
}

/// A shallow coordinate: the text verbatim, checked and read.
fn coordinate(text: Option<&str>, key: &str) -> Result<Option<Coordinate>, String> {
    let Some(text) = text else { return Ok(None) };
    if utf16_len(text) > COORDINATE_LIMIT {
        return Err(format!(
            "{key} is {} characters, and a coordinate is capped at {COORDINATE_LIMIT}.",
            utf16_len(text)
        ));
    }
    if !is_decimal(text) {
        return Err(format!(
            "{key} has to be a decimal number, with or without an exponent; the link says {text}."
        ));
    }
    let value = number(text);
    if !value.is_finite() {
        return Err(format!(
            "{key} is not a number this arithmetic can hold: {text}."
        ));
    }
    Ok(Some(Coordinate {
        text: text.to_string(),
        value,
    }))
}

/// `readCap`: a whole number between the floor and the limit.
fn read_cap(text: &str) -> Result<u32, String> {
    if text.is_empty() || !text.bytes().all(|b| b.is_ascii_digit()) {
        return Err(format!(
            "n is the iteration cap and has to be a whole number; the link says {text}."
        ));
    }
    // Digits only, so the one way this parse fails is a number past `u64`, which is past
    // the limit too.
    let value = text.parse::<u64>().unwrap_or(u64::MAX);
    if !(CAP_FLOOR..=CAP_LIMIT).contains(&value) {
        return Err(format!(
            "n is the iteration cap and is between {CAP_FLOOR} and 2,000,000; the link says {text}."
        ));
    }
    Ok(value as u32)
}

/// `readAspect`: `across:down`, one to five digits a side, each side 1 to 10000.
fn read_aspect(text: Option<&str>) -> Result<(u32, u32), String> {
    let Some(text) = text else {
        return Ok(DEFAULT_ASPECT);
    };
    let refused = || format!("a is the aspect, written across:down — the link says {text}.");
    let (across, down) = text.split_once(':').ok_or_else(refused)?;
    let side =
        |side: &str| (1..=5).contains(&side.len()) && side.bytes().all(|b| b.is_ascii_digit());
    if !side(across) || !side(down) {
        return Err(refused());
    }
    let (across, down): (u32, u32) = (across.parse().unwrap(), down.parse().unwrap());
    if across < 1 || down < 1 || across > ASPECT_LIMIT || down > ASPECT_LIMIT {
        return Err(format!(
            "an aspect's two sides are each between 1 and {ASPECT_LIMIT}; the link says {text}."
        ));
    }
    Ok((across, down))
}

/// A version number as both contracts check one: digits, and a number they read.
fn read_version(text: &str, reads: &[u32]) -> Option<u32> {
    if text.is_empty() || !text.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    let value = text.parse::<u64>().unwrap_or(u64::MAX);
    reads
        .iter()
        .copied()
        .find(|&version| u64::from(version) == value)
}

// --------------------------------------------------------------------- the query

/// `URLSearchParams` over a query: `+` is a space, `%XX` a byte, and the bytes UTF-8.
struct Query {
    pairs: Vec<(String, String)>,
}

impl Query {
    fn parse(search: &str) -> Query {
        let search = search.strip_prefix('?').unwrap_or(search);
        let pairs = search
            .split('&')
            .filter(|piece| !piece.is_empty())
            .map(|piece| match piece.split_once('=') {
                Some((name, value)) => (decode(name), decode(value)),
                None => (decode(piece), String::new()),
            })
            .collect();
        Query { pairs }
    }

    fn get(&self, key: &str) -> Option<&str> {
        self.pairs
            .iter()
            .find(|(name, _)| name == key)
            .map(|(_, value)| value.as_str())
    }

    fn has(&self, key: &str) -> bool {
        self.get(key).is_some()
    }

    /// Every key once, or the one given twice.
    fn keys(&self) -> Result<Vec<&str>, String> {
        let mut seen = Vec::new();
        for (name, _) in &self.pairs {
            if seen.contains(&name.as_str()) {
                return Err(format!(
                    "the link gives {name} twice, and there is no rule for which wins."
                ));
            }
            seen.push(name.as_str());
        }
        Ok(seen)
    }
}

/// application/x-www-form-urlencoded percent-decoding, as `URLSearchParams` does it.
fn decode(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut at = 0;
    while at < bytes.len() {
        let byte = bytes[at];
        let hex = |b: u8| (b as char).to_digit(16);
        if byte == b'+' {
            out.push(b' ');
        } else if byte == b'%'
            && at + 2 < bytes.len()
            && let (Some(high), Some(low)) = (hex(bytes[at + 1]), hex(bytes[at + 2]))
        {
            out.push((high * 16 + low) as u8);
            at += 3;
            continue;
        } else {
            out.push(byte);
        }
        at += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// `encodeURIComponent`, with the colon left alone: `permalink.js`'s `encode`.
pub fn encode(text: &str) -> String {
    encode_keeping(text, b":")
}

/// The same, and the slash and the comma too: `encodeCurve`, for `level`.
fn encode_curve(text: &str) -> String {
    encode_keeping(text, b":/,")
}

fn encode_keeping(text: &str, kept: &[u8]) -> String {
    let mut out = String::with_capacity(text.len());
    for &byte in text.as_bytes() {
        if byte.is_ascii_alphanumeric() || b"-_.!~*'()".contains(&byte) || kept.contains(&byte) {
            out.push(byte as char);
        } else {
            out.push_str(&format!("%{byte:02X}"));
        }
    }
    out
}

/// The query part of whatever a caller was handed: a whole explorer URL, `?query`, or
/// the bare query. A fragment is not part of the link.
pub fn query_of(link: &str) -> &str {
    let link = link.trim();
    let link = link.split_once('#').map_or(link, |(before, _)| before);
    match link.split_once('?') {
        Some((before, after)) if before.contains('/') || before.is_empty() => after,
        _ => link,
    }
}

// --------------------------------------------------------------------- the shade

/// The shade keys, read into the engine's own palette recipe — which is what they are.
fn read_shade(query: &Query) -> Result<Palette, String> {
    let mut palette = Palette::default();
    let flag = |text: &str, key: &str| match text {
        "0" => Ok(false),
        "1" => Ok(true),
        _ => Err(format!("{key} is 0 or 1; the link says {text}.")),
    };
    if let Some(text) = query.get("gamma") {
        palette.gamma = positive(text, "gamma")?;
    }
    if let Some(text) = query.get("cycles") {
        palette.cycles = positive(text, "cycles")?;
    }
    if let Some(text) = query.get("phase") {
        palette.phase = finite(text, "phase")?;
    }
    if let Some(text) = query.get("reverse") {
        palette.bake.reverse = flag(text, "reverse")?;
    }
    if let Some(text) = query.get("mirror") {
        palette.bake.mirror = flag(text, "mirror")?;
    }
    if let Some(text) = query.get("transfer") {
        palette.transfer = match tagged(text, "transfer", &["value", "edge", "rank"], "edge")? {
            ("edge", Some(weight)) => {
                if weight.is_nan() || weight < 0.0 {
                    return Err(format!(
                        "the edge transfer's weight is at least 0; the link says {text}."
                    ));
                }
                Transfer::Edge { weight }
            }
            ("rank", _) => Transfer::Rank,
            _ => Transfer::Value,
        };
    }
    if let Some(text) = query.get("rolloff") {
        palette.rolloff = match tagged(
            text,
            "rolloff",
            &["none", "soft_knee", "reinhard", "aces"],
            "soft_knee",
        )? {
            ("soft_knee", Some(knee)) => {
                if !(0.0..1.0).contains(&knee) {
                    return Err(format!(
                        "the rolloff's knee is at least 0 and below 1; the link says {text}."
                    ));
                }
                Rolloff::SoftKnee { knee }
            }
            ("reinhard", _) => Rolloff::Reinhard,
            ("aces", _) => Rolloff::Aces,
            _ => Rolloff::None,
        };
    }
    if let Some(text) = query.get("scale") {
        palette.scale = match text {
            "leveled" => Scale::Leveled,
            "absolute" => Scale::Absolute,
            _ => {
                return Err(format!(
                    "scale is one of leveled, absolute; the link says {text}."
                ));
            }
        };
    }
    if let Some(text) = query.get("lambda") {
        let value = finite(text, "lambda")?;
        if !(0.0..=1.0).contains(&value) {
            return Err(format!("lambda is between 0 and 1; the link says {text}."));
        }
        palette.lambda = value;
    }
    if let Some(text) = query.get("period") {
        palette.period = positive(text, "period")?;
    }
    Ok(palette)
}

/// `name` or `name:number`, where only `parametered` takes the number.
fn tagged(
    text: &str,
    key: &str,
    kinds: &[&'static str],
    parametered: &str,
) -> Result<(&'static str, Option<f64>), String> {
    let (kind, value) = match text.split_once(':') {
        Some((kind, value)) => (kind, Some(value)),
        None => (text, None),
    };
    let Some(&kind) = kinds.iter().find(|&&known| known == kind) else {
        return Err(format!(
            "{key} is one of {}; the link says {text}.",
            kinds.join(", ")
        ));
    };
    match (kind == parametered, value) {
        (false, None) => Ok((kind, None)),
        (false, Some(_)) => Err(format!(
            "{key}={kind} takes no value after it; the link says {text}."
        )),
        (true, None) => Err(format!(
            "{key}={kind} needs its value after a colon; the link says {text}."
        )),
        (true, Some(value)) => Ok((kind, Some(finite(value, key)?))),
    }
}

/// The shade keys a canonical link writes: the ones that are not the engine's default.
fn emit_shade(palette: &Palette, parts: &mut Vec<String>) {
    let defaults = Palette::default();
    let mut push = |key: &str, value: String| parts.push(format!("{key}={}", encode(&value)));
    if palette.gamma != defaults.gamma {
        push("gamma", js_number(palette.gamma));
    }
    if palette.cycles != defaults.cycles {
        push("cycles", js_number(palette.cycles));
    }
    if palette.phase != defaults.phase {
        push("phase", js_number(palette.phase));
    }
    if palette.bake.reverse {
        push("reverse", "1".into());
    }
    if palette.bake.mirror {
        push("mirror", "1".into());
    }
    match palette.transfer {
        Transfer::Value => {}
        Transfer::Edge { weight } => push("transfer", format!("edge:{}", js_number(weight))),
        Transfer::Rank => push("transfer", "rank".into()),
    }
    match palette.rolloff {
        Rolloff::None => {}
        Rolloff::SoftKnee { knee } => push("rolloff", format!("soft_knee:{}", js_number(knee))),
        Rolloff::Reinhard => push("rolloff", "reinhard".into()),
        Rolloff::Aces => push("rolloff", "aces".into()),
    }
    if palette.scale == Scale::Absolute {
        push("scale", "absolute".into());
    }
    if palette.lambda != defaults.lambda {
        push("lambda", js_number(palette.lambda));
    }
    if palette.period != defaults.period {
        push("period", js_number(palette.period));
    }
}

/// `readLevel`: `band_autolevel/v1:black,white,exponent,out0,out1`.
fn read_level(text: &str) -> Result<Curve, String> {
    let (operator, numbers) = match text.split_once(':') {
        Some((operator, numbers)) => (operator, Some(numbers)),
        None => (text, None),
    };
    if operator != autolevel::OPERATOR {
        return Err(format!(
            "level names {operator}, and the operators this page can replay are {}.",
            autolevel::OPERATOR
        ));
    }
    let numbers = numbers.ok_or_else(|| {
        format!("level={operator} needs its 5 numbers after a colon; the link says {text}.")
    })?;
    let parts: Vec<&str> = numbers.split(',').collect();
    if parts.len() != 5 {
        return Err(format!(
            "{operator} takes 5 numbers and the link gives {}.",
            parts.len()
        ));
    }
    let names = [
        "black_pt",
        "white_pt",
        "exponent",
        "out_ends[0]",
        "out_ends[1]",
    ];
    let mut read = [0.0; 5];
    for (at, part) in parts.iter().enumerate() {
        read[at] = finite(part, &format!("{operator}'s {}", names[at]))?;
    }
    let [black, white, exponent, low, high] = read;
    if white <= black {
        return Err(format!(
            "{operator}'s white point sits above its black point; the link says {} above {}.",
            js_number(white),
            js_number(black)
        ));
    }
    if exponent <= 0.0 {
        return Err(format!(
            "{operator}'s exponent is positive; the link says {}.",
            js_number(exponent)
        ));
    }
    Ok(Curve {
        black_pt: black,
        white_pt: white,
        exponent,
        out_ends: [low, high],
    })
}

fn emit_level(level: &Option<Curve>, palette: &Palette, parts: &mut Vec<String>) {
    if palette.scale == Scale::Absolute {
        return;
    }
    if let Some(curve) = level {
        let numbers = [
            curve.black_pt,
            curve.white_pt,
            curve.exponent,
            curve.out_ends[0],
            curve.out_ends[1],
        ]
        .map(js_number)
        .join(",");
        parts.push(format!(
            "level={}",
            encode_curve(&format!("{}:{numbers}", autolevel::OPERATOR))
        ));
    }
}

/// The palette a link names, checked against the library, and whether the shade may
/// fold it.
fn read_palette(query: &Query, palette: &Palette, context: &Context) -> Result<String, String> {
    let name = query.get("p").unwrap_or(DEFAULT_PALETTE);
    if !context.has_palette(name) {
        return Err(format!(
            "there is no palette called {name} among the ones this page carries."
        ));
    }
    if palette.bake.mirror && context.cyclic(name)? {
        return Err(format!(
            "{name} is cyclic, so folding it would halve the cycle it was drawn to have. \
             Folding is the seam fix for a map that has a seam."
        ));
    }
    Ok(name.to_string())
}

fn read_level_under(query: &Query, palette: &Palette) -> Result<Option<Curve>, String> {
    let level = query.get("level").map(read_level).transpose()?;
    // `levelUnder`: no curve under the absolute scale — parsed, so a malformed one is
    // still refused, and then dropped.
    Ok(if palette.scale == Scale::Absolute {
        None
    } else {
        level
    })
}

// ---------------------------------------------------------------- the shallow view

/// A shallow link, as `permalink.js`'s `parse` returns it.
#[derive(Clone, Debug)]
pub struct ShallowView {
    pub family: &'static str,
    /// In the family's emit order.
    pub constants: BTreeMap<&'static str, Coordinate>,
    pub mode: &'static str,
    /// By the name the link gives each; emitted in the mode's own order.
    pub params: BTreeMap<String, f64>,
    pub x: Coordinate,
    pub y: Coordinate,
    pub w: Coordinate,
    /// The link's own `n`, or `None` for the width policy.
    pub maxiter: Option<u32>,
    pub aspect: (u32, u32),
    pub palette: String,
    pub shade: Palette,
    pub level: Option<Curve>,
}

/// A link, whichever contract it is.
#[derive(Clone, Debug)]
pub enum Link {
    Shallow(ShallowView),
    Deep(DeepView),
}

/// Read a link, dispatching on the deep marker exactly as the page's door does.
pub fn parse(search: &str, context: &Context) -> Result<Link, String> {
    if Query::parse(search).has(DEEP_MARKER) {
        parse_deep(search, context).map(Link::Deep)
    } else {
        parse_shallow(search, context).map(Link::Shallow)
    }
}

impl Link {
    /// The canonical query: what the site's `canonicalize` gives for the same link.
    pub fn canonical(&self, context: &Context) -> Result<String, String> {
        match self {
            Link::Shallow(view) => view.emit(context),
            Link::Deep(view) => Ok(view.emit()),
        }
    }
}

/// `permalink.js`'s `parse`.
pub fn parse_shallow(search: &str, context: &Context) -> Result<ShallowView, String> {
    let query = Query::parse(search);
    let seen = query.keys()?;
    if seen.iter().all(|key| UI_KEYS.contains(key)) {
        return fresh(context);
    }

    let version = query.get("v").ok_or(
        "the link carries no v, so there is no way to know which set of rules it was written \
         against.",
    )?;
    let version = read_version(version, &READS).ok_or_else(|| {
        format!(
            "this page speaks permalink v{VERSION} and the link says v={version}. It was \
             written for a version of this page that no longer exists, or for one that does \
             not exist yet."
        )
    })?;

    let named = query.get("f").unwrap_or(FAMILIES[0]);
    let family = *FAMILIES.iter().find(|&&f| f == named).ok_or_else(|| {
        if named == "fractional_multibrot" {
            "fractional_multibrot is not a view: a non-integer degree is render-only.".into()
        } else {
            format!("there is no family called {named}.")
        }
    })?;

    let named = query.get("m").unwrap_or(MODES[0]);
    let mode = *MODES.iter().find(|&&m| m == named).ok_or_else(|| {
        if named == "de" {
            "de is not offered here: the distance estimate is a niche render mode.".into()
        } else {
            format!("there is no render mode called {named}.")
        }
    })?;

    let wanted = mode_parameters(mode);
    for key in &seen {
        if *key == "n" && version < 4 {
            return Err(
                "the link carries a key this page does not know: n. The iteration cap is a key \
                 from v=4 on."
                    .into(),
            );
        }
        let known = ["v", "f", "m", "x", "y", "w", "n", "a", "p", "level"].contains(key)
            || constant_keys(family).contains(key)
            || wanted.contains(key)
            || SHADE_KEYS.contains(key)
            || UI_KEYS.contains(key);
        if known {
            continue;
        }
        if CONSTANT_KEYS.contains(key) {
            return Err(format!(
                "{key} is a constant of a family this link does not name."
            ));
        }
        if PARAMETER_KEYS.contains(key) {
            return Err(format!("the {mode} render mode has no {key} parameter."));
        }
        return Err(format!(
            "the link carries a key this page does not know: {key}."
        ));
    }

    let seeds = context.seeds(family)?;
    let mut constants = BTreeMap::new();
    for &key in constant_keys(family) {
        let read = coordinate(query.get(key), key)?;
        constants.insert(key, read.unwrap_or_else(|| seeds[key].clone()));
    }
    // `both`: a pair is written whole or not at all.
    for (re, im) in CONSTANT_PAIRS {
        if !constant_keys(family).contains(&re) {
            continue;
        }
        if query.has(re) != query.has(im) {
            let (given, missing) = if query.has(re) { (re, im) } else { (im, re) };
            return Err(format!(
                "{re} and {im} are the two halves of one number, so a link carries both or \
                 neither; this one names {given} and not {missing}."
            ));
        }
    }

    let [home_x, home_y, home_w] = context.home(family)?;
    let x = coordinate(query.get("x"), "x")?.unwrap_or(home_x);
    let y = coordinate(query.get("y"), "y")?.unwrap_or(home_y);
    let w = coordinate(query.get("w"), "w")?.unwrap_or(home_w);
    if w.value.is_nan() || w.value <= 0.0 {
        return Err(format!(
            "w is the width of the view in the plane, so it has to be positive; the link says \
             {}.",
            w.text
        ));
    }

    let maxiter = query.get("n").map(read_cap).transpose()?;
    let aspect = read_aspect(query.get("a"))?;

    let mut params = BTreeMap::new();
    for &key in wanted {
        let Some(text) = query.get(key) else { continue };
        let value = finite(text, key)?;
        let (fits, says) = match key {
            "weight" | "opacity" => ((0.0..=1.0).contains(&value), "between 0 and 1"),
            "shift" => (true, "a number"),
            _ => (value > 0.0, "positive"),
        };
        if !fits {
            return Err(format!("{key} has to be {says}; the link says {text}."));
        }
        params.insert(key.to_string(), value);
    }
    if version < 3
        && let Some(derived) = derived_parameter(mode)
        && !params.contains_key(derived)
    {
        let settled = mode::params_of(&mode::resolve(mode, None)?);
        let value = settled
            .get(derived)
            .ok_or_else(|| format!("the catalog has no settled {derived} for {mode}"))?;
        params.insert(derived.to_string(), *value);
    }

    // The site checks the palette before the shade and the shade before the fold; which
    // refusal a link meets first changes its sentence and never whether it is refused.
    let shade = read_shade(&query)?;
    let palette = read_palette(&query, &shade, context)?;
    let level = read_level_under(&query, &shade)?;

    Ok(ShallowView {
        family,
        constants,
        mode,
        params,
        x,
        y,
        w,
        maxiter,
        aspect,
        palette,
        shade,
        level,
    })
}

/// `fresh(mandelbrot, smooth)`: the view a link that says nothing about the picture is.
fn fresh(context: &Context) -> Result<ShallowView, String> {
    let family = FAMILIES[0];
    let [x, y, w] = context.home(family)?;
    Ok(ShallowView {
        family,
        constants: BTreeMap::new(),
        mode: MODES[0],
        params: BTreeMap::new(),
        x,
        y,
        w,
        maxiter: None,
        aspect: DEFAULT_ASPECT,
        palette: DEFAULT_PALETTE.into(),
        shade: Palette::default(),
        level: None,
    })
}

impl ShallowView {
    /// `permalink.js`'s `emit`: keys in contract order, defaults left out.
    pub fn emit(&self, context: &Context) -> Result<String, String> {
        let [home_x, home_y, home_w] = context.home(self.family)?;
        let mut parts = vec![format!("v={VERSION}")];
        if self.family != FAMILIES[0] {
            parts.push(format!("f={}", encode(self.family)));
        }
        for &key in constant_keys(self.family) {
            parts.push(format!("{key}={}", encode(&self.constants[key].text)));
        }
        if self.mode != MODES[0] {
            parts.push(format!("m={}", encode(self.mode)));
        }
        for &key in mode_parameters(self.mode) {
            if let Some(&value) = self.params.get(key) {
                parts.push(format!("{key}={}", encode(&js_number(value))));
            }
        }
        for (key, coordinate, home) in [
            ("x", &self.x, &home_x),
            ("y", &self.y, &home_y),
            ("w", &self.w, &home_w),
        ] {
            if coordinate.text != home.text {
                parts.push(format!("{key}={}", encode(&coordinate.text)));
            }
        }
        if let Some(cap) = self.maxiter
            && cap != maxiter::for_width(self.w.value)
        {
            parts.push(format!("n={cap}"));
        }
        if self.aspect != DEFAULT_ASPECT {
            parts.push(format!("a={}:{}", self.aspect.0, self.aspect.1));
        }
        parts.push(format!("p={}", encode(&self.palette)));
        emit_shade(&self.shade, &mut parts);
        emit_level(&self.level, &self.shade, &mut parts);
        Ok(parts.join("&"))
    }

    /// The parameter a v3+ link left for the page to derive off its canvas, if any.
    ///
    /// `render-link` has no canvas to derive it off — the explorer measures the view it
    /// is showing, at the size it is showing it — so a link that leaves one out is
    /// refused there rather than drawn at a number nobody chose. Every link the page and
    /// the pipeline write carries the value in force, so this is only ever a hand-typed
    /// link.
    pub fn underived(&self) -> Option<&'static str> {
        derived_parameter(self.mode).filter(|key| !self.params.contains_key(*key))
    }

    /// The engine render this view is, at one output size.
    pub fn render_spec(
        &self,
        resolution: [u32; 2],
        supersample: u32,
        colormap_dir: PathBuf,
        output: PathBuf,
    ) -> RenderSpec {
        RenderSpec {
            schema: 1,
            family: family_spec(self.family, &self.constants),
            viewport: ViewportSpec {
                center_re: Some(self.x.text.clone()),
                center_im: Some(self.y.text.clone()),
                width: Some(self.w.text.clone()),
            },
            resolution,
            supersample,
            mode: Some(self.mode.to_string()),
            coloring: None,
            params: self.params.clone(),
            palette: self.shade,
            colormap: self.palette.clone(),
            colormap_dir,
            maxiter: self.maxiter,
            output,
            allow_unresolvable_in_f64: false,
        }
    }
}

// ------------------------------------------------------------------ exact decimals

/// An exact decimal: `±digits × 10^-scale`, `deep-fx.js`'s `{units, scale}` held as the
/// digit string rather than a `BigInt`, with trailing zeros taken off.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Decimal {
    negative: bool,
    /// No leading zeros; `"0"` for zero.
    digits: String,
    scale: u32,
}

/// `deep-fx.js`'s `MAX_SCALE`: the most fraction digits a coordinate may carry.
const MAX_SCALE: i64 = 120;

/// How many zeros an exponent may append before this reader refuses, where `deep-fx.js`
/// would build the `BigInt`. No link the site writes comes near it; a coordinate is 64
/// characters, and `1e1000` is a place no frame is at.
const MAX_INTEGER_ZEROS: i64 = 1000;

impl Decimal {
    /// `fx.parse`: `None` where the text is not a decimal or needs more than
    /// [`MAX_SCALE`] fraction digits.
    pub fn parse(text: &str) -> Option<Decimal> {
        let trimmed = text.trim();
        if trimmed.is_empty() || !is_decimal(trimmed) {
            return None;
        }
        let negative = trimmed.starts_with('-');
        let body = trimmed.trim_start_matches(['+', '-']);
        let (body, exponent) = match body.find(['e', 'E']) {
            Some(at) => {
                let written = &body[at + 1..];
                let exponent = written
                    .parse::<i64>()
                    .unwrap_or(if written.starts_with('-') {
                        i64::MIN / 2
                    } else {
                        i64::MAX / 2
                    });
                (&body[..at], exponent)
            }
            None => (body, 0),
        };
        let (whole, fraction) = body.split_once('.').unwrap_or((body, ""));
        let scale = fraction.len() as i64 - exponent;
        let mut digits = format!("{whole}{fraction}");
        if scale < 0 {
            if -scale > MAX_INTEGER_ZEROS {
                return None;
            }
            digits.push_str(&"0".repeat((-scale) as usize));
            return Some(Decimal::make(negative, digits, 0));
        }
        if scale > MAX_SCALE {
            return None;
        }
        Some(Decimal::make(negative, digits, scale as u32))
    }

    fn make(negative: bool, digits: String, mut scale: u32) -> Decimal {
        let mut digits = digits.trim_start_matches('0').to_string();
        while scale > 0 && digits.ends_with('0') {
            digits.pop();
            scale -= 1;
        }
        if digits.is_empty() {
            return Decimal {
                negative: false,
                digits: "0".into(),
                scale: 0,
            };
        }
        Decimal {
            negative,
            digits,
            scale,
        }
    }

    /// `fx.text`: a plain decimal, never an exponent.
    pub fn text(&self) -> String {
        let scale = self.scale as usize;
        let body = if scale == 0 {
            self.digits.clone()
        } else if self.digits.len() > scale {
            let split = self.digits.len() - scale;
            format!("{}.{}", &self.digits[..split], &self.digits[split..])
        } else {
            format!("0.{}{}", "0".repeat(scale - self.digits.len()), self.digits)
        };
        if self.negative {
            format!("-{body}")
        } else {
            body
        }
    }
}

// -------------------------------------------------------------------- the deep view

/// A deep link, as `deep-link.js`'s `parse` returns it.
#[derive(Clone, Debug)]
pub struct DeepView {
    pub degree: u32,
    /// The Julia parameter, where the link names one.
    pub julia: Option<(Decimal, Decimal)>,
    pub x: Decimal,
    pub y: Decimal,
    /// The width's shortest text, and the double it is.
    pub w: Coordinate,
    /// The link's own `n`, or `None` where the width's policy is to decide it.
    pub maxiter: Option<u32>,
    pub aspect: (u32, u32),
    pub palette: String,
    pub shade: Palette,
    pub level: Option<Curve>,
}

const DEEP_KNOWN: [&str; 11] = ["dv", "f", "cx", "cy", "x", "y", "w", "n", "a", "p", "level"];

fn deep_coordinate(text: &str, key: &str) -> Result<Decimal, String> {
    if utf16_len(text) > COORDINATE_LIMIT {
        return Err(format!(
            "{key} is {} characters, and a coordinate is capped at {COORDINATE_LIMIT}.",
            utf16_len(text)
        ));
    }
    Decimal::parse(text).ok_or_else(|| {
        format!(
            "{key} has to be a decimal number, with or without an exponent; the link says {text}."
        )
    })
}

/// `deep-link.js`'s `parse`.
pub fn parse_deep(search: &str, context: &Context) -> Result<DeepView, String> {
    let query = Query::parse(search);
    let seen = query.keys()?;
    let version = query
        .get(DEEP_MARKER)
        .ok_or("this is not a deep link: it carries no dv.")?;
    let version = read_version(version, &DEEP_READS).ok_or_else(|| {
        format!(
            "this page speaks the deep contract v{DEEP_VERSION} and the link says dv={version}."
        )
    })?;
    for key in &seen {
        if (*key == "f" && version < 3)
            || !(DEEP_KNOWN.contains(key) || SHADE_KEYS.contains(key) || UI_KEYS.contains(key))
        {
            return Err(format!(
                "the link carries a key the Deep tab does not know: {key}."
            ));
        }
    }

    let julia = match (query.get("cx"), query.get("cy")) {
        (None, None) => None,
        (Some(re), Some(im)) => Some((deep_coordinate(re, "cx")?, deep_coordinate(im, "cy")?)),
        _ => {
            return Err(
                "cx and cy are the two halves of one number — the c of z² + c — so a link \
                 carries both or neither."
                    .into(),
            );
        }
    };
    let degree = match query.get("f") {
        None => 2,
        Some(name) => {
            let (degree, is_julia) = match name {
                "mandelbrot" => (2, false),
                "julia" => (2, true),
                _ => match (name.strip_prefix("multibrot"), name.strip_prefix("julia")) {
                    (Some(d), _) if ["3", "4", "5", "6"].contains(&d) => {
                        (d.parse().unwrap(), false)
                    }
                    (_, Some(d)) if ["3", "4", "5", "6"].contains(&d) => (d.parse().unwrap(), true),
                    _ => return Err(format!("f is the family; the link says {name}.")),
                },
            };
            if is_julia && julia.is_none() {
                return Err(format!(
                    "{name} is a Julia set, so the link has to say which one with cx and cy."
                ));
            }
            if !is_julia && julia.is_some() {
                return Err(format!(
                    "{name} is a parameter plane, and cx and cy name a Julia set."
                ));
            }
            degree
        }
    };

    let home_family = if degree == 2 {
        "mandelbrot".to_string()
    } else {
        format!("multibrot{degree}")
    };
    let [home_x, home_y, home_w] = context.home(&home_family)?;
    let x = match (query.get("x"), &julia) {
        (Some(text), _) => deep_coordinate(text, "x")?,
        (None, Some((re, _))) => re.clone(),
        (None, None) => deep_coordinate(&home_x.text, "x")?,
    };
    let y = match (query.get("y"), &julia) {
        (Some(text), _) => deep_coordinate(text, "y")?,
        (None, Some((_, im))) => im.clone(),
        (None, None) => deep_coordinate(&home_y.text, "y")?,
    };
    let width_text = query.get("w").unwrap_or(&home_w.text);
    if utf16_len(width_text) > COORDINATE_LIMIT {
        return Err(format!(
            "w is the width of the view in the plane, and this is not one: {width_text}."
        ));
    }
    if Decimal::parse(width_text).is_none() {
        return Err(format!(
            "w has to be a decimal number; the link says {width_text}."
        ));
    }
    let width = number(width_text);
    if !(width.is_finite() && width > 0.0) {
        return Err(format!(
            "w is the width of the view in the plane, so it has to be positive; the link says \
             {width_text}."
        ));
    }
    let w = Coordinate::of(width);

    let maxiter = query.get("n").map(read_cap).transpose()?;
    let aspect = read_aspect(query.get("a"))?;
    let shade = read_shade(&query)?;
    let palette = read_palette(&query, &shade, context)?;
    let level = read_level_under(&query, &shade)?;

    Ok(DeepView {
        degree,
        julia,
        x,
        y,
        w,
        maxiter,
        aspect,
        palette,
        shade,
        level,
    })
}

impl DeepView {
    /// The family name the shallow contract would give this set.
    pub fn family(&self) -> String {
        match (self.julia.is_some(), self.degree) {
            (true, 2) => "julia".into(),
            (true, d) => format!("julia{d}"),
            (false, 2) => "mandelbrot".into(),
            (false, d) => format!("multibrot{d}"),
        }
    }

    /// `deep-link.js`'s `emit`.
    pub fn emit(&self) -> String {
        let mut parts = vec![format!("{DEEP_MARKER}={DEEP_VERSION}")];
        if self.degree != 2 {
            parts.push(format!("f={}", self.family()));
        }
        if let Some((re, im)) = &self.julia {
            parts.push(format!("cx={}", encode(&re.text())));
            parts.push(format!("cy={}", encode(&im.text())));
        }
        parts.push(format!("x={}", encode(&self.x.text())));
        parts.push(format!("y={}", encode(&self.y.text())));
        parts.push(format!("w={}", encode(&self.w.text)));
        if let Some(cap) = self.maxiter {
            parts.push(format!("n={cap}"));
        }
        if self.aspect != DEFAULT_ASPECT {
            parts.push(format!("a={}:{}", self.aspect.0, self.aspect.1));
        }
        parts.push(format!("p={}", encode(&self.palette)));
        emit_shade(&self.shade, &mut parts);
        emit_level(&self.level, &self.shade, &mut parts);
        parts.join("&")
    }
}

// ------------------------------------------------------------------ the deep seam

/// One deep frame, as a perturbation renderer is handed it.
///
/// Every coordinate is the exact decimal text the link carried, because a deep centre is a
/// place no double can hold: the renderer reads it into its own fixed point. The width is
/// a double, which is the one number down here a double still holds honestly.
pub struct DeepFrame<'a> {
    pub view: &'a DeepView,
    /// Samples across and down: the output size times the supersample.
    pub samples: [u32; 2],
}

/// One smooth lane per sample, row-major, `NaN` for interior — the layout
/// `perturb::compute_rows` writes and `engine.wasm`'s `shade_level` reads.
pub struct Lanes {
    pub width: u32,
    pub height: u32,
    pub smooth: Vec<f64>,
}

/// **The seam a deep renderer plugs into: lanes in, shading out.**
///
/// A backend computes the frame's escape field and nothing else — no colour, no
/// palette, no levelling, no file — which is the division the Deep tab already makes
/// between `perturb.wasm` and `engine.wasm`. [`shade_lanes`] is the other half and is
/// the engine's own colouring, so a deep picture is coloured by the same code as every
/// shallow one.
///
/// **What a backend has to settle before its pictures are the Deep tab's**, known today
/// and not yet built:
///
/// - **The arrival fit.** A dv link without `scale` does not open to a fixed recipe:
///   the page fits `lambda`, `period` and `phase` off the picture on screen (`fit.js`,
///   and `ArrivalRefit` once the frame is finished). A backend either ports that fit or
///   `render-link` refuses a scale-less deep link. Every Deep gallery row carries
///   `scale=absolute`, so none of them needs it.
/// - **A fresh reference orbit.** The page reuses a held orbit on the Mandelbrot side
///   when the key matches and the centre is within half a frame, so its picture can
///   depend on how the reader got there. Only a cold open — the reference at the view's
///   own centre — is reproducible, and that is what a backend should take.
/// - **Pinning `libm`.** `perturb`'s smooth count takes three `ln` a sample, and native
///   and `wasm32` `ln` are not promised to agree to the bit; nothing has measured
///   whether they do. Until something does, native lanes are "the same picture within a
///   tolerance" of the tab's and not the same bytes.
/// - **The cap.** A link without `n` leaves it to the width, and the tab's probe may
///   raise it (`policy::settle`) before the picture settles; a backend decides whether to
///   settle or to take the width's answer, and says which.
pub trait DeepBackend {
    /// What this backend is, for a report.
    fn name(&self) -> &'static str;
    /// The frame's smooth lanes.
    fn lanes(&self, frame: &DeepFrame) -> Result<Lanes, String>;
}

/// The only deep backend there is: it says so.
pub struct NotBuilt;

impl DeepBackend for NotBuilt {
    fn name(&self) -> &'static str {
        "not built"
    }

    fn lanes(&self, frame: &DeepFrame) -> Result<Lanes, String> {
        Err(format!(
            "deep rendering not built yet: this is a dv={DEEP_VERSION} link to a {} frame at \
             width {}, which the Deep tab draws by perturbation, and fractal-engine has no \
             perturbation backend. The link is parsed and canonical; open it in the explorer.",
            frame.view.family(),
            frame.view.w.text
        ))
    }
}

/// The shading half of the deep seam: lanes to linear-light RGB and down to the output
/// size, through the engine's own colouring.
///
/// The lanes are narrowed to `f32`, which is where `engine.wasm`'s `read_lanes` narrows
/// a deep field too, so a native deep picture is coloured from exactly the numbers the
/// tab's is. A deep view is `smooth`, read linearly.
pub fn shade_lanes(
    lanes: &Lanes,
    palette: &Palette,
    colormap: &Colormap,
    out: [u32; 2],
    supersample: u32,
) -> Vec<u8> {
    let field = Field {
        values: lanes.smooth.iter().map(|&value| value as f32).collect(),
        width: lanes.width,
        height: lanes.height,
    };
    let linear = coloring::toned(
        coloring::shade(&field, coloring::Transform::Linear, palette, colormap),
        palette,
    );
    resample::downsample(
        &linear,
        lanes.width as usize,
        lanes.height as usize,
        out[0] as usize,
        out[1] as usize,
        supersample,
    )
}

/// The map a view is drawn through: its stops, curved by a replayed `level=` where the
/// link carries one, then baked under the shade's own fold and flip.
pub fn colormap_for(
    context: &Context,
    name: &str,
    level: Option<&Curve>,
    bake: Bake,
) -> Result<Colormap, String> {
    let (kind, stops) = Colormap::read_stops(context.palettes(), name)?;
    match level {
        Some(curve) => {
            curve.validate()?;
            let curved = autolevel::curved_stops(&stops, curve);
            Colormap::from_stops_baked(name, kind, &curved, bake)
        }
        None => Colormap::from_stops_baked(name, kind, &stops, bake),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn data() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../data")
    }

    fn context() -> Context {
        Context::from_data(&data()).expect("the checkout's data/")
    }

    #[test]
    fn numbers_are_written_the_way_javascript_writes_them() {
        for (value, text) in [
            (0.0, "0"),
            (-0.0, "0"),
            (1.0, "1"),
            (100.0, "100"),
            (0.5, "0.5"),
            (-0.77, "-0.77"),
            (4.4, "4.4"),
            (1e-6, "0.000001"),
            (1e-7, "1e-7"),
            (1.5e-7, "1.5e-7"),
            (1e21, "1e+21"),
            (1.2345e21, "1.2345e+21"),
            (1e20, "100000000000000000000"),
            (123456.789, "123456.789"),
            (2.95e-16, "2.95e-16"),
            (0.1 + 0.2, "0.30000000000000004"),
        ] {
            assert_eq!(js_number(value), text, "{value:?}");
        }
    }

    #[test]
    fn a_decimal_is_exact_and_written_plainly() {
        for (text, back) in [
            (
                "-0.7450177282853233584294189",
                "-0.7450177282853233584294189",
            ),
            ("0.1000", "0.1"),
            ("-00.20", "-0.2"),
            ("+1.5e2", "150"),
            (".25", "0.25"),
            ("5.", "5"),
            ("1e-3", "0.001"),
            ("-0", "0"),
            ("2.5E-4", "0.00025"),
        ] {
            assert_eq!(Decimal::parse(text).expect(text).text(), back, "{text}");
        }
        assert_eq!(Decimal::parse("1e-200"), None);
        assert_eq!(Decimal::parse("0x10"), None);
    }

    #[test]
    fn a_whole_url_is_its_query() {
        assert_eq!(
            query_of("https://techmatt.github.io/fractals/explorer/?v=4&p=viridis#top"),
            "v=4&p=viridis"
        );
        assert_eq!(query_of("?v=4&p=viridis"), "v=4&p=viridis");
        assert_eq!(query_of("v=4&p=viridis"), "v=4&p=viridis");
    }

    /// **Both parsers are the site's, on every row of the fixture.** Each row is a link
    /// and what `permalink.js` or `deep-link.js` made of it, recorded by running the
    /// site's own modules — `fixtures/link-cases.json` carries the generator and the
    /// website commit it ran at. A row the site refused is refused here; a row it read is
    /// read to the same view and settles to the same canonical string, byte for byte.
    #[test]
    fn the_parsers_are_the_sites() {
        let fixture = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fixtures/link-cases.json");
        // Read exactly: the fixture's numbers are JavaScript's shortest spellings of the
        // doubles the site held, and this compares doubles to the bit.
        let cases = crate::exact_json::exactly(
            &std::fs::read_to_string(&fixture).expect("link-cases.json"),
        );
        let context = context();
        let mut checked = 0;
        for case in cases["cases"].as_array().expect("cases") {
            let query = case["query"].as_str().expect("a query");
            let parsed = parse(query, &context);
            if case["ok"] == false {
                assert!(
                    parsed.is_err(),
                    "{query}: the site refused ({}) and this read it",
                    case["why"]
                );
                checked += 1;
                continue;
            }
            let link = parsed.unwrap_or_else(|why| panic!("{query}: the site read it, and: {why}"));
            let canonical = link.canonical(&context).expect("a canonical string");
            assert_eq!(
                canonical,
                case["canonical"].as_str().unwrap(),
                "{query}: canonical"
            );
            let view = &case["view"];
            match (&link, case["deep"].as_bool().unwrap()) {
                (Link::Shallow(ours), false) => {
                    assert_eq!(ours.family, view["family"], "{query}");
                    assert_eq!(ours.mode, view["mode"], "{query}");
                    assert_eq!(ours.x.text, view["x"], "{query}");
                    assert_eq!(ours.y.text, view["y"], "{query}");
                    assert_eq!(ours.w.text, view["w"], "{query}");
                    for (key, text) in view["constants"].as_object().unwrap() {
                        assert_eq!(ours.constants[key.as_str()].text, *text, "{query}: {key}");
                    }
                    let params: BTreeMap<String, f64> =
                        serde_json::from_value(view["params"].clone()).unwrap();
                    assert_eq!(ours.params, params, "{query}: params");
                    assert_eq!(
                        ours.maxiter.map(u64::from),
                        view["maxiter"].as_u64(),
                        "{query}"
                    );
                }
                (Link::Deep(ours), true) => {
                    assert_eq!(ours.degree as u64, view["degree"].as_u64().unwrap());
                    assert_eq!(ours.x.text(), view["x"], "{query}");
                    assert_eq!(ours.y.text(), view["y"], "{query}");
                    assert_eq!(ours.w.text, view["w"], "{query}");
                    let julia = ours.julia.as_ref().map(|(re, im)| [re.text(), im.text()]);
                    let theirs: Option<[String; 2]> =
                        serde_json::from_value(view["julia"].clone()).unwrap();
                    assert_eq!(julia, theirs, "{query}: julia");
                    assert_eq!(
                        ours.maxiter.map(u64::from),
                        view["maxiter"].as_u64(),
                        "{query}"
                    );
                }
                _ => panic!("{query}: the site and this disagree about which contract it is"),
            }
            // Shared by both: the aspect, the palette, the shade and the curve.
            let (aspect, palette, shade, level) = match &link {
                Link::Shallow(v) => (v.aspect, &v.palette, v.shade, v.level),
                Link::Deep(v) => (v.aspect, &v.palette, v.shade, v.level),
            };
            assert_eq!(
                [aspect.0, aspect.1],
                [
                    view["aspect"][0].as_u64().unwrap() as u32,
                    view["aspect"][1].as_u64().unwrap() as u32
                ]
            );
            assert_eq!(palette, view["palette"].as_str().unwrap(), "{query}");
            let theirs: Palette = serde_json::from_value(view["shade"].clone())
                .unwrap_or_else(|e| panic!("{query}: the site's shade reads as a palette: {e}"));
            assert_eq!(shade, theirs, "{query}: shade");
            match (level, view["level"].is_null()) {
                (None, true) => {}
                (Some(curve), false) => {
                    let held = &view["level"];
                    assert_eq!(curve.black_pt, held["black_pt"].as_f64().unwrap());
                    assert_eq!(curve.white_pt, held["white_pt"].as_f64().unwrap());
                    assert_eq!(curve.exponent, held["exponent"].as_f64().unwrap());
                    assert_eq!(curve.out_ends[0], held["out_ends"][0].as_f64().unwrap());
                    assert_eq!(curve.out_ends[1], held["out_ends"][1].as_f64().unwrap());
                }
                _ => panic!("{query}: level"),
            }
            checked += 1;
        }
        assert!(
            checked >= 500,
            "the fixture is the spread it claims: {checked}"
        );
    }

    /// The deep seam refuses by name, and its shading half is the engine's colouring:
    /// a backend that hands over the engine's own smooth field gets the engine's own
    /// smooth picture, byte for byte.
    #[test]
    fn the_deep_seam_shades_lanes_the_way_a_render_does() {
        let context = context();
        let Link::Deep(view) = parse("dv=3&x=-0.5&y=0&w=3&p=viridis", &context).unwrap() else {
            panic!("a deep link")
        };
        let frame = DeepFrame {
            view: &view,
            samples: [64, 36],
        };
        let refused = NotBuilt.lanes(&frame).err().expect("refused");
        assert!(
            refused.starts_with("deep rendering not built yet"),
            "{refused}"
        );

        let family = crate::family::Family::Multibrot { degree: 2 };
        let viewport = crate::viewport::Viewport {
            center: num_complex::Complex::new(-0.5, 0.0),
            width: 3.0,
            out_width: 32,
            out_height: 18,
            supersample: 2,
        };
        let map = colormap_for(&context, "viridis", None, Bake::default()).unwrap();
        let palette = Palette::default();
        let smooth = mode::resolve("smooth", Some(&family)).unwrap();
        let painted =
            coloring::paint(&viewport, &family, 500, &smooth, &palette, &map).expect("painted");
        let expected = resample::downsample(&painted.linear, 64, 36, 32, 18, 2);
        let sampled =
            crate::field::render_field(&viewport, &family, 500, crate::field::FieldSpec::Smooth);
        let lanes = Lanes {
            width: 64,
            height: 36,
            smooth: sampled.fields[0].values.iter().map(|&v| v as f64).collect(),
        };
        assert_eq!(shade_lanes(&lanes, &palette, &map, [32, 18], 2), expected);
    }
}
