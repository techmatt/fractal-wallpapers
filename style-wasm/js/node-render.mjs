// Draw a list of style requests under Node, for `fractal-wallpapers style wasm-parity` and `wasm-speed`:
//
//   node node-render.mjs <style_wasm.wasm> <jobs.json> <out dir>
//
// `jobs.json` is `[{id, request, draw}]`, `draw` one of `frame` (one pass) or
// `{measure: {width, height, supersample}, tile: [w, h]}` (measured, then tiled). Each
// picture is written raw as `<out dir>/<id>.rgba`; `<out dir>/results.jsonl` gets one
// line per job, with its seconds. One thread: the module has none of its own.

import { readFileSync, writeFileSync, appendFileSync } from "node:fs";
import { join } from "node:path";
import { performance } from "node:perf_hooks";

import { load } from "./style-wasm.mjs";

const [wasmPath, jobsPath, outDir] = process.argv.slice(2);
const styles = await load(readFileSync(wasmPath));
const jobs = JSON.parse(readFileSync(jobsPath, "utf8"));
const results = join(outDir, "results.jsonl");

for (const job of jobs) {
  const row = { id: job.id };
  let picture = null;
  try {
    let started = performance.now();
    picture = styles.open(job.request);
    row.open = (performance.now() - started) / 1000;
    let rgba;
    started = performance.now();
    if (job.draw === "frame") {
      rgba = picture.frame();
    } else {
      row.measured = picture.measure(job.draw.measure || {});
      row.measure = (performance.now() - started) / 1000;
      started = performance.now();
      const [tw, th] = job.draw.tile;
      rgba = new Uint8ClampedArray(picture.width * picture.height * 4);
      for (let y = 0; y < picture.height; y += th) {
        for (let x = 0; x < picture.width; x += tw) {
          const w = Math.min(tw, picture.width - x);
          const h = Math.min(th, picture.height - y);
          const part = picture.tile(x, y, w, h);
          for (let r = 0; r < h; r++) {
            rgba.set(part.subarray(r * w * 4, (r + 1) * w * 4), ((y + r) * picture.width + x) * 4);
          }
        }
      }
    }
    row.draw = (performance.now() - started) / 1000;
    row.resolution = [picture.width, picture.height];
    row.maxiter = picture.summary.maxiter;
    writeFileSync(join(outDir, `${job.id}.rgba`), rgba);
    row.ok = true;
  } catch (error) {
    row.ok = false;
    row.why = String(error && error.message ? error.message : error);
  } finally {
    if (picture) {
      picture.close();
    }
  }
  appendFileSync(results, JSON.stringify(row) + "\n");
}
