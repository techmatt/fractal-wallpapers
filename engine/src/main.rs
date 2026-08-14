//! `fractal-engine` — the command line around the render pipeline.
//!
//! ```text
//! fractal-engine render [spec.json]     # or: … | fractal-engine render
//! ```
//!
//! One subcommand, one JSON object in, one PNG out, and a JSON report on stdout
//! describing what was rendered. The report is the record: it carries the
//! location's decimal strings back unchanged alongside the values the engine
//! filled in for itself, so a render can be repeated from its own output.

use std::io::Read;
use std::path::Path;
use std::time::Instant;

use serde::Serialize;

use fractal_engine::{
    coloring,
    colormap::Colormap,
    field, resample,
    spec::{Location, RenderSpec},
};

/// What the engine did, printed to stdout as one JSON object.
#[derive(Serialize)]
struct Report {
    schema: u32,
    location: Location,
    resolution: [u32; 2],
    supersample: u32,
    maxiter: u32,
    colormap: String,
    /// Share of samples whose orbit never escaped — a one-number sanity check on
    /// a render, and the first thing to look at when a frame comes out black.
    interior_fraction: f64,
    output: String,
    seconds: Seconds,
}

#[derive(Serialize)]
struct Seconds {
    field: f64,
    color: f64,
    resample: f64,
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
    match args.first().map(String::as_str) {
        Some("render") => render(args.get(1).map(String::as_str)),
        Some("--help") | Some("-h") | None => {
            println!("{USAGE}");
            Ok(())
        }
        Some(other) => Err(format!("unknown subcommand '{other}'\n\n{USAGE}")),
    }
}

const USAGE: &str = "\
usage: fractal-engine render [SPEC.json]

Render one fractal image. The spec is read from SPEC.json, or from stdin when no
path is given. A JSON report describing the render is written to stdout.";

fn render(spec_path: Option<&str>) -> Result<(), String> {
    let text = match spec_path {
        Some(path) => std::fs::read_to_string(path).map_err(|e| format!("read {path}: {e}"))?,
        None => {
            let mut buffer = String::new();
            std::io::stdin()
                .read_to_string(&mut buffer)
                .map_err(|e| format!("read spec from stdin: {e}"))?;
            buffer
        }
    };

    let spec = RenderSpec::parse(&text)?.resolve()?;
    let colormap = Colormap::load(&spec.colormap_dir, &spec.colormap)?;

    let started = Instant::now();
    let field = field::render_field(&spec.view, &spec.family, spec.maxiter);
    let field_seconds = started.elapsed().as_secs_f64();

    let started = Instant::now();
    let linear = coloring::colorize(&field, &colormap);
    let color_seconds = started.elapsed().as_secs_f64();

    let started = Instant::now();
    let pixels = resample::downsample(
        &linear,
        field.width as usize,
        field.height as usize,
        spec.view.out_width as usize,
        spec.view.out_height as usize,
        spec.view.supersample,
    );
    resample::write_png(
        Path::new(&spec.output),
        &pixels,
        spec.view.out_width,
        spec.view.out_height,
    )?;
    let resample_seconds = started.elapsed().as_secs_f64();

    let report = Report {
        schema: 1,
        location: spec.location,
        resolution: [spec.view.out_width, spec.view.out_height],
        supersample: spec.view.supersample,
        maxiter: spec.maxiter,
        colormap: colormap.name().to_string(),
        interior_fraction: field.interior_fraction(),
        output: spec.output.display().to_string(),
        seconds: Seconds {
            field: field_seconds,
            color: color_seconds,
            resample: resample_seconds,
        },
    };
    println!(
        "{}",
        serde_json::to_string(&report).map_err(|e| format!("report: {e}"))?
    );
    Ok(())
}
