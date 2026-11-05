// The style module's whole glue, for a browser or Node: load `style_wasm.wasm`, open a
// session on one picture, measure it, draw it in tiles or in one pass.
//
//   const styles = await load(bytes);              // an ArrayBuffer, typed array or Response
//   const picture = styles.open(request);          // engine/README.md's *The style module*
//   picture.measure({width: 320, height: 200});    // a preview's balance, or {} for the frame's
//   const rgba = picture.tile(0, 0, 256, 256);     // Uint8ClampedArray, width·height·4
//   picture.close();
//
// Every buffer is copied out of the module's memory before it is freed, so what a call
// returns stays valid however the memory grows afterwards.

const decoder = new TextDecoder();
const encoder = new TextEncoder();

export async function load(source) {
  let bytes = source;
  if (typeof Response !== "undefined" && source instanceof Response) {
    bytes = await source.arrayBuffer();
  }
  const { instance } = await WebAssembly.instantiate(bytes, {});
  return new StyleModule(instance.exports);
}

export class StyleModule {
  constructor(exports) {
    this.exports = exports;
  }

  // A JSON request in, the length-prefixed JSON answer out.
  call(name, ...args) {
    return this.text(this.exports[name](...args));
  }

  // A pointer arrives as a signed i32; past 2 GiB of memory it would read negative.
  text(ptr) {
    ptr >>>= 0;
    const memory = new Uint8Array(this.exports.memory.buffer);
    const len = new DataView(this.exports.memory.buffer).getUint32(ptr, true);
    const value = JSON.parse(decoder.decode(memory.slice(ptr + 4, ptr + 4 + len)));
    this.exports.dealloc(ptr, len + 4);
    return value;
  }

  bytes(ptr, len) {
    ptr >>>= 0;
    if (ptr === 0) {
      throw new Error(this.text(this.exports.last_error()));
    }
    const out = new Uint8ClampedArray(this.exports.memory.buffer.slice(ptr, ptr + len));
    this.exports.dealloc(ptr, len);
    return out;
  }

  open(request) {
    const raw = encoder.encode(typeof request === "string" ? request : JSON.stringify(request));
    const ptr = this.exports.alloc(raw.length);
    new Uint8Array(this.exports.memory.buffer, ptr, raw.length).set(raw);
    const answer = this.call("open", ptr, raw.length);
    this.exports.dealloc(ptr, raw.length);
    if (!answer.ok) {
      throw new Error(answer.why);
    }
    return new Picture(this, answer);
  }
}

export class Picture {
  constructor(module, summary) {
    this.module = module;
    this.handle = summary.handle;
    this.summary = summary;
    [this.width, this.height] = summary.resolution;
  }

  // Every frame-wide statistic and the tone curve, over a frame of this view: the
  // picture's own with no arguments (tiles then stitch to `frame()`), else a preview.
  measure({ width = 0, height = 0, supersample = 0 } = {}) {
    for (const n of [width, height, supersample]) {
      if (!Number.isInteger(n) || n < 0) {
        throw new RangeError(`a measure frame is whole pixels; got ${n}`);
      }
    }
    const answer = this.module.call("measure", this.handle, width, height, supersample);
    if (!answer.ok) {
      throw new Error(answer.why);
    }
    return answer;
  }

  // Whole pixels: the length read back must be the one the module drew.
  tile(x, y, width, height) {
    [x, y, width, height] = [x, y, width, height].map((n) => {
      if (!Number.isInteger(n) || n < 0) {
        throw new RangeError(`a tile is whole pixels; got ${n}`);
      }
      return n;
    });
    const ptr = this.module.exports.tile(this.handle, x, y, width, height);
    return this.module.bytes(ptr, width * height * 4);
  }

  frame() {
    const ptr = this.module.exports.frame(this.handle);
    return this.module.bytes(ptr, this.width * this.height * 4);
  }

  close() {
    this.module.exports.close(this.handle);
  }
}
