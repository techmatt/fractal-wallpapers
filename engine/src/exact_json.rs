//! JSON read so that every float is the nearest double to its decimal — test support.
//!
//! The engine's `serde_json` runs without `float_roundtrip`, and the stored answers the
//! tests compare against are seventeen-digit doubles a lossy parse can land one unit of
//! last place away. Only the tests read JSON floats that way, so only the tests get this.

/// JSON text to a `serde_json::Value` whose every float is **the nearest double to
/// its decimal**, which is `str::parse`'s answer and not always `serde_json`'s.
///
/// Without its `float_roundtrip` feature `serde_json` may land a seventeen-digit
/// double one unit of last place away, and a statistic one ulp off derives a curve
/// one ulp off: 426 of the 4,479 backfill rows did, which is the count the website's
/// crate met before it enabled the feature. The engine leaves the feature off — a
/// link's `level=` is read by `str::parse` and never passes through `serde_json` —
/// so the stored answers these tests compare against are read exactly here instead.
pub fn exactly(text: &str) -> serde_json::Value {
    let mut reader = Exact {
        bytes: text.as_bytes(),
        at: 0,
    };
    let value = reader.value();
    reader.space();
    assert_eq!(
        reader.at,
        reader.bytes.len(),
        "trailing text after the JSON value"
    );
    value
}

struct Exact<'a> {
    bytes: &'a [u8],
    at: usize,
}

impl Exact<'_> {
    fn space(&mut self) {
        while self.at < self.bytes.len() && self.bytes[self.at].is_ascii_whitespace() {
            self.at += 1;
        }
    }

    fn eat(&mut self, byte: u8) {
        self.space();
        assert_eq!(
            self.bytes.get(self.at),
            Some(&byte),
            "JSON at byte {}",
            self.at
        );
        self.at += 1;
    }

    fn value(&mut self) -> serde_json::Value {
        use serde_json::Value;
        self.space();
        match self.bytes[self.at] {
            b'{' => {
                self.at += 1;
                let mut map = serde_json::Map::new();
                self.space();
                if self.bytes[self.at] == b'}' {
                    self.at += 1;
                    return Value::Object(map);
                }
                loop {
                    self.space();
                    let Value::String(key) = self.value() else {
                        panic!("a JSON key is a string")
                    };
                    self.eat(b':');
                    map.insert(key, self.value());
                    self.space();
                    self.at += 1;
                    if self.bytes[self.at - 1] == b'}' {
                        return Value::Object(map);
                    }
                }
            }
            b'[' => {
                self.at += 1;
                let mut items = Vec::new();
                self.space();
                if self.bytes[self.at] == b']' {
                    self.at += 1;
                    return Value::Array(items);
                }
                loop {
                    items.push(self.value());
                    self.space();
                    self.at += 1;
                    if self.bytes[self.at - 1] == b']' {
                        return Value::Array(items);
                    }
                }
            }
            b'"' => {
                // Strings go through serde_json itself, escapes and all: only the
                // numbers are what this reader exists for.
                let start = self.at;
                self.at += 1;
                while self.bytes[self.at] != b'"' {
                    self.at += if self.bytes[self.at] == b'\\' { 2 } else { 1 };
                }
                self.at += 1;
                serde_json::from_slice(&self.bytes[start..self.at]).expect("a JSON string")
            }
            b't' | b'f' | b'n' => {
                let word = [&b"true"[..], b"false", b"null"]
                    .into_iter()
                    .find(|word| self.bytes[self.at..].starts_with(word))
                    .expect("a JSON literal");
                self.at += word.len();
                serde_json::from_slice(word).expect("a JSON literal")
            }
            _ => {
                let start = self.at;
                while self.at < self.bytes.len()
                    && matches!(
                        self.bytes[self.at],
                        b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9'
                    )
                {
                    self.at += 1;
                }
                let number = std::str::from_utf8(&self.bytes[start..self.at]).unwrap();
                if number.contains(['.', 'e', 'E']) {
                    let value: f64 = number.parse().expect("a JSON number");
                    Value::Number(serde_json::Number::from_f64(value).expect("finite"))
                } else {
                    serde_json::from_str(number).expect("a JSON integer")
                }
            }
        }
    }
}
