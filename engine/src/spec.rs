//! A render, described as JSON.
//!
//! The engine takes one object on stdin or from a file and makes one image. It
//! has no other input, no configuration file, and no defaults hidden anywhere
//! but here — which is what lets a render be reproduced from the record of it.
//!
//! ```json
//! {
//!   "schema": 1,
//!   "family": { "kind": "julia", "c": ["-0.4", "0.6"] },
//!   "viewport": { "center_re": "0", "center_im": "0", "width": "3.0" },
//!   "resolution": [1920, 1080],
//!   "supersample": 2,
//!   "mode": "smooth_stripe",
//!   "colormap": "twilight_shifted",
//!   "colormap_dir": "data/palettes",
//!   "output": "artifacts/julia.png"
//! }
//! ```
//!
//! How the render is colored is either a **mode** — a name from
//! [`crate::mode`]'s catalog — or a **coloring** written out in full. Never
//! both: a mode *is* a coloring with a name, and a spec that gave one of each
//! would have two answers to the same question. Neither means `smooth`.
//!
//! Every coordinate and every family constant is a **decimal string**, and the
//! string is the identity: it is what gets recorded, compared, and re-rendered
//! from. `f64` is a view of that identity which is exact enough for the depths
//! this slice reaches and will not be forever, so the strings survive the render
//! and are echoed back unchanged.

use std::path::PathBuf;

use num_complex::Complex;
use serde::{Deserialize, Serialize};

use crate::coloring::{Coloring, Palette};
use crate::family::{Family, HomeView, PHOENIX_C, PHOENIX_P};
use crate::maxiter;
use crate::mode;
use crate::viewport::Viewport;

/// A complex constant, as the pair of decimal strings it was written as.
pub type Pair = [String; 2];

/// The render spec, exactly as it appears on the wire.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RenderSpec {
    pub schema: u32,
    pub family: FamilySpec,
    #[serde(default)]
    pub viewport: ViewportSpec,
    /// `[width, height]` in output pixels.
    pub resolution: [u32; 2],
    #[serde(default = "one")]
    pub supersample: u32,
    /// A name from the mode catalog. Mutually exclusive with `coloring`.
    #[serde(default)]
    pub mode: Option<String>,
    /// A coloring written out in full. Mutually exclusive with `mode`.
    #[serde(default)]
    pub coloring: Option<Coloring>,
    /// How the gradient is spent on whatever the coloring produced. Independent
    /// of the mode, and every default is the identity.
    #[serde(default)]
    pub palette: Palette,
    pub colormap: String,
    #[serde(default = "default_colormap_dir")]
    pub colormap_dir: PathBuf,
    /// Iterations per sample. Absent means the depth-aware policy decides.
    #[serde(default)]
    pub maxiter: Option<u32>,
    pub output: PathBuf,
}

/// Which recurrence, and its fixed constants.
#[derive(Debug, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum FamilySpec {
    /// `z ← z² + c` over the parameter plane.
    Mandelbrot,
    /// `z ← z^d + c` over the parameter plane, `d ∈ {3, 4, 5}`.
    Multibrot { degree: u32 },
    /// `z ← z^d + c` over the dynamical plane at a fixed `c`. The Julia twin of
    /// whichever parameter-plane family shares its degree.
    Julia {
        #[serde(default = "two")]
        degree: u32,
        c: Pair,
    },
    /// `z_{n+1} = z_n² + c + p·z_{n-1}` over the dynamical plane. Every constant
    /// has a classic default, so `{"kind": "phoenix"}` alone is the Ushiki set.
    Phoenix {
        #[serde(default = "phoenix_c")]
        c: Pair,
        #[serde(default = "phoenix_p")]
        p: Pair,
        #[serde(default = "origin")]
        z_prev: Pair,
    },
    /// `z ← z^d + c` over the parameter plane at a **non-integer** `d`, on the
    /// principal branch: the gaps between the integer degrees the families above
    /// render, and **render-only** — `render` and `dump-field` take it and every
    /// other door refuses it. See [`Family::FractionalMultibrot`].
    ///
    /// The degree is a decimal string for the same reason every coordinate is:
    /// it is not a whole number, so the string is the identity of the render and
    /// the `f64` is a view of it.
    FractionalMultibrot { degree: String },
}

/// A dumped field, read back and colored again.
///
/// Everything geometric — the grid, the location, the field itself — comes from
/// the dump's own record, because it is already settled. What is left is the
/// coloring tail, and every key of it is optional: a recolor that says nothing
/// but where to write reproduces the render the dump came from, which is what
/// makes it a usable starting point rather than a form to fill in.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RecolorSpec {
    pub schema: u32,
    /// Path to the dumped field. Its record is the file beside it.
    pub field: PathBuf,
    #[serde(default)]
    pub colormap: Option<String>,
    #[serde(default = "default_colormap_dir")]
    pub colormap_dir: PathBuf,
    #[serde(default)]
    pub transform: Option<crate::coloring::Transform>,
    /// How the gradient is spent. A recolor that says nothing here reproduces
    /// the render the dump came from.
    #[serde(default)]
    pub palette: Palette,
    pub output: PathBuf,
}

impl RecolorSpec {
    /// Read a recolor spec from JSON text.
    pub fn parse(text: &str) -> Result<RecolorSpec, String> {
        let spec: RecolorSpec = serde_json::from_str(text).map_err(|e| format!("spec: {e}"))?;
        if spec.schema != 1 {
            return Err(format!("spec has schema {}, expected 1", spec.schema));
        }
        spec.palette.validate()?;
        Ok(spec)
    }
}

/// A family, and nothing else.
///
/// The whole input to `home-view`, which answers *where is this family framed
/// when nothing says otherwise*. It exists so the Python half can read the home
/// table instead of keeping a second copy of it: framing has one owner, and this
/// is the door to it.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HomeViewSpec {
    pub schema: u32,
    pub family: FamilySpec,
}

impl HomeViewSpec {
    /// Read a home-view spec from JSON text.
    pub fn parse(text: &str) -> Result<HomeViewSpec, String> {
        let spec: HomeViewSpec = serde_json::from_str(text).map_err(|e| format!("spec: {e}"))?;
        if spec.schema != 1 {
            return Err(format!("spec has schema {}, expected 1", spec.schema));
        }
        Ok(spec)
    }
}

/// Where to look. Anything omitted falls back to the family's home view.
#[derive(Debug, Default, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ViewportSpec {
    pub center_re: Option<String>,
    pub center_im: Option<String>,
    pub width: Option<String>,
}

/// A spec with its strings parsed and its defaults filled in.
pub struct Resolved {
    pub family: Family,
    pub view: Viewport,
    pub maxiter: u32,
    /// The mode's name, when the spec asked for one by name.
    pub mode: Option<String>,
    pub coloring: Coloring,
    pub palette: Palette,
    pub colormap: String,
    pub colormap_dir: PathBuf,
    pub output: PathBuf,
    /// The location as it was written, carried through untouched for the echo.
    pub location: Location,
}

/// The exponent of a location, as its record writes it.
///
/// Integer degrees stay integers on the wire — `"degree": 2` is the same five
/// bytes it has always been — and a fractional degree is the decimal string it
/// was written as, exactly like every coordinate. Untagged, so neither form
/// carries a discriminator and neither is a new key: one `degree`, two shapes,
/// and a record from before this existed reads back unchanged.
///
/// The two shapes cannot collide, and that is by construction rather than by
/// care: [`FamilySpec::FractionalMultibrot`] refuses a whole number, so an
/// integer exponent has exactly one spelling.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Degree {
    Integer(u32),
    Fractional(String),
}

/// The decimal strings that identify this render, kept verbatim.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Location {
    pub family: String,
    pub degree: Degree,
    pub center_re: String,
    pub center_im: String,
    pub width: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub c: Option<Pair>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub p: Option<Pair>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub z_prev: Option<Pair>,
}

impl RenderSpec {
    /// Read a spec from JSON text.
    pub fn parse(text: &str) -> Result<RenderSpec, String> {
        let spec: RenderSpec = serde_json::from_str(text).map_err(|e| format!("spec: {e}"))?;
        if spec.schema != 1 {
            return Err(format!("spec has schema {}, expected 1", spec.schema));
        }
        Ok(spec)
    }

    /// Parse the strings, fill in the defaults, and check the result is sane.
    pub fn resolve(self) -> Result<Resolved, String> {
        let resolved = self.family.resolve()?;
        let family = resolved.family;

        let home = family.home_view();
        let framed = |written: Option<String>, key: &str, of: fn(&HomeView) -> f64| match written {
            Some(text) => Ok(text),
            None => home
                .as_ref()
                .map(|home| format_default(of(home)))
                .ok_or_else(|| unframed_refusal(resolved.kind, key)),
        };
        let center_re = framed(self.viewport.center_re, "center_re", |home| home.center.re)?;
        let center_im = framed(self.viewport.center_im, "center_im", |home| home.center.im)?;
        let width = framed(self.viewport.width, "width", |home| home.width)?;

        let [out_width, out_height] = self.resolution;
        if out_width == 0 || out_height == 0 {
            return Err("resolution must be positive in both dimensions".into());
        }
        if self.supersample == 0 {
            return Err("supersample must be at least 1".into());
        }

        let plane_width = decimal(&width, "viewport.width")?;
        if plane_width <= 0.0 {
            return Err(format!("viewport.width must be positive, got '{width}'"));
        }

        let view = Viewport {
            center: Complex::new(
                decimal(&center_re, "viewport.center_re")?,
                decimal(&center_im, "viewport.center_im")?,
            ),
            width: plane_width,
            out_width,
            out_height,
            supersample: self.supersample,
        };
        if !view.is_resolvable_in_f64() {
            return Err(format!(
                "pixel size {:.3e} is at the limit of f64: neighbouring pixels would round to \
                 the same coordinate. This engine renders shallow views only.",
                view.pixel_size()
            ));
        }

        let (coloring, mode) = resolve_coloring(self.mode, self.coloring, &family)?;
        self.palette.validate()?;
        // The two halves are settled separately and then checked against each
        // other: almost every pairing is free, and the one that is not should cost
        // a message rather than a render that ignored half the spec. The family is
        // the third such pairing, and it is checked here rather than in the loop
        // for the same reason: it is knowable before a single orbit is run.
        coloring.agrees_with(&self.palette)?;
        coloring.agrees_with_family(&family)?;

        Ok(Resolved {
            maxiter: self
                .maxiter
                .unwrap_or_else(|| maxiter::for_width(plane_width)),
            coloring,
            palette: self.palette,
            mode,
            location: Location {
                family: resolved.kind.to_string(),
                degree: resolved.degree,
                center_re,
                center_im,
                width,
                c: resolved.c,
                p: resolved.p,
                z_prev: resolved.z_prev,
            },
            family,
            view,
            colormap: self.colormap,
            colormap_dir: self.colormap_dir,
            output: self.output,
        })
    }
}

/// A family spec with its constants parsed: the recurrence, and everything the
/// record echoes back about it.
///
/// One struct rather than a tuple because the record's exponent is no longer
/// derivable from the recurrence — a Phoenix escapes quadratically and records no
/// degree of its own, and a fractional degree is a string the spec wrote rather
/// than a number the engine chose.
pub struct ResolvedFamily {
    pub family: Family,
    /// The `kind` the spec named it by, which is what the record calls it.
    pub kind: &'static str,
    /// The exponent as the record writes it.
    pub degree: Degree,
    pub c: Option<Pair>,
    pub p: Option<Pair>,
    pub z_prev: Option<Pair>,
}

impl FamilySpec {
    /// Parse the constants and name the family.
    pub fn resolve(self) -> Result<ResolvedFamily, String> {
        let plain = |family: Family, kind: &'static str, degree: u32| ResolvedFamily {
            family,
            kind,
            degree: Degree::Integer(degree),
            c: None,
            p: None,
            z_prev: None,
        };
        match self {
            FamilySpec::Mandelbrot => Ok(plain(Family::Multibrot { degree: 2 }, "mandelbrot", 2)),
            FamilySpec::Multibrot { degree } => {
                check_degree(degree, 3)?;
                Ok(plain(Family::Multibrot { degree }, "multibrot", degree))
            }
            FamilySpec::Julia { degree, c } => {
                check_degree(degree, 2)?;
                let family = Family::Julia {
                    degree,
                    c: pair(&c, "family.c")?,
                };
                Ok(ResolvedFamily {
                    c: Some(c),
                    ..plain(family, "julia", degree)
                })
            }
            FamilySpec::Phoenix { c, p, z_prev } => {
                let family = Family::Phoenix {
                    c: pair(&c, "family.c")?,
                    p: pair(&p, "family.p")?,
                    z_prev: pair(&z_prev, "family.z_prev")?,
                };
                Ok(ResolvedFamily {
                    c: Some(c),
                    p: Some(p),
                    z_prev: Some(z_prev),
                    ..plain(family, "phoenix", 2)
                })
            }
            FamilySpec::FractionalMultibrot { degree } => {
                let value = decimal(&degree, "family.degree")?;
                check_fractional_degree(value)?;
                Ok(ResolvedFamily {
                    family: Family::FractionalMultibrot { degree: value },
                    kind: "fractional_multibrot",
                    degree: Degree::Fractional(degree),
                    c: None,
                    p: None,
                    z_prev: None,
                })
            }
        }
    }
}

/// Why a render with no viewport could not be framed for it.
///
/// A render-only family has no row in the home table, on purpose: a row is a
/// claim that the family is worth looking at unprompted, and this one is drawn
/// where it is asked for or not at all. So the missing key is named rather than
/// filled in.
fn unframed_refusal(kind: &str, key: &str) -> String {
    format!(
        "viewport.{key} is required for a {kind} render: this family has no home view to \
         fall back on, and is framed by hand or not at all"
    )
}

/// Why a render-only family was turned away from a door that is not a render.
///
/// One message, and one place it is written, because the refusal is the whole of
/// what makes the guarantee true: a fractional degree may be rendered and dumped
/// and nothing else. Every caller that is not one of those two asks
/// [`Family::is_render_only`] and comes here.
pub fn render_only_refusal(kind: &str, what: &str) -> String {
    format!(
        "the {kind} family is render-only and cannot be {what}: it is reachable from a \
         written render or dump-field spec and from nowhere else"
    )
}

/// The mode a spec that says nothing about coloring gets.
pub const DEFAULT_MODE: &str = "smooth";

/// Settle what a spec's `mode` / `coloring` keys mean, and check the result.
///
/// Validating here rather than at the point of use is deliberate: a coloring
/// that cannot work should cost a message, not a minute of iteration followed by
/// a message.
///
/// The family is here because one catalogued setting depends on it — where
/// `itinerary` opens its address — and a **named** mode is the only thing it
/// moves. A coloring written out in full is taken exactly as written, defaults
/// and all: the wire says what it says, and this is what keeps the door the
/// comparison sheets rendered `z0` through open.
fn resolve_coloring(
    mode: Option<String>,
    coloring: Option<Coloring>,
    family: &Family,
) -> Result<(Coloring, Option<String>), String> {
    let (coloring, mode) = match (mode, coloring) {
        (Some(mode), Some(_)) => {
            return Err(format!(
                "the spec gives both mode '{mode}' and an explicit coloring; a mode is a \
                 coloring with a name, so give one or the other"
            ));
        }
        (Some(mode), None) => (mode::resolve(&mode, Some(family))?, Some(mode)),
        (None, Some(coloring)) => (coloring, None),
        (None, None) => (
            mode::resolve(DEFAULT_MODE, Some(family))?,
            Some(DEFAULT_MODE.to_string()),
        ),
    };
    coloring.validate()?;
    Ok((coloring, mode))
}

/// Degrees outside `[lowest, 5]` are refused rather than rendered: the families
/// above 5 have not been looked at, and silently rendering one would put an
/// unexamined picture into the corpus under a name that implies it belongs.
fn check_degree(degree: u32, lowest: u32) -> Result<(), String> {
    if (lowest..=5).contains(&degree) {
        Ok(())
    } else {
        Err(format!(
            "degree {degree} is outside the supported range {lowest}..=5"
        ))
    }
}

/// A fractional degree must be **between** two supported integer degrees and
/// must not be one of them.
///
/// The open interval is where the family means something: below 2 and above 5
/// are exponents nobody has looked at, exactly as [`check_degree`] says of the
/// integers. The whole-number refusal is the same rule the integer families
/// already keep — `multibrot` refuses degree 2 because that set is the
/// Mandelbrot set and one picture gets one name — read the other way round: an
/// integer exponent is the integer family's, so `degree: "3.0"` is refused
/// rather than rendered under a second name and cached under a second identity.
fn check_fractional_degree(degree: f64) -> Result<(), String> {
    if degree.fract() == 0.0 {
        return Err(format!(
            "family.degree {degree} is a whole number, and the whole degrees are the \
             mandelbrot and multibrot families' — render it as a multibrot at \
             degree {degree:.0} so that one picture keeps one name"
        ));
    }
    if !(2.0..=5.0).contains(&degree) {
        return Err(format!(
            "family.degree {degree} is outside the supported range 2..=5"
        ));
    }
    Ok(())
}

/// Parse one decimal string to `f64`, refusing anything that is not a finite
/// number. `f64`'s own parser is correctly rounded, so this is the nearest
/// representable value to what was written.
pub fn decimal(text: &str, what: &str) -> Result<f64, String> {
    let value: f64 = text
        .trim()
        .parse()
        .map_err(|_| format!("{what}: '{text}' is not a decimal number"))?;
    if value.is_finite() {
        Ok(value)
    } else {
        Err(format!("{what}: '{text}' is not finite"))
    }
}

fn pair(strings: &Pair, what: &str) -> Result<Complex<f64>, String> {
    Ok(Complex::new(
        decimal(&strings[0], &format!("{what}[0]"))?,
        decimal(&strings[1], &format!("{what}[1]"))?,
    ))
}

/// Render an `f64` as the decimal string it will be recorded as.
///
/// Rust's own formatting is what makes this safe to do: `{}` on an `f64` prints
/// the *shortest* decimal that parses back to the same bits, so nothing is lost
/// and nothing spurious is added. A coordinate the engine computed — a walk's
/// child frame, a family's home view — becomes an identity string here, and from
/// that point on it is the string that is the location.
pub fn to_decimal_string(value: f64) -> String {
    let text = format!("{value}");
    if text.contains(['.', 'e', 'E', 'n', 'i']) {
        text
    } else {
        format!("{text}.0")
    }
}

/// The name kept for the defaults this module fills in.
fn format_default(value: f64) -> String {
    to_decimal_string(value)
}

fn one() -> u32 {
    1
}
fn two() -> u32 {
    2
}
/// Where colormaps live, when a spec does not say.
pub fn default_colormap_dir() -> PathBuf {
    PathBuf::from("data").join("palettes")
}
fn origin() -> Pair {
    [format_default(0.0), format_default(0.0)]
}
fn phoenix_c() -> Pair {
    [format_default(PHOENIX_C.re), format_default(PHOENIX_C.im)]
}
fn phoenix_p() -> Pair {
    [format_default(PHOENIX_P.re), format_default(PHOENIX_P.im)]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal(family: &str) -> String {
        format!(
            r#"{{"schema":1,"family":{family},"resolution":[64,36],
                "colormap":"twilight_shifted","output":"out.png"}}"#
        )
    }

    fn resolve(family: &str) -> Resolved {
        RenderSpec::parse(&minimal(family))
            .unwrap()
            .resolve()
            .unwrap()
    }

    /// A viewport-less spec takes the family's derived row, and the cap follows
    /// from the width it lands on rather than from a second constant: the two
    /// were separate jobs sharing one number until the home table existed.
    #[test]
    fn a_minimal_spec_resolves_to_the_home_view_and_the_policy_cap() {
        let resolved = resolve(r#"{"kind":"mandelbrot"}"#);
        assert_eq!(resolved.family, Family::Multibrot { degree: 2 });
        let home = Family::Multibrot { degree: 2 }.home_view().unwrap();
        assert_eq!(resolved.view.center, home.center);
        assert_eq!(resolved.view.width, home.width);
        assert_eq!(resolved.maxiter, maxiter::for_width(home.width));
        assert_eq!(resolved.location.center_re, "-0.77");
        assert_eq!(resolved.location.width, "4.4");
    }

    #[test]
    fn a_julia_comes_home_to_the_origin() {
        let resolved = resolve(r#"{"kind":"julia","c":["-0.4","0.6"]}"#);
        assert_eq!(resolved.view.center, Complex::new(0.0, 0.0));
        assert_eq!(resolved.location.c.unwrap(), ["-0.4", "0.6"]);
    }

    /// A viewport-less render takes the *family's* row of the home table, not
    /// one shared frame: every row is derived from that family's own set, and
    /// Phoenix's is the narrowest and tallest of the five.
    #[test]
    fn phoenix_comes_home_to_its_own_wider_frame() {
        let resolved = resolve(r#"{"kind":"phoenix"}"#);
        assert_eq!(
            resolved.view.center,
            crate::family::CLASSIC_PHOENIX.home_view().unwrap().center
        );
        assert_eq!(
            resolved.view.width,
            crate::family::CLASSIC_PHOENIX.home_view().unwrap().width
        );
        assert_eq!(resolved.location.center_re, "0.04");
        assert_eq!(resolved.location.width, "5.0");
        assert!(resolved.view.width > resolve(r#"{"kind":"mandelbrot"}"#).view.width);
    }

    /// A viewport that gives only some of its keys fills the rest from the same
    /// row, rather than from whatever the last family to be rendered used.
    #[test]
    fn a_partial_viewport_takes_the_rest_of_the_family_s_home() {
        let spec = r#"{"schema":1,"family":{"kind":"phoenix"},"resolution":[64,36],
            "viewport":{"width":"2.0"},"colormap":"twilight_shifted","output":"o.png"}"#;
        let resolved = RenderSpec::parse(spec).unwrap().resolve().unwrap();
        assert_eq!(resolved.view.width, 2.0);
        assert_eq!(
            resolved.view.center,
            crate::family::CLASSIC_PHOENIX.home_view().unwrap().center
        );
    }

    #[test]
    fn phoenix_defaults_to_the_classic_instance() {
        let resolved = resolve(r#"{"kind":"phoenix"}"#);
        assert_eq!(
            resolved.family,
            Family::Phoenix {
                c: PHOENIX_C,
                p: PHOENIX_P,
                z_prev: Complex::new(0.0, 0.0),
            }
        );
        assert_eq!(resolved.location.z_prev.unwrap(), ["0.0", "0.0"]);
    }

    /// The decimal strings are the identity of a location, so they must survive
    /// the round trip through the engine unaltered — not reformatted, not
    /// re-rounded through `f64`.
    #[test]
    fn the_written_coordinates_survive_verbatim() {
        let spec = r#"{"schema":1,"family":{"kind":"mandelbrot"},
            "viewport":{"center_re":"0.41041350545462440","center_im":"0.20967482476903096",
                        "width":"0.5622541254857749"},
            "resolution":[64,36],"colormap":"twilight_shifted","output":"out.png"}"#;
        let resolved = RenderSpec::parse(spec).unwrap().resolve().unwrap();
        assert_eq!(resolved.location.center_re, "0.41041350545462440");
        assert_eq!(resolved.location.width, "0.5622541254857749");
    }

    /// A spec that says nothing about coloring renders the spine.
    #[test]
    fn coloring_defaults_to_the_smooth_mode() {
        let resolved = resolve(r#"{"kind":"mandelbrot"}"#);
        assert_eq!(resolved.mode.as_deref(), Some(DEFAULT_MODE));
        assert_eq!(resolved.coloring, Coloring::default());
    }

    #[test]
    fn a_named_mode_resolves_to_its_coloring() {
        let spec = r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
            "mode":"stripe","colormap":"twilight_shifted","output":"o.png"}"#;
        let resolved = RenderSpec::parse(spec).unwrap().resolve().unwrap();
        assert_eq!(resolved.mode.as_deref(), Some("stripe"));
        assert_eq!(
            resolved.coloring,
            crate::mode::resolve("stripe", None).unwrap()
        );
    }

    /// The adoption, at the door Python and the command line both come through:
    /// the *name* `itinerary` means the `z₁` address on a dynamical plane and the
    /// `z₀` one on a parameter plane, so the record of either says which it was.
    #[test]
    fn the_named_itinerary_mode_opens_its_address_where_the_plane_wants() {
        let opened = |family: &str| {
            let spec = format!(
                r#"{{"schema":1,"family":{family},"resolution":[8,8],"mode":"itinerary",
                    "colormap":"twilight_shifted","output":"o.png"}}"#
            );
            let resolved = RenderSpec::parse(&spec).unwrap().resolve().unwrap();
            assert_eq!(resolved.mode.as_deref(), Some("itinerary"));
            let crate::coloring::Coloring::Modulate { texture, .. } = resolved.coloring else {
                panic!("itinerary is a modulate");
            };
            let crate::field::FieldSpec::Itinerary { start, .. } = texture.field else {
                panic!("itinerary's texture is the address");
            };
            start
        };
        for family in [
            r#"{"kind":"julia","c":["-0.4","0.6"]}"#,
            r#"{"kind":"julia","degree":5,"c":["0.4","0"]}"#,
            r#"{"kind":"phoenix"}"#,
        ] {
            assert_eq!(opened(family), crate::field::AddressStart::Z1, "{family}");
        }
        for family in [
            r#"{"kind":"mandelbrot"}"#,
            r#"{"kind":"multibrot","degree":4}"#,
        ] {
            assert_eq!(opened(family), crate::field::AddressStart::Z0, "{family}");
        }
    }

    /// A coloring written out in full is nameless — the record echoes the
    /// coloring itself, which is the thing that determines the render.
    #[test]
    fn a_coloring_written_out_in_full_has_no_mode_name() {
        let spec = r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
            "coloring":{"kind":"field","field":{"kind":"tia"},"transform":"sqrt"},
            "colormap":"twilight_shifted","output":"o.png"}"#;
        let resolved = RenderSpec::parse(spec).unwrap().resolve().unwrap();
        assert_eq!(resolved.mode, None);
        assert_eq!(
            resolved.coloring,
            Coloring::Field {
                field: crate::field::FieldSpec::Tia,
                transform: crate::coloring::Transform::Sqrt,
            }
        );
    }

    /// The same coloring the parameter plane refuses resolves on a dynamical one,
    /// which is what makes the refusal a statement about the plane rather than
    /// about the option.
    #[test]
    fn the_z1_address_start_resolves_on_a_dynamical_plane() {
        for family in [
            r#"{"kind":"julia","c":["-0.4","0.6"]}"#,
            r#"{"kind":"phoenix"}"#,
        ] {
            let spec = format!(
                r#"{{"schema":1,"family":{family},"resolution":[8,8],
                    "coloring":{{"kind":"field",
                        "field":{{"kind":"itinerary","start":"z1"}}}},
                    "colormap":"twilight_shifted","output":"o.png"}}"#
            );
            let resolved = RenderSpec::parse(&spec).unwrap().resolve().unwrap();
            assert_eq!(resolved.mode, None);
            assert_eq!(
                resolved.coloring,
                Coloring::Field {
                    field: crate::field::FieldSpec::Itinerary {
                        sectors: 4,
                        weight_base: None,
                        depth: 26,
                        start: crate::field::AddressStart::Z1,
                    },
                    transform: crate::coloring::Transform::Linear,
                }
            );
        }
    }

    #[test]
    fn an_explicit_maxiter_wins_over_the_policy() {
        let spec = r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[64,36],
            "maxiter":37,"colormap":"twilight_shifted","output":"out.png"}"#;
        let resolved = RenderSpec::parse(spec).unwrap().resolve().unwrap();
        assert_eq!(resolved.maxiter, 37);
    }

    /// **The wire is the record**, so what a location serializes to is pinned
    /// as text rather than as a struct. Every existing family writes `degree` as
    /// a bare integer, which is what it wrote before [`Degree`] had a second
    /// shape at all — a record from any earlier run reads back and writes out
    /// the same bytes.
    #[test]
    fn an_integer_degree_still_serializes_as_a_bare_number() {
        let written = |family: &str| {
            serde_json::to_string(&resolve(family).location).expect("a location serializes")
        };
        assert_eq!(
            written(r#"{"kind":"mandelbrot"}"#),
            r#"{"family":"mandelbrot","degree":2,"center_re":"-0.77","center_im":"0.0","width":"4.4"}"#
        );
        assert_eq!(
            written(r#"{"kind":"multibrot","degree":5}"#),
            r#"{"family":"multibrot","degree":5,"center_re":"0.0","center_im":"0.0","width":"3.6"}"#
        );
        assert_eq!(
            written(r#"{"kind":"julia","c":["-0.4","0.6"]}"#),
            r#"{"family":"julia","degree":2,"center_re":"0.0","center_im":"0.0","width":"3.0",
               "c":["-0.4","0.6"]}"#
                .replace("\n               ", "")
        );
        assert_eq!(
            written(r#"{"kind":"phoenix"}"#),
            r#"{"family":"phoenix","degree":2,"center_re":"0.04","center_im":"0.0","width":"5.0",
               "c":["0.5667","0.0"],"p":["-0.5","0.0"],"z_prev":["0.0","0.0"]}"#
                .replace("\n               ", "")
        );
    }

    /// The record a location round-trips through has to survive it: a written
    /// record is read back by `recolor` and by every reader of a dump.
    #[test]
    fn a_location_round_trips_through_its_own_record() {
        for family in [
            r#"{"kind":"mandelbrot"}"#,
            r#"{"kind":"multibrot","degree":4}"#,
            r#"{"kind":"julia","degree":3,"c":["-0.4","0.6"]}"#,
            r#"{"kind":"phoenix"}"#,
        ] {
            let location = resolve(family).location;
            let text = serde_json::to_string(&location).unwrap();
            let back: Location = serde_json::from_str(&text).unwrap();
            assert_eq!(back, location, "{family}");
        }
        let fractional = fractional("2.5").location;
        let text = serde_json::to_string(&fractional).unwrap();
        let back: Location = serde_json::from_str(&text).unwrap();
        assert_eq!(back, fractional);
    }

    /// A spec that says where to look, which a fractional degree must.
    fn fractional(degree: &str) -> Resolved {
        let spec = format!(
            r#"{{"schema":1,"family":{{"kind":"fractional_multibrot","degree":"{degree}"}},
                "viewport":{{"center_re":"-0.4","center_im":"0","width":"4.0"}},
                "resolution":[64,36],"colormap":"twilight_shifted","output":"out.png"}}"#
        );
        RenderSpec::parse(&spec).unwrap().resolve().unwrap()
    }

    /// A fractional degree reaches the engine as a decimal string and is
    /// recorded as the string that was written, exactly like a coordinate. That
    /// is what keeps `2.5` and `2.50` one picture under two names rather than a
    /// rounding, and what keeps both distinct from every integer degree.
    #[test]
    fn a_fractional_degree_is_recorded_as_the_string_it_was_written_as() {
        let resolved = fractional("2.5");
        assert_eq!(resolved.family, Family::FractionalMultibrot { degree: 2.5 });
        assert_eq!(
            serde_json::to_string(&resolved.location).unwrap(),
            r#"{"family":"fractional_multibrot","degree":"2.5","center_re":"-0.4",
               "center_im":"0","width":"4.0"}"#
                .replace("\n               ", "")
        );
    }

    /// The identity a field cache and a replay are keyed on is the record, so
    /// what matters is that no two of these renders write the same one. Two
    /// fractional degrees differ, and a fractional degree differs from every
    /// integer one in the family name as well as in the degree.
    #[test]
    fn no_fractional_render_collides_with_another_render() {
        let mut written = std::collections::HashSet::new();
        for degree in ["2.5", "2.75", "3.5", "4.25"] {
            let text = serde_json::to_string(&fractional(degree).location).unwrap();
            assert!(written.insert(text.clone()), "{degree} collided: {text}");
        }
        for family in [
            r#"{"kind":"mandelbrot"}"#,
            r#"{"kind":"multibrot","degree":3}"#,
            r#"{"kind":"multibrot","degree":4}"#,
            r#"{"kind":"multibrot","degree":5}"#,
        ] {
            let text = serde_json::to_string(&resolve(family).location).unwrap();
            assert!(written.insert(text.clone()), "{family} collided: {text}");
        }
    }

    /// A render-only family has no row in the home table, so a spec that does
    /// not say where to look is refused rather than framed by a default nobody
    /// derived. Every missing key says so on its own.
    #[test]
    fn a_fractional_render_has_to_say_where_to_look() {
        for viewport in [
            r#""viewport":{"center_im":"0","width":"4.0"},"#,
            r#""viewport":{"center_re":"-0.4","width":"4.0"},"#,
            r#""viewport":{"center_re":"-0.4","center_im":"0"},"#,
            "",
        ] {
            let spec = format!(
                r#"{{"schema":1,"family":{{"kind":"fractional_multibrot","degree":"2.5"}},
                    {viewport}"resolution":[64,36],"colormap":"twilight_shifted",
                    "output":"out.png"}}"#
            );
            let message = RenderSpec::parse(&spec)
                .and_then(RenderSpec::resolve)
                .err()
                .unwrap_or_else(|| panic!("accepted: {spec}"));
            assert!(message.contains("no home"), "{message}");
        }
    }

    #[test]
    fn bad_specs_are_refused_rather_than_guessed_at() {
        let cases = [
            (minimal(r#"{"kind":"multibrot","degree":7}"#), "degree"),
            (minimal(r#"{"kind":"multibrot","degree":2}"#), "degree"),
            (minimal(r#"{"kind":"julia","c":["nope","0"]}"#), "decimal"),
            (minimal(r#"{"kind":"nautilus"}"#), "spec"),
            (
                r#"{"schema":2,"family":{"kind":"mandelbrot"},"resolution":[8,8],
                    "colormap":"x","output":"o.png"}"#
                    .into(),
                "schema",
            ),
            (
                r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[0,8],
                    "colormap":"x","output":"o.png"}"#
                    .into(),
                "resolution",
            ),
            (
                r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
                    "viewport":{"width":"-1"},"colormap":"x","output":"o.png"}"#
                    .into(),
                "positive",
            ),
            (
                r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
                    "viewport":{"width":"1e-20"},"colormap":"x","output":"o.png"}"#
                    .into(),
                "f64",
            ),
            (
                r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
                    "mode":"nautilus","colormap":"x","output":"o.png"}"#
                    .into(),
                "unknown mode",
            ),
            (
                r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
                    "mode":"stripe","coloring":{"kind":"field","field":{"kind":"tia"}},
                    "colormap":"x","output":"o.png"}"#
                    .into(),
                "one or the other",
            ),
            (
                r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
                    "coloring":{"kind":"composite",
                        "base":{"field":{"kind":"stripe","density":6}},
                        "texture":{"field":{"kind":"stripe","density":3}},
                        "blend":"screen"},
                    "colormap":"x","output":"o.png"}"#
                    .into(),
                "nothing to blend",
            ),
            (
                r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
                    "coloring":{"kind":"direct","shape":"ring","merge":"screen",
                        "start_color":"puce"},
                    "colormap":"x","output":"o.png"}"#
                    .into(),
                "start_color",
            ),
            (
                r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[8,8],
                    "coloring":{"kind":"field",
                        "field":{"kind":"itinerary","start":"z1"}},
                    "colormap":"x","output":"o.png"}"#
                    .into(),
                "dynamical-plane option",
            ),
            // A whole degree belongs to the integer family, so it is refused
            // here rather than rendered under a second name — the same rule that
            // refuses `multibrot` at degree 2, read the other way round.
            (
                minimal(r#"{"kind":"fractional_multibrot","degree":"3"}"#),
                "whole number",
            ),
            (
                minimal(r#"{"kind":"fractional_multibrot","degree":"4.0"}"#),
                "whole number",
            ),
            // And the interval is the one the integer families cover: below and
            // above it are exponents nobody has looked at.
            (
                minimal(r#"{"kind":"fractional_multibrot","degree":"1.5"}"#),
                "supported range",
            ),
            (
                minimal(r#"{"kind":"fractional_multibrot","degree":"5.5"}"#),
                "supported range",
            ),
            (
                minimal(r#"{"kind":"fractional_multibrot","degree":"two and a half"}"#),
                "decimal",
            ),
            // The degree is a string here for the same reason a coordinate is,
            // and a spec that writes it as a number is refused rather than read
            // through an f64 nobody wrote down.
            (
                minimal(r#"{"kind":"fractional_multibrot","degree":2.5}"#),
                "spec",
            ),
            (minimal(r#"{"kind":"fractional_multibrot"}"#), "spec"),
        ];
        for (text, expected) in cases {
            let outcome = RenderSpec::parse(&text).and_then(RenderSpec::resolve);
            let message = outcome.err().unwrap_or_else(|| panic!("accepted: {text}"));
            assert!(
                message.contains(expected),
                "wanted '{expected}' in error, got: {message}"
            );
        }
    }
}
