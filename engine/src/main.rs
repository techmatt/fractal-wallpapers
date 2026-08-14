//! `fractal-engine` — the command line around the render pipeline.
//!
//! ```text
//! fractal-engine render     [spec.json]   # a location and a coloring → a PNG
//! fractal-engine dump-field [spec.json]   # the same, stopping at the raw field
//! fractal-engine recolor    [spec.json]   # a dumped field → a PNG, no iteration
//! fractal-engine modes                    # what the named colorings are
//! ```
//!
//! One JSON object in, one file out, and a JSON report on stdout describing what
//! happened. The report is the record: it carries the location's decimal strings
//! back unchanged alongside the values the engine filled in for itself, so a
//! render can be repeated from its own output.
//!
//! `dump-field` and `recolor` are the two halves of one idea. Iterating is
//! expensive and coloring is not, so a field is worth keeping: dump it once,
//! then try palettes against it for the cost of a pass over memory. They are an
//! exploration tool and stop there — no cache, no index, nothing to maintain.

use std::io::Read;
use std::path::Path;
use std::time::Instant;

use serde::Serialize;

use fractal_engine::{
    coloring::{self, Coloring},
    colormap::Colormap,
    dump, field, mode, resample,
    spec::{Location, RecolorSpec, RenderSpec},
};

/// What a render did, printed to stdout as one JSON object.
#[derive(Serialize)]
struct RenderReport {
    schema: u32,
    location: Location,
    resolution: [u32; 2],
    supersample: u32,
    maxiter: u32,
    /// The mode's name, when the render asked for one by name.
    #[serde(skip_serializing_if = "Option::is_none")]
    mode: Option<String>,
    /// The coloring in full, named or not — this is what determines the picture.
    coloring: Coloring,
    colormap: String,
    /// Share of samples whose orbit never escaped — a one-number sanity check on
    /// a render, and the first thing to look at when a frame comes out flat.
    interior_fraction: f64,
    output: String,
    seconds: RenderSeconds,
}

#[derive(Serialize)]
struct RenderSeconds {
    /// Iterate and color. One number, because the strange modes interleave the
    /// two and splitting them would be reporting an implementation detail.
    paint: f64,
    resample: f64,
}

/// What a field dump did.
#[derive(Serialize)]
struct DumpReport {
    schema: u32,
    field: String,
    record: String,
    samples: [u32; 2],
    seconds: f64,
}

/// One entry of the mode catalog, as `modes` prints it.
#[derive(Serialize)]
struct Mode {
    name: &'static str,
    identity: &'static str,
}

/// What a recolor did.
#[derive(Serialize)]
struct RecolorReport {
    schema: u32,
    field: String,
    colormap: String,
    transform: coloring::Transform,
    resolution: [u32; 2],
    output: String,
    seconds: f64,
}

fn main() -> std::process::ExitCode {
    match run(std::env::args().skip(1).collect()) {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("fractal-engine: {message}");
            std::process::ExitCode::FAILURE
        }
    }
}

fn run(args: Vec<String>) -> Result<(), String> {
    let argument = args.get(1).map(String::as_str);
    match args.first().map(String::as_str) {
        Some("render") => render(argument),
        Some("dump-field") => dump_field(argument),
        Some("recolor") => recolor(argument),
        Some("modes") => print(
            &mode::CATALOG
                .iter()
                .map(|(name, identity)| Mode { name, identity })
                .collect::<Vec<_>>(),
        ),
        Some("--help") | Some("-h") | None => {
            println!("{USAGE}");
            Ok(())
        }
        Some(other) => Err(format!("unknown subcommand '{other}'\n\n{USAGE}")),
    }
}

const USAGE: &str = "\
usage: fractal-engine render     [SPEC.json]
       fractal-engine dump-field [SPEC.json]
       fractal-engine recolor    [SPEC.json]
       fractal-engine modes

render      Render one location through one coloring to a PNG.
dump-field  Write that render's raw scalar field instead, plus a record of it.
            Only for colorings that have a single scalar field behind them.
recolor     Color a dumped field again, without iterating anything.
modes       List the named colorings, as JSON.

The spec is read from SPEC.json, or from stdin when no path is given. A JSON
report describing what happened is written to stdout.";

/// Read a spec from a file or from stdin.
fn read_spec(path: Option<&str>) -> Result<String, String> {
    match path {
        Some(path) => std::fs::read_to_string(path).map_err(|e| format!("read {path}: {e}")),
        None => {
            let mut buffer = String::new();
            std::io::stdin()
                .read_to_string(&mut buffer)
                .map_err(|e| format!("read spec from stdin: {e}"))?;
            Ok(buffer)
        }
    }
}

fn print<T: Serialize>(report: &T) -> Result<(), String> {
    println!(
        "{}",
        serde_json::to_string(report).map_err(|e| format!("report: {e}"))?
    );
    Ok(())
}

fn render(spec_path: Option<&str>) -> Result<(), String> {
    let spec = RenderSpec::parse(&read_spec(spec_path)?)?.resolve()?;
    let colormap = Colormap::load(&spec.colormap_dir, &spec.colormap)?;

    let started = Instant::now();
    let painted = coloring::paint(
        &spec.view,
        &spec.family,
        spec.maxiter,
        &spec.coloring,
        &colormap,
    )?;
    let paint_seconds = started.elapsed().as_secs_f64();

    let started = Instant::now();
    write_image(&spec.output, &painted.linear, &spec.view)?;
    let resample_seconds = started.elapsed().as_secs_f64();

    print(&RenderReport {
        schema: 1,
        location: spec.location,
        resolution: [spec.view.out_width, spec.view.out_height],
        supersample: spec.view.supersample,
        maxiter: spec.maxiter,
        mode: spec.mode,
        coloring: spec.coloring,
        colormap: colormap.name().to_string(),
        interior_fraction: painted.interior_fraction,
        output: spec.output.display().to_string(),
        seconds: RenderSeconds {
            paint: paint_seconds,
            resample: resample_seconds,
        },
    })
}

fn dump_field(spec_path: Option<&str>) -> Result<(), String> {
    let spec = RenderSpec::parse(&read_spec(spec_path)?)?.resolve()?;
    dump::check_path(&spec.output)?;

    let named = spec.mode.clone().unwrap_or_else(|| "this coloring".into());
    let layer = spec.coloring.dumpable_field().ok_or_else(|| {
        format!(
            "dump-field: {named} has no scalar field to dump — {}",
            spec.coloring
                .why_not_a_field()
                .expect("a coloring with no field has a reason")
        )
    })?;

    let started = Instant::now();
    let sampled = field::render_field(&spec.view, &spec.family, spec.maxiter, layer.field);
    let seconds = started.elapsed().as_secs_f64();
    let field = &sampled.fields[0];

    let record = dump::Record {
        schema: 1,
        mode: spec.mode,
        field: layer.field,
        transform: layer.transform,
        colormap: spec.colormap,
        location: spec.location,
        maxiter: spec.maxiter,
        resolution: [spec.view.out_width, spec.view.out_height],
        supersample: spec.view.supersample,
        samples: [field.width, field.height],
        interior_fraction: sampled.interior_fraction,
        dtype: dump::DTYPE.into(),
        layout: dump::LAYOUT.into(),
        field_file: file_name(&spec.output),
    };
    let record_path = dump::write(&spec.output, field, &record)?;

    print(&DumpReport {
        schema: 1,
        field: spec.output.display().to_string(),
        record: record_path.display().to_string(),
        samples: [field.width, field.height],
        seconds,
    })
}

fn recolor(spec_path: Option<&str>) -> Result<(), String> {
    let spec = RecolorSpec::parse(&read_spec(spec_path)?)?;
    let (field, record) = dump::read(&spec.field)?;

    let name = spec.colormap.unwrap_or(record.colormap);
    let colormap = Colormap::load(&spec.colormap_dir, &name)?;
    let transform = spec.transform.unwrap_or(record.transform);

    let started = Instant::now();
    let linear = coloring::colorize(&field, transform, &colormap);
    let [out_width, out_height] = record.resolution;
    let pixels = resample::downsample(
        &linear,
        field.width as usize,
        field.height as usize,
        out_width as usize,
        out_height as usize,
        record.supersample,
    );
    resample::write_png(&spec.output, &pixels, out_width, out_height)?;
    let seconds = started.elapsed().as_secs_f64();

    print(&RecolorReport {
        schema: 1,
        field: spec.field.display().to_string(),
        colormap: colormap.name().to_string(),
        transform,
        resolution: record.resolution,
        output: spec.output.display().to_string(),
        seconds,
    })
}

/// Downsample a supersampled linear-light buffer and write it as a PNG.
fn write_image(
    output: &Path,
    linear: &[[f64; 3]],
    view: &fractal_engine::viewport::Viewport,
) -> Result<(), String> {
    let pixels = resample::downsample(
        linear,
        view.sample_width() as usize,
        view.sample_height() as usize,
        view.out_width as usize,
        view.out_height as usize,
        view.supersample,
    );
    resample::write_png(output, &pixels, view.out_width, view.out_height)
}

fn file_name(path: &Path) -> String {
    path.file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_default()
}
