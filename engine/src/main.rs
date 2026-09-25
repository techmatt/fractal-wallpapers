//! `fractal-engine` — the command line around the render pipeline.
//!
//! ```text
//! fractal-engine render     [spec.json]   # a location and a coloring → a PNG
//! fractal-engine dump-field [spec.json]   # the same, stopping at the raw field
//! fractal-engine recolor    [spec.json]   # a dumped field → a PNG, no iteration
//! fractal-engine expand     [spec.json]   # walk nodes → one rung each, gated
//! fractal-engine screen     [spec.json]   # named frames → what each gate said
//! fractal-engine tiles      [spec.json]   # one field per location → many crops
//! fractal-engine home-view  [spec.json]   # a family → where it is framed by default
//! fractal-engine maxiter    [spec.json]   # plane widths → the iteration cap policy
//! fractal-engine modes                    # what the named colorings are
//! fractal-engine render-link --link <URL|query> --size WxH [--ss N] [--out FILE] [--data DIR]
//!                                         # an explorer link → the wallpaper, link embedded
//! ```
//!
//! One JSON object in, one file out, and a JSON report on stdout describing what
//! happened. `render-link` is the one subcommand that takes flags rather than a
//! spec: its input is a link somebody copied, and a spec would be a second spelling
//! of it. The report is the record: it carries the location's decimal strings
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
    dump, embed, expand, family, field, link, mode, resample, screen, spec,
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
    /// Whether the coloring's texture layer carried no information — see
    /// [`coloring::Painted::texture_flat`]. Absent for every coloring that has no
    /// texture to be flat, which is all of them but the two modulates, and absent
    /// for the same recorded-name reason `Composite::texture_gamma` is: a key that
    /// appeared unconditionally would say nothing on seventeen of the nineteen
    /// production modes and would put a member into every render record ever read
    /// back. The count is `mode`'s own split test — eight fields, six composites
    /// and four direct traps carry no texture layer, against two modulates that
    /// do — read over the nineteen entries of [`mode::CATALOG`] on
    /// [`mode::Tier::Production`], which is all of them but `de`. A `true` here
    /// says the picture is the base spent by rank, bit for bit — the reason to
    /// report it rather than throw it away.
    #[serde(skip_serializing_if = "Option::is_none")]
    texture_flat: Option<bool>,
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
    /// nineteen of the twenty, and `itinerary`'s parameter-plane one. Where the
    /// pixel is `z₀` that mode opens its address at `z₁` instead, which its
    /// identity line says and [`mode::resolve`] does. `tail_itinerary` reads the
    /// same on both planes, so its listed coloring is exact.
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
        Some("screen") => screen_frames(argument),
        Some("tiles") => build_tiles(argument),
        Some("home-view") => home_view(argument),
        Some("maxiter") => maxiter_caps(argument),
        Some("render-link") => render_link(&args[1..]),
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
       fractal-engine screen     [SPEC.json]
       fractal-engine tiles      [SPEC.json]
       fractal-engine home-view  [SPEC.json]
       fractal-engine maxiter    [SPEC.json]
       fractal-engine modes
       fractal-engine render-link --link <URL|query> --size WxH [--ss N]
                                  [--out FILE.png|FILE.jpg] [--data DIR]

render      Render one location through one coloring to a PNG.
dump-field  Write that render's raw scalar field instead, plus a record of it.
            Only for colorings that have a single scalar field behind them.
recolor     Color a dumped field again, without iterating anything.
expand      Take one rung of a walk from each of a batch of nodes: draw
            candidate next frames, gate them, and report every one with its
            fate and a thumbnail of the survivors.
screen      Run the same structural gates over frames somebody named, and
            report what each gate read and which way it went. Proposes
            nothing: this is expand's filter without expand's search.
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
render-link Draw an explorer link — the whole URL or its query — at a size, and
            write it with the link embedded in its metadata. --ss defaults to 3.
            --out defaults to render-link.png; .jpg writes a JPEG. The palettes,
            anchors and band come from a checkout's data/: --data DIR, else
            $FRACTAL_ENGINE_DATA, else the first data/ found walking up from the
            working directory, then from the executable. A deep (dv=) link is
            read and refused: deep rendering is not built yet.

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
        texture_flat: painted.texture_flat,
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

fn screen_frames(spec_path: Option<&str>) -> Result<(), String> {
    let spec = screen::ScreenSpec::parse(&read_spec(spec_path)?)?;
    print(&screen::run(spec)?)
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
    // Through `toned` for the same reason `paint` is: a recolor is the render
    // its field came from, and the recipe's last stage belongs to both.
    let linear = coloring::toned(
        coloring::shade(&field, transform, &spec.palette, &colormap),
        &spec.palette,
    );
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

// ------------------------------------------------------------------ render-link

/// The environment variable `render-link` reads a `data/` directory from.
const DATA_ENV: &str = "FRACTAL_ENGINE_DATA";

/// What `render-link` did: the render's own report, and the link it carried.
#[derive(Serialize)]
struct LinkReport {
    #[serde(flatten)]
    render: RenderReport,
    /// The canonical query — what the explorer itself would write for this view — which
    /// is also what the file's metadata now carries.
    link: String,
    url: String,
    /// Whether a `level=` curve was replayed on the map's stops.
    levelled: bool,
    /// The `data/` directory the palettes and anchors were read from.
    data: String,
}

/// `render-link`'s flags, parsed.
struct LinkArgs {
    link: String,
    size: [u32; 2],
    supersample: u32,
    output: std::path::PathBuf,
    data: Option<std::path::PathBuf>,
}

/// The release regime's supersample is 2 (`release.RELEASE_REGIME`); the production
/// setting this command defaults to is 3, on Matt's call for `render_link_ckpt148`.
const DEFAULT_SUPERSAMPLE: u32 = 3;

fn link_args(args: &[String]) -> Result<LinkArgs, String> {
    let mut link = None;
    let mut size = None;
    let mut supersample = DEFAULT_SUPERSAMPLE;
    let mut output = std::path::PathBuf::from("render-link.png");
    let mut data = None;
    let mut at = 0;
    while at < args.len() {
        let flag = args[at].as_str();
        let value = args
            .get(at + 1)
            .ok_or_else(|| format!("render-link: {flag} needs a value\n\n{USAGE}"))?;
        match flag {
            "--link" => link = Some(value.clone()),
            "--size" => {
                let (width, height) = value
                    .split_once(['x', 'X'])
                    .ok_or_else(|| format!("render-link: --size is WxH, got '{value}'"))?;
                let read = |side: &str| {
                    side.parse::<u32>()
                        .ok()
                        .filter(|&side| side > 0)
                        .ok_or_else(|| format!("render-link: --size is WxH, got '{value}'"))
                };
                size = Some([read(width)?, read(height)?]);
            }
            "--ss" => {
                supersample = value
                    .parse::<u32>()
                    .ok()
                    .filter(|&ss| ss > 0)
                    .ok_or_else(|| format!("render-link: --ss is a whole number, got '{value}'"))?;
            }
            "--out" => output = value.into(),
            "--data" => data = Some(value.into()),
            _ => return Err(format!("render-link: unknown flag '{flag}'\n\n{USAGE}")),
        }
        at += 2;
    }
    Ok(LinkArgs {
        link: link.ok_or_else(|| format!("render-link: --link is required\n\n{USAGE}"))?,
        size: size.ok_or_else(|| format!("render-link: --size is required\n\n{USAGE}"))?,
        supersample,
        output,
        data,
    })
}

/// Where the palettes, the anchors and the band live: `--data`, else [`DATA_ENV`], else
/// the first `data/` holding a colormap library and the anchors found walking up from
/// the working directory, and then from the executable — which is a clone's own
/// `data/` whether the binary is run from the checkout or from `engine/target/release`.
fn data_dir(given: Option<std::path::PathBuf>) -> Result<std::path::PathBuf, String> {
    let holds = |dir: &Path| dir.join("palettes").is_dir() && dir.join("anchors.jsonl").is_file();
    if let Some(dir) = given {
        return if holds(&dir) {
            Ok(dir)
        } else {
            Err(format!(
                "--data {}: no palettes/ and anchors.jsonl there",
                dir.display()
            ))
        };
    }
    if let Some(dir) = std::env::var_os(DATA_ENV).map(std::path::PathBuf::from) {
        return if holds(&dir) {
            Ok(dir)
        } else {
            Err(format!(
                "{DATA_ENV}={}: no palettes/ and anchors.jsonl there",
                dir.display()
            ))
        };
    }
    let starts = [
        std::env::current_dir().ok(),
        std::env::current_exe()
            .ok()
            .and_then(|exe| exe.parent().map(Path::to_path_buf)),
    ];
    for start in starts.into_iter().flatten() {
        for dir in start.ancestors() {
            let candidate = dir.join("data");
            if holds(&candidate) {
                return Ok(candidate);
            }
        }
    }
    Err(format!(
        "render-link found no data/ directory: run it inside a fractal-wallpapers checkout, \
         or say where one is with --data DIR or {DATA_ENV}"
    ))
}

/// What a deep `render-link` did.
#[derive(Serialize)]
struct DeepReport {
    schema: u32,
    backend: &'static str,
    resolution: [u32; 2],
    supersample: u32,
    output: String,
    link: String,
    url: String,
    data: String,
    seconds: f64,
}

/// A deep link through a backend: its lanes, the engine's own colouring, the file, the
/// link. Everything but the backend's lanes is here already, so a perturbation backend
/// is the one missing piece; today the only backend is [`link::NotBuilt`], which refuses
/// before a file is touched.
fn render_deep(
    backend: &dyn link::DeepBackend,
    view: &link::DeepView,
    args: &LinkArgs,
    context: &link::Context,
    canonical: String,
    data: &Path,
) -> Result<(), String> {
    if !fits_aspect(args.size, view.aspect) {
        return Err(format!(
            "--size {}x{} is not the link's aspect {}:{}",
            args.size[0], args.size[1], view.aspect.0, view.aspect.1
        ));
    }
    let started = Instant::now();
    let frame = link::DeepFrame {
        view,
        samples: args.size.map(|side| side * args.supersample),
    };
    let lanes = backend.lanes(&frame)?;
    let colormap =
        link::colormap_for(context, &view.palette, view.level.as_ref(), view.shade.bake)?;
    let pixels = link::shade_lanes(&lanes, &view.shade, &colormap, args.size, args.supersample);
    resample::write_image(&args.output, &pixels, args.size[0], args.size[1])?;
    embed::embed_file(&args.output, &canonical)?;
    print(&DeepReport {
        schema: 1,
        backend: backend.name(),
        resolution: args.size,
        supersample: args.supersample,
        output: args.output.display().to_string(),
        url: embed::url_of(&canonical),
        link: canonical,
        data: data.display().to_string(),
        seconds: started.elapsed().as_secs_f64(),
    })
}

/// Whether an output size is the link's aspect, to the nearest pixel either way.
fn fits_aspect(size: [u32; 2], aspect: (u32, u32)) -> bool {
    let [width, height] = size.map(u64::from);
    let (across, down) = (u64::from(aspect.0), u64::from(aspect.1));
    let rounded =
        |numerator: u64, denominator: u64| (2 * numerator + denominator) / (2 * denominator);
    height == rounded(width * down, across) || width == rounded(height * across, down)
}

fn render_link(args: &[String]) -> Result<(), String> {
    let args = link_args(args)?;
    let data = data_dir(args.data.clone())?;
    let context = link::Context::from_data(&data)?;
    let query = link::query_of(&args.link);
    let parsed = link::parse(query, &context)?;
    let canonical = parsed.canonical(&context)?;

    let view = match parsed {
        link::Link::Shallow(view) => view,
        link::Link::Deep(view) => {
            return render_deep(&link::NotBuilt, &view, &args, &context, canonical, &data);
        }
    };
    if let Some(key) = view.underived() {
        return Err(format!(
            "this link leaves {key} out, which under permalink v3+ means \"derive it from the \
             view\": the explorer measures the picture on its canvas, and render-link has no \
             canvas to measure. Open the link in the explorer and copy it again — the link it \
             writes carries the {key} it drew at — or add {key}= yourself"
        ));
    }
    if !fits_aspect(args.size, view.aspect) {
        return Err(format!(
            "--size {}x{} is not the link's aspect {}:{}; a link names a shape, and a picture \
             at another one would show a different frame",
            args.size[0], args.size[1], view.aspect.0, view.aspect.1
        ));
    }

    let spec = view
        .render_spec(
            args.size,
            args.supersample,
            context.palettes().to_path_buf(),
            args.output.clone(),
        )
        .resolve()?;
    // The operator's own `applies_to`: a replayed curve on a coloring it never acts on
    // is a decision no run took, and the explorer's module refuses it the same way.
    if view.level.is_some()
        && !matches!(
            spec.coloring,
            Coloring::Field { .. } | Coloring::Composite { .. }
        )
    {
        return Err(format!(
            "{} does not act on the {} mode, so there is no curve for this link to replay",
            fractal_engine::autolevel::OPERATOR,
            view.mode
        ));
    }
    let colormap = link::colormap_for(
        &context,
        &view.palette,
        view.level.as_ref(),
        spec.palette.bake,
    )?;

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
    embed::embed_file(&spec.output, &canonical)?;
    let resample_seconds = started.elapsed().as_secs_f64();

    print(&LinkReport {
        render: RenderReport {
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
            texture_flat: painted.texture_flat,
            output: spec.output.display().to_string(),
            seconds: RenderSeconds {
                paint: paint_seconds,
                resample: resample_seconds,
            },
        },
        url: embed::url_of(&canonical),
        link: canonical,
        levelled: view.level.is_some(),
        data: data.display().to_string(),
    })
}
