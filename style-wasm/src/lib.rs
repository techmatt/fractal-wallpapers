//! The style compositor as a raw `wasm32-unknown-unknown` module.
//!
//! A page opens a **session** on one picture — a location, a published style with its
//! knobs turned, a colormap, a size — and draws it in two steps, the split the
//! compositor is built on ([`fractal_engine::style::Measures`]):
//!
//! ```text
//! open(request)                 -> JSON      the picture this request implies, or why not
//! measure(h, width, height, ss) -> JSON      every frame-wide statistic, the tone curve
//!                                            with them, over a frame of the same view
//! tile(h, x, y, width, height)  -> RGBA      output pixels of the picture, against them
//! frame(h)                      -> RGBA      the whole picture in one pass: measure and
//!                                            tile at once, as the native engine draws it
//! close(h)
//! ```
//!
//! `measure` at the picture's own size (`0, 0, 0`) makes the tiles stitch to `frame`'s
//! bytes, which are the native engine's; at a smaller size of the same aspect it is a
//! preview's balance at full detail for the preview's cost, which is what lets an
//! explorer draw progressively and settle later.
//!
//! **The request is the CLI's inputs, not the engine's spec.** What a `style render`
//! does to a style file before the engine sees it — a location's own projection
//! members ([`projected`], after `styles.projected`), then the knobs ([`with_knobs`],
//! after `styles.with_knobs`, so a knob wins over a record), and the fold of a sequential map under a repeating palette
//! layer ([`mirrored`], after `styles.spec_of`) — happens here, so a page hands over
//! the bundle's style and a knob setting and gets the pipeline's picture.
//!
//! Every number then crosses into the engine as JSON text through
//! [`RenderSpec::parse`], exactly as a native render's spec does: the same digits
//! read by the same parser to the same bits. Results are JSON behind a four-byte
//! little-endian length, as the website's `engine-wasm` returns them; a tile is bare
//! RGBA, `width · height · 4` bytes, and a null pointer means [`last_error`] says why.

use std::collections::BTreeMap;
use std::sync::Mutex;

use fractal_engine::coloring::Palette;
use fractal_engine::colormap::{Colormap, Kind};
use fractal_engine::family::Family;
use fractal_engine::resample::{self, Crop};
use fractal_engine::spec::RenderSpec;
use fractal_engine::style::{self, Measures, Style};
use fractal_engine::viewport::Viewport;
use serde::Deserialize;
use serde_json::value::RawValue;
use serde_json::{Map, Value, json};

// ------------------------------------------------------------------------ the request

/// One picture, as the page asks for it.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub schema: u32,
    /// A location record, as `style render --location` reads one: `family`, `viewport`,
    /// optionally `maxiter` and the place's own `projection` members. Anything else a
    /// record carries (`name`, `note`) is provenance and ignored.
    pub location: Location,
    /// The stack: a style file's `style` member, the bundle's `stack`.
    pub style: Value,
    /// The knobs the stack exposes, a style file's `public.knobs`.
    #[serde(default)]
    pub knobs: Vec<Value>,
    /// Knob settings, `{name: value}`; each must be a knob above, inside its range.
    ///
    /// Read as text and parsed by `str::parse`, which is exact: serde_json's default
    /// reader can land a 17-digit decimal one unit of last place away, and a knob's
    /// write is arithmetic on the value, where `styles.with_knobs` has Python's exact
    /// one. (The stack itself is parsed the default way on purpose: the native engine
    /// reads it so.)
    #[serde(default)]
    pub settings: BTreeMap<String, Box<RawValue>>,
    /// A colormap file's own shape (`data/palettes/<name>.json`); its other members
    /// (`source`, `schema`) are allowed and ignored.
    pub colormap: ColormapSpec,
    /// `[width, height]` in output pixels.
    pub resolution: [u32; 2],
    #[serde(default = "one")]
    pub supersample: u32,
}

#[derive(Debug, Deserialize)]
pub struct Location {
    pub family: Value,
    #[serde(default)]
    pub viewport: Option<Value>,
    #[serde(default)]
    pub maxiter: Option<u32>,
    #[serde(default)]
    pub projection: Option<Value>,
}

#[derive(Debug, Deserialize)]
pub struct ColormapSpec {
    pub name: String,
    pub kind: Kind,
    pub stops: Vec<(f64, [u8; 3])>,
}

fn one() -> u32 {
    1
}

// ------------------------------------------------------------------ the CLI's rules

/// One step of a concrete path into a stack.
#[derive(Clone, Debug)]
enum Step {
    Index(usize),
    Key(String),
}

/// Every concrete path a knob pointer names in a stack, as `styles.targets` finds them.
///
/// `/`-separated, list indices as numbers; a `*` step matches every member of that list
/// or object under which the rest of the pointer exists.
fn targets(stack: &Value, pointer: &str) -> Vec<Vec<Step>> {
    fn walk(node: &Value, rest: &[&str], at: &mut Vec<Step>, found: &mut Vec<Vec<Step>>) {
        let (step, more) = (rest[0], &rest[1..]);
        let keys: Vec<Step> = match (step, node) {
            ("*", Value::Array(items)) => (0..items.len()).map(Step::Index).collect(),
            ("*", Value::Object(map)) => map.keys().cloned().map(Step::Key).collect(),
            ("*", _) => Vec::new(),
            (_, Value::Array(items)) => match step.parse::<usize>() {
                Ok(i) if step.bytes().all(|b| b.is_ascii_digit()) && i < items.len() => {
                    vec![Step::Index(i)]
                }
                _ => Vec::new(),
            },
            (_, Value::Object(map)) if map.contains_key(step) => vec![Step::Key(step.into())],
            _ => Vec::new(),
        };
        for key in keys {
            let child = match &key {
                Step::Index(i) => &node[*i],
                Step::Key(k) => &node[k.as_str()],
            };
            at.push(key);
            if more.is_empty() {
                found.push(at.clone());
            } else if child.is_object() || child.is_array() {
                walk(child, more, at, found);
            }
            at.pop();
        }
    }
    let steps: Vec<&str> = pointer.split('/').filter(|s| !s.is_empty()).collect();
    let mut found = Vec::new();
    if !steps.is_empty() {
        walk(stack, &steps, &mut Vec::new(), &mut found);
    }
    found
}

fn at_mut<'a>(mut node: &'a mut Value, path: &[Step]) -> &'a mut Value {
    for step in path {
        node = match step {
            Step::Index(i) => &mut node[*i],
            Step::Key(k) => &mut node[k.as_str()],
        };
    }
    node
}

/// The stack's members the engine reads as integers: `inside.iterations`, a bubble's
/// `hit`, the lines' `settle`, a checker's `sectors`, a projection's `turns`.
///
/// A knob's write to one of these is rounded half to even, by the member's name, on both
/// sides: `styles.INTEGER_MEMBERS` is the same list and `styles.with_knobs` rounds the
/// same way (`tests/test_style_wasm.py` holds the two lists equal).
pub const INTEGER_MEMBERS: [&str; 5] = ["iterations", "hit", "settle", "sectors", "turns"];

/// The stack turned to `settings`, as `styles.with_knobs` turns it: each knob writes
/// `scale·value + offset` to every member its pointers name, rounded half to even where
/// the member is an integer ([`INTEGER_MEMBERS`]). Knobs are applied in the order
/// `knobs` lists them.
pub fn with_knobs(
    stack: &Value,
    knobs: &[Value],
    settings: &BTreeMap<String, f64>,
) -> Result<Value, String> {
    let mut stack = stack.clone();
    let name_of = |knob: &Value| knob["name"].as_str().unwrap_or("?").to_string();
    for name in settings.keys() {
        if !knobs.iter().any(|knob| name_of(knob) == *name) {
            let offered: Vec<String> = knobs.iter().map(name_of).collect();
            let offered = if offered.is_empty() {
                "none".to_string()
            } else {
                offered.join(", ")
            };
            return Err(format!(
                "this style has no knob '{name}'; it has: {offered}"
            ));
        }
    }
    for knob in knobs {
        let name = name_of(knob);
        let Some(&value) = settings.get(&name) else {
            continue;
        };
        let (low, high) = (
            knob["range"][0].as_f64().unwrap_or(f64::NAN),
            knob["range"][1].as_f64().unwrap_or(f64::NAN),
        );
        if !(low <= value && value <= high) {
            return Err(format!(
                "knob '{name}' is {low}..{high}; {value} is outside it"
            ));
        }
        let writes = knob["set"].as_array().cloned().unwrap_or_default();
        for target in writes {
            let (path, scale, offset) = match &target {
                Value::String(path) => (path.clone(), 1.0, 0.0),
                _ => (
                    target["path"].as_str().unwrap_or_default().to_string(),
                    target.get("scale").and_then(Value::as_f64).unwrap_or(1.0),
                    target.get("offset").and_then(Value::as_f64).unwrap_or(0.0),
                ),
            };
            let number = scale * value + offset;
            for place in targets(&stack, &path) {
                let whole = matches!(place.last(), Some(Step::Key(key))
                    if INTEGER_MEMBERS.contains(&key.as_str()));
                *at_mut(&mut stack, &place) = if whole {
                    json!(number.round_ties_even() as i64)
                } else {
                    json!(number)
                };
            }
        }
    }
    Ok(stack)
}

/// The stack, its projection's members overridden by the location's own, as
/// `styles.projected` lays them: a style without a projection ignores the record's.
pub fn projected(stack: &Value, overrides: Option<&Value>) -> Value {
    let overrides = overrides
        .and_then(Value::as_object)
        .filter(|o| !o.is_empty());
    let own = stack
        .get("projection")
        .and_then(Value::as_object)
        .filter(|o| !o.is_empty());
    let (Some(overrides), Some(own)) = (overrides, own) else {
        return stack.clone();
    };
    let merged: Map<String, Value> = own
        .iter()
        .map(|(kind, members)| {
            let mut members = members.as_object().cloned().unwrap_or_default();
            if let Some(Value::Object(more)) = overrides.get(kind) {
                for (key, value) in more {
                    members.insert(key.clone(), value.clone());
                }
            }
            (kind.clone(), Value::Object(members))
        })
        .collect();
    let mut stack = stack.clone();
    stack["projection"] = Value::Object(merged);
    stack
}

/// Whether the render folds its map, as `styles.spec_of` decides: a sequential map is
/// mirrored only when a palette layer runs it more than once.
pub fn mirrored(stack: &Value, kind: Kind) -> bool {
    let repeats = stack["layers"].as_array().is_some_and(|layers| {
        layers.iter().any(|layer| {
            layer["kind"] == "palette"
                && layer["palette"]
                    .get("cycles")
                    .and_then(Value::as_f64)
                    .unwrap_or(1.0)
                    > 1.0
        })
    });
    repeats && kind != Kind::Cyclic
}

// --------------------------------------------------------------------- the session

/// One picture, resolved: what every export after `open` draws.
pub struct Session {
    pub family: Family,
    pub view: Viewport,
    pub maxiter: u32,
    pub style: Style,
    pub palette: Palette,
    pub colormap: Colormap,
    /// The stack as drawn — knobs turned, projection laid over — for the page's record.
    pub drawn: Value,
    pub measures: Option<Measures>,
}

impl Session {
    /// Resolve a request through the CLI's rules and the engine's own spec reader.
    pub fn open(request: &str) -> Result<Session, String> {
        let request: Request =
            serde_json::from_str(request).map_err(|e| format!("request: {e}"))?;
        if request.schema != 1 {
            return Err(format!("request has schema {}, expected 1", request.schema));
        }
        let settings = request
            .settings
            .iter()
            .map(|(name, raw)| match raw.get().trim().parse::<f64>() {
                Ok(value) if value.is_finite() => Ok((name.clone(), value)),
                _ => Err(format!(
                    "knob '{name}' is set to {}, not a number",
                    raw.get()
                )),
            })
            .collect::<Result<BTreeMap<String, f64>, String>>()?;
        // The record's own projection first, then the knobs: a knob asked for wins over
        // a record carrying the same member (a keep whose record carries `turns` beside
        // a `turns` knob), as `styles.spec_of` turns them.
        let stack = projected(&request.style, request.location.projection.as_ref());
        let stack = with_knobs(&stack, &request.knobs, &settings)?;
        let colormap = &request.colormap;
        let mut spec = json!({
            "schema": 1,
            "family": request.location.family,
            "resolution": request.resolution,
            "supersample": request.supersample,
            "style": stack,
            "colormap": colormap.name,
            "output": "style-wasm",
        });
        if let Some(viewport) = &request.location.viewport {
            spec["viewport"] = viewport.clone();
        }
        if let Some(maxiter) = request.location.maxiter {
            spec["maxiter"] = json!(maxiter);
        }
        if mirrored(&stack, colormap.kind) {
            spec["palette"] = json!({"mirror": true});
        }
        // Through text, as a native render's spec reaches the engine.
        let resolved = RenderSpec::parse(&spec.to_string())?.resolve()?;
        let style = resolved.style.ok_or("the request draws no style")?;
        let colormap = Colormap::from_stops_baked(
            colormap.name.clone(),
            colormap.kind,
            &colormap.stops,
            resolved.palette.bake,
        )?;
        Ok(Session {
            family: resolved.family,
            view: resolved.view,
            maxiter: resolved.maxiter,
            style,
            palette: resolved.palette,
            colormap,
            drawn: stack,
            measures: None,
        })
    }

    /// What `open` reports: the picture's shape and the stack as drawn.
    pub fn summary(&self) -> Value {
        json!({
            "ok": true,
            "maxiter": self.maxiter,
            "resolution": [self.view.out_width, self.view.out_height],
            "supersample": self.view.supersample,
            "samples": [self.view.sample_width(), self.view.sample_height()],
            "mirror": self.palette.bake.mirror,
            "style": self.drawn,
        })
    }

    /// Measure over a frame of this view at `width × height`, supersample `ss`; zeros
    /// mean the picture's own size, which is what makes tiles stitch to [`Self::frame`].
    pub fn measure(&mut self, width: u32, height: u32, ss: u32) -> Result<Value, String> {
        let view = if width == 0 || height == 0 {
            self.view
        } else {
            Viewport {
                out_width: width,
                out_height: height,
                supersample: ss.max(1),
                ..self.view
            }
        };
        let measures = style::measure(
            &view,
            &self.family,
            self.maxiter,
            &self.style,
            &self.colormap,
        )?;
        let report = json!({
            "ok": true,
            "measured": [view.out_width, view.out_height],
            "supersample": view.supersample,
            "tone": measures.tone_curve().map(|(b, g)| json!({"b": b, "g": g})),
            "interior_fraction": measures.interior_fraction,
        });
        self.measures = Some(measures);
        Ok(report)
    }

    /// Output pixels `crop` of the picture, RGB, against the last [`Self::measure`].
    pub fn tile(&self, crop: Crop) -> Result<Vec<u8>, String> {
        let measures = self
            .measures
            .as_ref()
            .ok_or("measure before drawing a tile: the tiles are composited against it")?;
        style::tile(
            &self.view,
            &self.family,
            self.maxiter,
            &self.style,
            &self.palette,
            &self.colormap,
            measures,
            crop,
        )
    }

    /// The whole picture in one pass, RGB: the native `render`'s own path.
    pub fn frame(&self) -> Result<Vec<u8>, String> {
        let painted = style::paint(
            &self.view,
            &self.family,
            self.maxiter,
            &self.style,
            &self.palette,
            &self.colormap,
        )?;
        Ok(resample::downsample(
            &painted.linear,
            self.view.sample_width() as usize,
            self.view.sample_height() as usize,
            self.view.out_width as usize,
            self.view.out_height as usize,
            self.view.supersample,
        ))
    }
}

// --------------------------------------------------------------------- the exports

static SESSIONS: Mutex<Vec<Option<Session>>> = Mutex::new(Vec::new());
static LAST_ERROR: Mutex<String> = Mutex::new(String::new());

fn failed(why: String) -> *mut u8 {
    *LAST_ERROR.lock().unwrap() = why;
    std::ptr::null_mut()
}

/// Run `run` on one session **with the table unlocked**: the session is taken out for the
/// call and put back after. Under `panic = "abort"` a trap mid-render (memory, a bug)
/// never returns, so a lock held across the render would stay held and every later call
/// on the instance would trap too; this way only that one session is lost.
fn with_session<T>(handle: u32, run: impl FnOnce(&mut Session) -> T) -> Result<T, String> {
    let slot = handle.checked_sub(1).map(|i| i as usize);
    let taken = slot.and_then(|i| SESSIONS.lock().unwrap().get_mut(i).and_then(Option::take));
    let mut session = taken.ok_or_else(|| format!("no open session {handle}"))?;
    let result = run(&mut session);
    if let Some(i) = slot {
        SESSIONS.lock().unwrap()[i] = Some(session);
    }
    Ok(result)
}

/// Open a session on one picture. JSON: `{ok, handle, maxiter, resolution, supersample,
/// samples, mirror, style}`, or `{ok: false, why}`.
///
/// Exported as `open` on wasm32 only: a native unmangled `open` (and `close`) would
/// replace the C library's own on Linux and macOS, which rustc refuses to compile.
#[cfg_attr(target_arch = "wasm32", unsafe(export_name = "open"))]
pub extern "C" fn open_session(request_ptr: *const u8, request_len: usize) -> *mut u8 {
    let report = match text(request_ptr, request_len).and_then(|t| Session::open(&t)) {
        Ok(session) => {
            let mut summary = session.summary();
            // A handle is never reused, so a closed picture's handle cannot reach another.
            let mut sessions = SESSIONS.lock().unwrap();
            sessions.push(Some(session));
            summary["handle"] = json!(sessions.len());
            summary
        }
        Err(why) => json!({"ok": false, "why": why}),
    };
    release_text(&report.to_string())
}

/// Measure the session's view over a `width × height` frame at supersample `ss`
/// (zeros: the picture's own). JSON: `{ok, measured, supersample, tone, interior_fraction}`.
#[unsafe(no_mangle)]
pub extern "C" fn measure(handle: u32, width: u32, height: u32, ss: u32) -> *mut u8 {
    let report = match with_session(handle, |s| s.measure(width, height, ss)).and_then(|r| r) {
        Ok(report) => report,
        Err(why) => json!({"ok": false, "why": why}),
    };
    release_text(&report.to_string())
}

/// Output pixels `[x, x + width) × [y, y + height)` as RGBA, `width · height · 4`
/// bytes; null when it cannot be drawn ([`last_error`]).
#[unsafe(no_mangle)]
pub extern "C" fn tile(handle: u32, x: u32, y: u32, width: u32, height: u32) -> *mut u8 {
    let crop = Crop {
        x: x as usize,
        y: y as usize,
        width: width as usize,
        height: height as usize,
    };
    match with_session(handle, |s| s.tile(crop)).and_then(|r| r) {
        Ok(rgb) => release(rgba(&rgb)),
        Err(why) => failed(why),
    }
}

/// The whole picture in one pass as RGBA; null when it cannot be drawn.
#[unsafe(no_mangle)]
pub extern "C" fn frame(handle: u32) -> *mut u8 {
    match with_session(handle, |s| s.frame()).and_then(|r| r) {
        Ok(rgb) => release(rgba(&rgb)),
        Err(why) => failed(why),
    }
}

/// Free a session. Exported as `close` on wasm32 only, as [`open_session`] is `open`.
#[cfg_attr(target_arch = "wasm32", unsafe(export_name = "close"))]
pub extern "C" fn close_session(handle: u32) {
    let mut sessions = SESSIONS.lock().unwrap();
    if let Some(slot) = handle
        .checked_sub(1)
        .and_then(|i| sessions.get_mut(i as usize))
    {
        // The slot stays, empty: its handle is spent.
        *slot = None;
    }
}

/// Why the last null came back, as length-prefixed text.
#[unsafe(no_mangle)]
pub extern "C" fn last_error() -> *mut u8 {
    release_text(&LAST_ERROR.lock().unwrap())
}

#[unsafe(no_mangle)]
pub extern "C" fn alloc(len: usize) -> *mut u8 {
    let mut buffer = Vec::<u8>::with_capacity(len);
    let ptr = buffer.as_mut_ptr();
    std::mem::forget(buffer);
    ptr
}

/// # Safety
/// `ptr` must come from [`alloc`] or a returned buffer, with that buffer's length.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn dealloc(ptr: *mut u8, len: usize) {
    unsafe { drop(Vec::from_raw_parts(ptr, 0, len)) }
}

// ------------------------------------------------------------------- the plumbing

fn text(ptr: *const u8, len: usize) -> Result<String, String> {
    if ptr.is_null() {
        return Err("no request was written to the heap".into());
    }
    let raw = unsafe { std::slice::from_raw_parts(ptr, len) };
    std::str::from_utf8(raw)
        .map(str::to_string)
        .map_err(|_| "the request is not valid UTF-8".into())
}

/// Hand a `Vec` to JavaScript at exactly its length, which `dealloc` frees it at.
fn release(mut bytes: Vec<u8>) -> *mut u8 {
    bytes.shrink_to_fit();
    let ptr = bytes.as_mut_ptr();
    std::mem::forget(bytes);
    ptr
}

/// Four bytes of little-endian length, then the UTF-8.
fn release_text(text: &str) -> *mut u8 {
    let raw = text.as_bytes();
    let mut bytes = Vec::with_capacity(raw.len() + 4);
    bytes.extend_from_slice(&(raw.len() as u32).to_le_bytes());
    bytes.extend_from_slice(raw);
    release(bytes)
}

fn rgba(rgb: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(rgb.len() / 3 * 4);
    for pixel in rgb.chunks_exact(3) {
        out.extend_from_slice(pixel);
        out.push(255);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_star_pointer_finds_every_member_under_which_the_rest_exists() {
        let stack = json!({"layers": [{"light": {"azimuth": 10.0}}, {"hit": 1, "opacity": 1},
                                      {"light": {}}]});
        let found = targets(&stack, "/layers/*/light/azimuth");
        assert_eq!(found.len(), 1);
        let knobs = vec![json!({"name": "a", "range": [0.0, 360.0],
            "set": ["/layers/*/light/azimuth", {"path": "/layers/1/hit", "scale": 0.5},
                    {"path": "/layers/1/opacity", "scale": 0.1}]})];
        let settings = BTreeMap::from([("a".to_string(), 5.0)]);
        let turned = with_knobs(&stack, &knobs, &settings).unwrap();
        assert_eq!(turned["layers"][0]["light"]["azimuth"], json!(5.0));
        // An integer member is rounded half to even; any other takes the number, even
        // where the page's JSON spelled it `1`.
        assert_eq!(turned["layers"][1]["hit"], json!(2));
        assert_eq!(turned["layers"][1]["opacity"], json!(0.5));
        let wide = BTreeMap::from([("a".to_string(), 400.0)]);
        assert!(with_knobs(&stack, &knobs, &wide).is_err());
        let unknown = BTreeMap::from([("b".to_string(), 1.0)]);
        assert!(with_knobs(&stack, &knobs, &unknown).is_err());
    }

    #[test]
    fn a_location_projection_lays_over_the_style_s_member_by_member() {
        let stack = json!({"projection": {"log_polar": {"turns": 4, "twist": 0.0}}});
        let place = json!({"log_polar": {"twist": 0.2}});
        let laid = projected(&stack, Some(&place));
        assert_eq!(
            laid["projection"]["log_polar"],
            json!({"turns": 4, "twist": 0.2})
        );
        let straight = json!({"layers": []});
        assert_eq!(projected(&straight, Some(&place)), straight);
    }

    #[test]
    fn a_knob_wins_over_the_record_s_own_projection_member() {
        // A keep whose record carries `turns` must not silence the style's `turns`
        // knob on the page: the record is laid first, then the knob.
        let request = json!({
            "schema": 1,
            "location": {"family": {"kind": "mandelbrot"},
                         "viewport": {"center_re": "-1.5437", "center_im": "0",
                                      "width": "0.05"}, "maxiter": 300,
                         "projection": {"log_polar": {"turns": 8, "twist": 0.1}}},
            "style": {"name": "x",
                      "projection": {"log_polar": {"turns": 5}},
                      "layers": [{"kind": "palette",
                                  "channel": {"field": {"kind": "smooth"}}}]},
            "knobs": [{"name": "turns", "range": [3.0, 6.0],
                       "set": ["/projection/log_polar/turns"]}],
            "settings": {"turns": 4},
            "colormap": {"name": "ramp", "kind": "sequential", "source": "a test",
                         "stops": [[0.0, [10, 20, 60]], [1.0, [250, 240, 200]]]},
            "resolution": [8, 5],
            "supersample": 1,
        });
        let session = Session::open(&request.to_string()).unwrap();
        assert_eq!(
            session.drawn["projection"]["log_polar"],
            json!({"turns": 4, "twist": 0.1})
        );
    }

    #[test]
    fn tiles_against_the_frame_s_own_measures_are_the_frame() {
        let request = json!({
            "schema": 1,
            "location": {"family": {"kind": "mandelbrot"},
                         "viewport": {"center_re": "-0.745", "center_im": "0.112",
                                      "width": "0.01"}, "maxiter": 600, "name": "x"},
            "style": {"name": "x", "layers": [
                {"kind": "palette", "channel": {"field": {"kind": "smooth"}},
                 "palette": {"transfer": {"kind": "rank"}, "cycles": 2.0}},
                {"kind": "glow", "channel": {"field": {"kind": "de"}}, "falloff": 0.002,
                 "color": {"palette": 0.9}, "blend": "screen", "opacity": 1}],
              "tone": {"median": 0.4, "p10": 0.05}},
            "knobs": [{"name": "glow", "range": [0.0, 1.0],
                       "set": ["/layers/1/opacity"]}],
            "settings": {"glow": 0.7},
            "colormap": {"name": "ramp", "kind": "sequential", "source": "a test",
                         "stops": [[0.0, [10, 20, 60]], [1.0, [250, 240, 200]]]},
            "resolution": [29, 17],
            "supersample": 2,
        });
        let mut session = Session::open(&request.to_string()).unwrap();
        assert!(
            session.palette.bake.mirror,
            "a repeating layer folds a sequential map"
        );
        assert_eq!(session.drawn["layers"][1]["opacity"], json!(0.7));
        let whole = session.frame().unwrap();
        assert!(
            session
                .tile(Crop {
                    x: 0,
                    y: 0,
                    width: 1,
                    height: 1
                })
                .is_err()
        );
        session.measure(0, 0, 0).unwrap();
        let mut stitched = vec![0u8; whole.len()];
        for (y, height) in [(0, 8), (8, 9)] {
            let rgb = session
                .tile(Crop {
                    x: 0,
                    y,
                    width: 29,
                    height,
                })
                .unwrap();
            stitched[y * 29 * 3..(y + height) * 29 * 3].copy_from_slice(&rgb);
        }
        assert_eq!(stitched, whole);
    }
}
