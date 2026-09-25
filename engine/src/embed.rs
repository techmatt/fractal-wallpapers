//! A finished picture with its explorer link written into its metadata, pixels untouched.
//!
//! A port of the wallpaper project's `curation/embed_link.py`, which mirrors the
//! website's `explorer/stamp.js`: the same fields in the same places in the same bytes,
//! so a picture `render-link` writes, a release wallpaper and a download from the
//! explorer are one kind of file, and one dropped on the explorer's canvas reopens its
//! view. `tests/test_render_link.py` holds this port to the Python writer byte for byte.
//!
//! What goes in:
//!
//! - **The tag**, `fractal-explorer <query>`: a PNG `iTXt` chunk under the keyword
//!   `fractal-explorer`, a JPEG `COM` segment. The explorer's own reader.
//! - **An XMP packet** whose `dc:source` is the absolute URL: a PNG `iTXt` under
//!   `XML:com.adobe.xmp`, a JPEG `APP1`.
//! - **In a JPEG, EXIF**: IFD0's `ImageDescription`, the URL again.
//!
//! Every chunk or segment a decoder turns into pixels is the same bytes in the same
//! order. A foreign XMP or EXIF is kept and ours goes without that half; a stamp of ours
//! already there is replaced rather than joined.

use crate::link::EXPLORER_URL;

/// What a file of ours says in front of its link, and the PNG keyword it travels under.
pub const TAG: &str = "fractal-explorer";
const XMP_KEYWORD: &str = "XML:com.adobe.xmp";
const XMP_SIGNATURE: &[u8] = b"http://ns.adobe.com/xap/1.0/\x00";
const EXIF_SIGNATURE: &[u8] = b"Exif\x00\x00";
const IMAGE_DESCRIPTION: u16 = 0x010E;
const COMMENT_LIMIT: usize = 0xFFFF - 2;
const PNG_MAGIC: &[u8] = b"\x89PNG\r\n\x1a\n";

/// The absolute link: the explorer, then the query.
pub fn url_of(query: &str) -> String {
    format!("{EXPLORER_URL}?{query}")
}

fn payload_of(query: &str) -> String {
    let query = query.trim();
    format!("{TAG} {}", query.strip_prefix('?').unwrap_or(query))
}

/// The query an explorer URL carries, whatever its host: `stamp.js`'s `queryOfUrl`,
/// `^[a-z][a-z0-9+.-]*://[^?#\s]*/explorer/(?:index\.html)?\?([^#\s]+)$`, ignoring case.
fn query_of_url(url: &str) -> Option<&str> {
    let url = url.trim();
    let (scheme, rest) = url.split_once("://")?;
    let mut letters = scheme.chars();
    if !letters.next()?.is_ascii_alphabetic()
        || !letters.all(|c| c.is_ascii_alphanumeric() || "+.-".contains(c))
    {
        return None;
    }
    let (path, query) = rest.split_once('?')?;
    if path.contains(['#']) || path.chars().any(char::is_whitespace) {
        return None;
    }
    let lower = path.to_ascii_lowercase();
    if !(lower.ends_with("/explorer/") || lower.ends_with("/explorer/index.html")) {
        return None;
    }
    if query.is_empty() || query.contains('#') || query.chars().any(char::is_whitespace) {
        return None;
    }
    Some(query)
}

/// The packet `stamp.js`'s `xmpOf` writes, character for character.
fn xmp_of(url: &str) -> String {
    let text = url
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;");
    format!(
        "<?xpacket begin=\"\u{feff}\" id=\"W5M0MpCehiHzreSzNTczkc9d\"?>\
         <x:xmpmeta xmlns:x=\"adobe:ns:meta/\">\
         <rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\">\
         <rdf:Description rdf:about=\"\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\">\
         <dc:source>{text}</dc:source>\
         </rdf:Description></rdf:RDF></x:xmpmeta>\
         <?xpacket end=\"r\"?>"
    )
}

/// The `dc:source` a packet names, unescaped, element or attribute form.
fn source_of(packet: &str) -> Option<String> {
    let found = packet
        .find("<dc:source>")
        .and_then(|at| {
            let rest = &packet[at + "<dc:source>".len()..];
            let end = rest.find('<')?;
            rest[end..]
                .starts_with("</dc:source>")
                .then(|| &rest[..end])
        })
        .or_else(|| {
            let at = packet.find("dc:source=\"")?;
            let rest = &packet[at + "dc:source=\"".len()..];
            Some(&rest[..rest.find('"')?])
        })?;
    Some(
        found
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&apos;", "'")
            .replace("&amp;", "&"),
    )
}

fn our_xmp(packet: &str) -> bool {
    source_of(packet).is_some_and(|source| query_of_url(&source).is_some())
}

/// IFD0 with one entry, `ImageDescription`, big-endian; `None` for a non-ASCII URL.
fn exif_of(url: &str) -> Option<Vec<u8>> {
    if !url.bytes().all(|b| (0x20..=0x7e).contains(&b)) {
        return None;
    }
    let mut text = url.as_bytes().to_vec();
    text.push(0);
    let mut out = EXIF_SIGNATURE.to_vec();
    out.extend_from_slice(b"MM");
    out.extend_from_slice(&42u16.to_be_bytes());
    out.extend_from_slice(&8u32.to_be_bytes());
    out.extend_from_slice(&1u16.to_be_bytes());
    out.extend_from_slice(&IMAGE_DESCRIPTION.to_be_bytes());
    out.extend_from_slice(&2u16.to_be_bytes());
    out.extend_from_slice(&(text.len() as u32).to_be_bytes());
    out.extend_from_slice(&26u32.to_be_bytes());
    out.extend_from_slice(&0u32.to_be_bytes());
    out.extend_from_slice(&text);
    Some(out)
}

/// IFD0's `ImageDescription`, either byte order.
fn description_of(block: &[u8]) -> Option<String> {
    let tiff = block.strip_prefix(EXIF_SIGNATURE)?;
    if tiff.len() < 8 {
        return None;
    }
    let big = match &tiff[..2] {
        b"MM" => true,
        b"II" => false,
        _ => return None,
    };
    let number = |at: usize, size: usize| -> Option<usize> {
        let bytes = tiff.get(at..at + size)?;
        Some(if big {
            bytes.iter().fold(0usize, |n, &b| (n << 8) | b as usize)
        } else {
            bytes
                .iter()
                .rev()
                .fold(0usize, |n, &b| (n << 8) | b as usize)
        })
    };
    let ifd = number(4, 4)?;
    for index in 0..number(ifd, 2)? {
        let at = ifd + 2 + index * 12;
        if at + 12 > tiff.len() {
            return None;
        }
        if number(at, 2)? != IMAGE_DESCRIPTION as usize || number(at + 2, 2)? != 2 {
            continue;
        }
        let count = number(at + 4, 4)?;
        let start = if count <= 4 {
            at + 8
        } else {
            number(at + 8, 4)?
        };
        let text = tiff.get(start..(start + count).min(tiff.len()))?;
        let text = text.split(|&b| b == 0).next().unwrap_or_default();
        return Some(text.iter().map(|&b| b as char).collect());
    }
    None
}

fn our_exif(block: &[u8]) -> bool {
    description_of(block).is_some_and(|text| query_of_url(&text).is_some())
}

fn link_of(payload: &str) -> Option<&str> {
    let text = payload.trim();
    let query = text.strip_prefix(TAG)?.strip_prefix(' ')?.trim();
    let query = query.strip_prefix('?').unwrap_or(query);
    (!query.is_empty()).then_some(query)
}

// --------------------------------------------------------------------------- PNG

/// CRC-32 (ISO-HDLC), which is what a PNG chunk and `zlib.crc32` use.
fn crc32(parts: &[&[u8]]) -> u32 {
    let mut crc = 0xFFFF_FFFFu32;
    for part in parts {
        for &byte in *part {
            crc ^= byte as u32;
            for _ in 0..8 {
                crc = if crc & 1 != 0 {
                    (crc >> 1) ^ 0xEDB8_8320
                } else {
                    crc >> 1
                };
            }
        }
    }
    !crc
}

/// Each chunk as `(type, start, end, body)`; stops at one that runs past the end.
fn png_chunks(data: &[u8]) -> Vec<([u8; 4], usize, usize, &[u8])> {
    let mut out = Vec::new();
    let mut at = 8;
    while at + 12 <= data.len() {
        let length = u32::from_be_bytes(data[at..at + 4].try_into().unwrap()) as usize;
        let end = at + 12 + length;
        if length > 0x7FFF_FFFF || end > data.len() {
            break;
        }
        let kind: [u8; 4] = data[at + 4..at + 8].try_into().unwrap();
        out.push((kind, at, end, &data[at + 8..at + 8 + length]));
        at = end;
    }
    out
}

fn chunk(kind: &[u8; 4], body: &[u8]) -> Vec<u8> {
    let mut out = (body.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(kind);
    out.extend_from_slice(body);
    out.extend_from_slice(&crc32(&[kind, body]).to_be_bytes());
    out
}

fn itxt(keyword: &str, text: &str) -> Vec<u8> {
    let mut body = keyword.as_bytes().to_vec();
    body.extend_from_slice(&[0, 0, 0, 0, 0]);
    body.extend_from_slice(text.as_bytes());
    chunk(b"iTXt", &body)
}

/// A `tEXt` or uncompressed `iTXt` chunk's keyword and text.
fn text_of(kind: &[u8; 4], body: &[u8]) -> Option<(String, String)> {
    let first = body.iter().position(|&b| b == 0)?;
    let keyword: String = body[..first].iter().map(|&b| b as char).collect();
    if kind == b"tEXt" {
        return Some((
            keyword,
            body[first + 1..].iter().map(|&b| b as char).collect(),
        ));
    }
    if kind != b"iTXt" || body.get(first + 1) != Some(&0) {
        return None;
    }
    let language = first + 3 + body.get(first + 3..)?.iter().position(|&b| b == 0)?;
    let translated = language + 1 + body.get(language + 1..)?.iter().position(|&b| b == 0)?;
    let text = std::str::from_utf8(&body[translated + 1..]).ok()?;
    Some((keyword, text.to_string()))
}

/// `embed_png`: the tag's chunk then the packet, straight after `IHDR`.
pub fn embed_png(data: &[u8], query: &str) -> Result<Vec<u8>, String> {
    if !data.starts_with(PNG_MAGIC) {
        return Err("not a PNG".into());
    }
    let chunks = png_chunks(data);
    let Some(&(first, _, header_end, _)) = chunks.first() else {
        return Err("a PNG opens with IHDR".into());
    };
    if &first != b"IHDR" {
        return Err("a PNG opens with IHDR".into());
    }
    let mut kept: Vec<&[u8]> = Vec::new();
    let mut foreign = false;
    for &(kind, start, end, body) in &chunks[1..] {
        let said = if &kind == b"tEXt" || &kind == b"iTXt" {
            text_of(&kind, body)
        } else {
            None
        };
        if let Some((keyword, text)) = &said {
            if keyword == TAG {
                continue;
            }
            if &kind == b"iTXt" && keyword == XMP_KEYWORD {
                if our_xmp(text) {
                    continue;
                }
                foreign = true;
            }
        }
        kept.push(&data[start..end]);
    }
    let last = chunks.last().map_or(header_end, |chunk| chunk.2);
    let mut out = data[..header_end].to_vec();
    out.extend(itxt(TAG, &payload_of(query)));
    if !foreign {
        out.extend(itxt(XMP_KEYWORD, &xmp_of(&url_of(query))));
    }
    for raw in kept {
        out.extend_from_slice(raw);
    }
    out.extend_from_slice(&data[last..]);
    Ok(out)
}

// -------------------------------------------------------------------------- JPEG

/// One marker segment: `(marker, start, end, body)`.
type Segment<'a> = (u8, usize, usize, &'a [u8]);

/// Every marker segment before the scan as `(marker, start, end, body)`, and where the
/// scan starts. Standalone markers carry an empty body.
fn jpeg_segments(data: &[u8]) -> (Vec<Segment<'_>>, usize) {
    let mut out = Vec::new();
    let mut at = 2;
    while at + 4 <= data.len() && data[at] == 0xFF {
        let marker = data[at + 1];
        if marker == 0xD9 || marker == 0xDA {
            break;
        }
        if marker == 0x01 || (0xD0..=0xD7).contains(&marker) {
            out.push((marker, at, at + 2, &data[at..at]));
            at += 2;
            continue;
        }
        let length = u16::from_be_bytes([data[at + 2], data[at + 3]]) as usize;
        if length < 2 || at + 2 + length > data.len() {
            break;
        }
        out.push((marker, at, at + 2 + length, &data[at + 4..at + 2 + length]));
        at += 2 + length;
    }
    (out, at)
}

fn segment(marker: u8, body: &[u8]) -> Result<Vec<u8>, String> {
    if body.len() + 2 > 0xFFFF {
        return Err(format!(
            "a JPEG segment holds {} bytes and this one is longer",
            0xFFFF - 2
        ));
    }
    let mut out = vec![0xFF, marker];
    out.extend_from_slice(&((body.len() + 2) as u16).to_be_bytes());
    out.extend_from_slice(body);
    Ok(out)
}

/// `embed_jpeg`: EXIF and XMP at the end of the leading `APPn` run, then the tag's
/// comment, and every other segment and the scan exactly as they were.
pub fn embed_jpeg(data: &[u8], query: &str) -> Result<Vec<u8>, String> {
    if !data.starts_with(&[0xFF, 0xD8]) {
        return Err("not a JPEG".into());
    }
    let payload = payload_of(query);
    if payload.len() > COMMENT_LIMIT {
        return Err(format!(
            "a JPEG comment holds {COMMENT_LIMIT} bytes and this link is longer"
        ));
    }
    let (segments, scan) = jpeg_segments(data);
    let mut kept: Vec<(u8, &[u8])> = Vec::new();
    let (mut foreign_exif, mut foreign_xmp) = (false, false);
    for &(marker, start, end, body) in &segments {
        if marker == 0xFE && link_of(&String::from_utf8_lossy(body)).is_some() {
            continue;
        }
        if marker == 0xE1 {
            if body.starts_with(EXIF_SIGNATURE) {
                if our_exif(body) {
                    continue;
                }
                foreign_exif = true;
            } else if let Some(packet) = body.strip_prefix(XMP_SIGNATURE) {
                if our_xmp(&String::from_utf8_lossy(packet)) {
                    continue;
                }
                foreign_xmp = true;
            }
        }
        kept.push((marker, &data[start..end]));
    }
    let insert = kept
        .iter()
        .take_while(|(marker, _)| (0xE0..=0xEF).contains(marker))
        .count();

    let url = url_of(query);
    let mut added = Vec::new();
    if !foreign_exif && let Some(exif) = exif_of(&url) {
        added.push(segment(0xE1, &exif)?);
    }
    if !foreign_xmp {
        let mut body = XMP_SIGNATURE.to_vec();
        body.extend_from_slice(xmp_of(&url).as_bytes());
        added.push(segment(0xE1, &body)?);
    }
    added.push(segment(0xFE, payload.as_bytes())?);

    let mut out = data[..2].to_vec();
    for (_, raw) in &kept[..insert] {
        out.extend_from_slice(raw);
    }
    for raw in added {
        out.extend(raw);
    }
    for (_, raw) in &kept[insert..] {
        out.extend_from_slice(raw);
    }
    out.extend_from_slice(&data[scan..]);
    Ok(out)
}

/// Whichever of the two these bytes are, with the link in it.
pub fn embed(data: &[u8], query: &str) -> Result<Vec<u8>, String> {
    if data.starts_with(PNG_MAGIC) {
        embed_png(data, query)
    } else if data.starts_with(&[0xFF, 0xD8]) {
        embed_jpeg(data, query)
    } else {
        Err("neither a PNG nor a JPEG".into())
    }
}

/// Write the link into a finished picture in place, through a temporary and a rename, so
/// a reader never meets half a file.
pub fn embed_file(path: &std::path::Path, query: &str) -> Result<(), String> {
    let data = std::fs::read(path).map_err(|e| format!("read {}: {e}", path.display()))?;
    let stamped = embed(&data, query).map_err(|e| format!("{}: {e}", path.display()))?;
    let stem = path.file_stem().unwrap_or_default().to_string_lossy();
    let suffix = path
        .extension()
        .map(|ext| format!(".{}", ext.to_string_lossy()))
        .unwrap_or_default();
    let scratch = path.with_file_name(format!("{stem}.embedding{suffix}"));
    std::fs::write(&scratch, stamped).map_err(|e| format!("write {}: {e}", scratch.display()))?;
    std::fs::rename(&scratch, path).map_err(|e| format!("rename {}: {e}", scratch.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_crc_is_zlibs() {
        // zlib.crc32(b"IEND") and zlib.crc32(b"123456789").
        assert_eq!(crc32(&[b"IEND"]), 0xAE42_6082);
        assert_eq!(crc32(&[b"1234", b"56789"]), 0xCBF4_3926);
    }

    #[test]
    fn an_explorer_url_is_recognized_whatever_its_host() {
        let query = "v=4&p=viridis";
        assert_eq!(query_of_url(&url_of(query)), Some(query));
        assert_eq!(
            query_of_url("http://localhost:8000/explorer/index.html?v=4&p=viridis"),
            Some(query)
        );
        assert_eq!(query_of_url("https://example.com/other/?v=4"), None);
        assert_eq!(source_of(&xmp_of(&url_of(query))), Some(url_of(query)));
    }

    /// A stamp read back is the link, and stamping twice leaves one stamp — for both
    /// formats, over the bytes the engine's own writers make.
    #[test]
    fn stamping_twice_leaves_one_stamp() {
        let pixels: Vec<u8> = (0..4 * 3 * 3).map(|i| (i * 7) as u8).collect();
        let dir = std::env::temp_dir().join(format!("embed-test-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        for name in ["a.png", "a.jpg"] {
            let path = dir.join(name);
            crate::resample::write_image(&path, &pixels, 4, 3).unwrap();
            let plain = std::fs::read(&path).unwrap();
            let once = embed(&plain, "v=4&p=viridis").unwrap();
            let twice = embed(&once, "v=4&p=viridis").unwrap();
            assert_eq!(once, twice, "{name}");
            let other = embed(&once, "v=4&p=magma").unwrap();
            assert_eq!(other, embed(&plain, "v=4&p=magma").unwrap(), "{name}");
            assert!(once.len() > plain.len());
        }
        let _ = std::fs::remove_dir_all(&dir);
    }
}
