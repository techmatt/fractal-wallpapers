// Draw a list of style requests under Node, for `fractal-wallpapers style wasm-parity` and `wasm-speed`:
//
//   node node-render.mjs <style_wasm.wasm> <jobs.json> <out dir> [workers]
//
// `jobs.json` is `[{id, request, draw}]`, `draw` one of `frame` (one pass) or
// `{measure: {width, height, supersample}, tile: [w, h]}` (measured, then tiled; with
// `shared: true` another picture measures and this one imports its report, with
// `from: <request>` that request's picture is measured and recoloured to this one). Each
// picture is written raw as `<out dir>/<id>.rgba`; `<out dir>/results.jsonl` gets one
// line per job, with its seconds, in the order the jobs finish. The module has no threads
// of its own, so `workers` (default 1) worker threads each hold an instance and take the
// next job off one shared counter: a job is always one thread's work, and its seconds
// are comparable only when the workers leave it a core.

import { readFileSync, writeFileSync, appendFileSync } from "node:fs";
import { join } from "node:path";
import { performance } from "node:perf_hooks";
import { Worker, isMainThread, parentPort, workerData } from "node:worker_threads";

import { load } from "./style-wasm.mjs";

function draw(styles, job, outDir) {
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
      if (job.draw.from) {
        // A recolour: measure the `from` request's picture, then switch it to this one.
        picture.close();
        picture = styles.open(job.draw.from);
        picture.measure(job.draw.measure || {});
        row.measured = picture.recolour(job.request);
      } else if (job.draw.shared) {
        // The shared measure: another picture measures, this one takes its report.
        const measurer = styles.open(job.request);
        try {
          measurer.measure(job.draw.measure || {});
          row.measured = picture.importMeasure(measurer.exportMeasure());
        } finally {
          measurer.close();
        }
      } else {
        row.measured = picture.measure(job.draw.measure || {});
      }
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
  return row;
}

if (isMainThread) {
  const [wasmPath, jobsPath, outDir, workers] = process.argv.slice(2);
  const count = JSON.parse(readFileSync(jobsPath, "utf8")).length;
  const results = join(outDir, "results.jsonl");
  // The next job's index, shared: each worker adds one and draws what it took.
  const next = new SharedArrayBuffer(4);
  const threads = Math.max(1, Math.min(Number(workers) || 1, count));
  for (let i = 0; i < threads; i++) {
    const worker = new Worker(new URL(import.meta.url), {
      workerData: { wasmPath, jobsPath, outDir, next },
    });
    worker.on("message", (row) => appendFileSync(results, JSON.stringify(row) + "\n"));
    // A worker lost (the module would not load, a crash outside a job's own catch):
    // stop at once, since the caller discards a failed run's rows anyway.
    worker.on("error", (error) => {
      console.error(error);
      process.exit(1);
    });
  }
} else {
  const { wasmPath, jobsPath, outDir, next } = workerData;
  const styles = await load(readFileSync(wasmPath));
  const jobs = JSON.parse(readFileSync(jobsPath, "utf8"));
  const counter = new Int32Array(next);
  for (;;) {
    const index = Atomics.add(counter, 0, 1);
    if (index >= jobs.length) {
      break;
    }
    parentPort.postMessage(draw(styles, jobs[index], outDir));
  }
}
