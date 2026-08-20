//! `fractal-engine` — the command line around the render pipeline.
//!
//! ```text
//! fractal-engine render     [spec.json]   # a location and a coloring → a PNG
//! fractal-engine dump-field [spec.json]   # the same, stopping at the raw field
//! fractal-engine recolor    [spec.json]   # a dumped field → a PNG, no iteration
//! fractal-engine expand     [spec.json]   # walk nodes → one rung each, gated
//! fractal-engine tiles      [spec.json]   # one field per location → many crops
//! fractal-engine home-view  [spec.json]   # a family → where it is framed by default
//! fractal-engine maxiter    [spec.json]   # plane widths → the iteration cap policy
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
    coloring::{self, Coloring, Palette},
    colormap::Colormap,
    dump, expand, family, field, mode, resample, spec,
    spec::{Location, MaxiterSpec, RecolorSpec, RenderSpec},
    tiles,
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
    /// How the gradient was spent on it. Echoed even when it is all defaults,
    /// because a record that omitted it would not say which render it was.
    palette: Palette,
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
    /// Whether a production draw may pick this mode. Every reader that draws one
    /// filters on this rather than keeping a list of exclusions.
    tier: mode::Tier,
    /// The coloring the name stands for, written out. A name is a claim that a
    /// setting is worth returning to; this is the setting, so a caller that
    /// needs to vary one knob of a mode can start from what the mode actually is
    /// instead of restating it and drifting.
    ///
    /// A listing has no family, so this is the **catalog form**: exact for
    /// eighteen of the nineteen, and `itinerary`'s parameter-plane one. Where the
    /// pixel is `z₀` that mode opens its address at `z₁` instead, which its
    /// identity line says and [`mode::resolve`] does.
    coloring: Coloring,
}

/// Where one family is framed when nothing says otherwise, and how that frame
/// was arrived at.
///
/// The derivation travels with the answer on purpose. A caller that reads a
/// framing out of the engine rather than keeping its own should be able to see
/// what the framing is *made of* — the measured set, the margin, the grid it was
/// measured on — without reading the engine's source.
#[derive(Serialize)]
struct HomeViewReport {
    schema: u32,
    family: &'static str,
    degree: spec::Degree,
    viewport: HomeViewport,
    /// True when the row is the rule evaluated on a measured set. False for the
    /// one family that has no set to measure, which then carries `exception`.
    derived: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    extent: Option<MeasuredExtent>,
    #[serde(skip_serializing_if = "Option::is_none")]
    exception: Option<&'static str>,
    rule: DerivationRule,
}

/// The home view as the decimal strings a location is written in.
#[derive(Serialize)]
struct HomeViewport {
    center_re: String,
    center_im: String,
    width: String,
}

/// The filled-set box the row was derived from, as `[low, high]` per axis.
#[derive(Serialize)]
struct MeasuredExtent {
    re: [f64; 2],
    im: [f64; 2],
}

/// The parameters the derivation was run with, recorded beside every answer.
#[derive(Serialize)]
struct DerivationRule {
    /// Samples per axis of the measuring grid.
    grid: u32,
    /// Half-span the grid covered, on both axes.
    half_span: f64,
    /// Iteration cap a sample counted as filled at.
    cap: u32,
    /// Slack beyond the set, as a share of its extent on the deciding axis.
    margin: f64,
    /// The output aspect the frame is composed for.
    aspect: f64,
}

/// What a recolor did.
#[derive(Serialize)]
struct RecolorReport {
    schema: u32,
    field: String,
    colormap: String,
    transform: coloring::Transform,
    /// How the gradient was spent. Echoed for the same reason a render's is.
    palette: Palette,
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
        Some("expand") => expand_nodes(argument),
        Some("tiles") => build_tiles(argument),
        Some("home-view") => home_view(argument),
        Some("maxiter") => maxiter_caps(argument),
        Some("modes") => print(
            &mode::CATALOG
                .iter()
                .map(|entry| {
                    Ok(Mode {
                        name: entry.name,
                        identity: entry.identity,
                        tier: entry.tier,
                        coloring: mode::resolve(entry.name, None)?,
                    })
                })
                .collect::<Result<Vec<_>, String>>()?,
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
       fractal-engine expand     [SPEC.json]
       fractal-engine tiles      [SPEC.json]
       fractal-engine home-view  [SPEC.json]
       fractal-engine maxiter    [SPEC.json]
       fractal-engine modes

render      Render one location through one coloring to a PNG.
dump-field  Write that render's raw scalar field instead, plus a record of it.
            Only for colorings that have a single scalar field behind them.
recolor     Color a dumped field again, without iterating anything.
expand      Take one rung of a walk from each of a batch of nodes: draw
            candidate next frames, gate them, and report every one with its
            fate and a thumbnail of the survivors.
tiles       Turn a plan of locations into training tiles: one iteration pass
            per location, and every tile a colored crop of it.
home-view   Where a family is framed when nothing says otherwise, with the
            measured set and the rule the frame was derived by. Takes a spec
            that is a schema and a family, and renders nothing.
maxiter     The iteration cap the policy gives each of a list of plane widths.
            The cap decides what counts as interior, so it is part of what a
            picture *is*; this is how the other half of the project checks that
            two renders of one location were drawn at the same one.
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
    let colormap = Colormap::load_baked(&spec.colormap_dir, &spec.colormap, spec.palette.bake)?;

    let started = Instant::now();
    let painted = coloring::paint(
        &spec.view,
        &spec.family,
        spec.maxiter,
        &spec.coloring,
        &spec.palette,
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
        palette: spec.palette,
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

fn expand_nodes(spec_path: Option<&str>) -> Result<(), String> {
    let spec = expand::ExpandSpec::parse(&read_spec(spec_path)?)?;
    print(&expand::run(spec)?)
}

/// What the cap policy gives a list of widths, printed as one JSON object.
#[derive(Serialize)]
struct MaxiterReport {
    schema: u32,
    widths: Vec<String>,
    caps: Vec<u32>,
}

fn maxiter_caps(spec_path: Option<&str>) -> Result<(), String> {
    let spec = MaxiterSpec::parse(&read_spec(spec_path)?)?;
    let caps = spec.caps()?;
    print(&MaxiterReport {
        schema: 1,
        widths: spec.widths,
        caps,
    })
}

/// The one exception in the home table, stated where a caller will read it.
const JULIA_EXCEPTION: &str = "a Julia set is a different shape for every c, so no one frame \
                              contains every member and there is no set to measure: this \
                              family comes home to the whole plane by exception";

fn home_view(spec_path: Option<&str>) -> Result<(), String> {
    let spec = spec::HomeViewSpec::parse(&read_spec(spec_path)?)?;
    let resolved = spec.family.resolve()?;
    let family = resolved.family;
    let home = family
        .home_view()
        .ok_or_else(|| spec::render_only_refusal(resolved.kind, "framed by the home table"))?;
    let extent = family.measured_extent();

    print(&HomeViewReport {
        schema: 1,
        family: resolved.kind,
        degree: resolved.degree,
        viewport: HomeViewport {
            center_re: spec::to_decimal_string(home.center.re),
            center_im: spec::to_decimal_string(home.center.im),
            width: spec::to_decimal_string(home.width),
        },
        derived: extent.is_some(),
        extent: extent.map(|e| MeasuredExtent {
            re: [e.re.0, e.re.1],
            im: [e.im.0, e.im.1],
        }),
        exception: extent.is_none().then_some(JULIA_EXCEPTION),
        rule: DerivationRule {
            grid: family::MEASURE_GRID,
            half_span: family::MEASURE_HALF_SPAN,
            cap: family::MEASURE_CAP,
            margin: family::HOME_MARGIN,
            aspect: family::HOME_ASPECT,
        },
    })
}

fn build_tiles(spec_path: Option<&str>) -> Result<(), String> {
    let spec = tiles::TilesSpec::parse(&read_spec(spec_path)?)?;
    print(&tiles::run(spec)?)
}

fn recolor(spec_path: Option<&str>) -> Result<(), String> {
    let spec = RecolorSpec::parse(&read_spec(spec_path)?)?;
    let (field, record) = dump::read(&spec.field)?;

    let name = spec.colormap.unwrap_or(record.colormap);
    let colormap = Colormap::load_baked(&spec.colormap_dir, &name, spec.palette.bake)?;
    let transform = spec.transform.unwrap_or(record.transform);

    let started = Instant::now();
    let linear = coloring::shade(&field, transform, &spec.palette, &colormap);
    let [out_width, out_height] = record.resolution;
    let pixels = resample::downsample(
        &linear,
        field.width as usize,
        field.height as usize,
        out_width as usize,
        out_height as usize,
        record.supersample,
    );
    resample::write_image(&spec.output, &pixels, out_width, out_height)?;
    let seconds = started.elapsed().as_secs_f64();

    print(&RecolorReport {
        schema: 1,
        field: spec.field.display().to_string(),
        colormap: colormap.name().to_string(),
        transform,
        palette: spec.palette,
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
    resample::write_image(output, &pixels, view.out_width, view.out_height)
}

fn file_name(path: &Path) -> String {
    path.file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_default()
}
