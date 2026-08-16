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
use crate::family::{Family, PHOENIX_C, PHOENIX_P};
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

/// The decimal strings that identify this render, kept verbatim.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Location {
    pub family: String,
    pub degree: u32,
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
        let (family, kind, c, p, z_prev) = self.family.resolve()?;

        let home = family.home_view();
        let center_re = self
            .viewport
            .center_re
            .unwrap_or_else(|| format_default(home.center.re));
        let center_im = self
            .viewport
            .center_im
            .unwrap_or_else(|| format_default(home.center.im));
        let width = self
            .viewport
            .width
            .unwrap_or_else(|| format_default(home.width));

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

        let (coloring, mode) = resolve_coloring(self.mode, self.coloring)?;
        self.palette.validate()?;

        Ok(Resolved {
            maxiter: self
                .maxiter
                .unwrap_or_else(|| maxiter::for_width(plane_width)),
            coloring,
            palette: self.palette,
            mode,
            location: Location {
                family: kind.to_string(),
                degree: family.degree(),
                center_re,
                center_im,
                width,
                c,
                p,
                z_prev,
            },
            family,
            view,
            colormap: self.colormap,
            colormap_dir: self.colormap_dir,
            output: self.output,
        })
    }
}

impl FamilySpec {
    /// Parse the constants and name the family. Returns the family, its spec
    /// name, and whichever constant strings apply to it.
    #[allow(clippy::type_complexity)]
    pub fn resolve(
        self,
    ) -> Result<
        (
            Family,
            &'static str,
            Option<Pair>,
            Option<Pair>,
            Option<Pair>,
        ),
        String,
    > {
        match self {
            FamilySpec::Mandelbrot => Ok((
                Family::Multibrot { degree: 2 },
                "mandelbrot",
                None,
                None,
                None,
            )),
            FamilySpec::Multibrot { degree } => {
                check_degree(degree, 3)?;
                Ok((Family::Multibrot { degree }, "multibrot", None, None, None))
            }
            FamilySpec::Julia { degree, c } => {
                check_degree(degree, 2)?;
                let family = Family::Julia {
                    degree,
                    c: pair(&c, "family.c")?,
                };
                Ok((family, "julia", Some(c), None, None))
            }
            FamilySpec::Phoenix { c, p, z_prev } => {
                let family = Family::Phoenix {
                    c: pair(&c, "family.c")?,
                    p: pair(&p, "family.p")?,
                    z_prev: pair(&z_prev, "family.z_prev")?,
                };
                Ok((family, "phoenix", Some(c), Some(p), Some(z_prev)))
            }
        }
    }
}

/// The mode a spec that says nothing about coloring gets.
pub const DEFAULT_MODE: &str = "smooth";

/// Settle what a spec's `mode` / `coloring` keys mean, and check the result.
///
/// Validating here rather than at the point of use is deliberate: a coloring
/// that cannot work should cost a message, not a minute of iteration followed by
/// a message.
fn resolve_coloring(
    mode: Option<String>,
    coloring: Option<Coloring>,
) -> Result<(Coloring, Option<String>), String> {
    let (coloring, mode) = match (mode, coloring) {
        (Some(mode), Some(_)) => {
            return Err(format!(
                "the spec gives both mode '{mode}' and an explicit coloring; a mode is a \
                 coloring with a name, so give one or the other"
            ));
        }
        (Some(mode), None) => (mode::resolve(&mode)?, Some(mode)),
        (None, Some(coloring)) => (coloring, None),
        (None, None) => (mode::resolve(DEFAULT_MODE)?, Some(DEFAULT_MODE.to_string())),
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

    #[test]
    fn a_minimal_spec_resolves_to_the_home_view_and_the_policy_cap() {
        let resolved = resolve(r#"{"kind":"mandelbrot"}"#);
        assert_eq!(resolved.family, Family::Multibrot { degree: 2 });
        let home = Family::Multibrot { degree: 2 }.home_view();
        assert_eq!(resolved.view.center, home.center);
        assert_eq!(resolved.view.width, home.width);
        assert_eq!(resolved.maxiter, maxiter::BASE as u32);
        assert_eq!(resolved.location.center_re, "-0.5");
        assert_eq!(resolved.location.width, "3.0");
    }

    #[test]
    fn a_julia_comes_home_to_the_origin() {
        let resolved = resolve(r#"{"kind":"julia","c":["-0.4","0.6"]}"#);
        assert_eq!(resolved.view.center, Complex::new(0.0, 0.0));
        assert_eq!(resolved.location.c.unwrap(), ["-0.4", "0.6"]);
    }

    /// A viewport-less render takes the *family's* row of the home table, not
    /// one shared frame: Phoenix's set is tall and is framed wider than the
    /// plane view every other family comes home to.
    #[test]
    fn phoenix_comes_home_to_its_own_wider_frame() {
        let resolved = resolve(r#"{"kind":"phoenix"}"#);
        assert_eq!(resolved.view.center, crate::family::PHOENIX_HOME.center);
        assert_eq!(resolved.view.width, crate::family::PHOENIX_HOME.width);
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
        assert_eq!(resolved.view.center, crate::family::PHOENIX_HOME.center);
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
        assert_eq!(resolved.coloring, crate::mode::resolve("stripe").unwrap());
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

    #[test]
    fn an_explicit_maxiter_wins_over_the_policy() {
        let spec = r#"{"schema":1,"family":{"kind":"mandelbrot"},"resolution":[64,36],
            "maxiter":37,"colormap":"twilight_shifted","output":"out.png"}"#;
        let resolved = RenderSpec::parse(spec).unwrap().resolve().unwrap();
        assert_eq!(resolved.maxiter, 37);
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
