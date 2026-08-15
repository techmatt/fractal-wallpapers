"""What a partition costs: active minutes per unit of currency, measured in-run.

The allocator spends its clock in proportion to `deficit / price`, so the price is
half of every decision it makes. It is measured, not assumed: a batch's active
minutes are charged to the partition it served, the currency that batch produced
is credited to the same partition, and the ratio is the estimate.

## The estimate is a ratio of two averages, not an average of ratios

```text
minutes ← (1−a)·minutes + a·(this batch's minutes)
units   ← (1−a)·units   + a·(this batch's units)
price   =  minutes / max(units, one class-3)
```

Both accumulators step **once per served batch**, and holding them apart rather
than folding them into one smoothed ratio is the whole point: a batch with
minutes and no finds has a numerator to contribute even though it has no ratio to
sample.

**A zero-yield batch prices itself.** The obvious design defers such a batch —
carry its minutes forward and price them whenever yield next arrives — and it
fails in two directions at once. The carried minutes land on whichever batch
happens to close next, so a partition's cost is charged to a moment rather than
spread over the batches that incurred it; and a partition that is never served
again never flushes, so its last sample is final. That second one is a *one-way
lockout*: share is `deficit / price`, an over-priced partition is served less, and
being served less is exactly what stops the price being revised. In the source
project it cost one partition — the largest deficit and the highest ratio of the
nine — its last sixty-two batches.

So a zero-yield batch is an ordinary case. The numerator takes the minutes, the
denominator decays, and the price rises: strictly, finitely, bounded per batch by
the smoothing rate and overall by the clamp. Sustained fruitless service *should*
raise a price. The defect was a frozen price and evidence held hostage to a credit
that never came, never a high one.

**A batch with units but no minutes does not close a window.** A zero numerator
would price the partition as free, which is the one direction the allocator
amplifies. Its units wait for the minutes they will be spent against.

## The seed is a measurement, and the clamp is a band around it

The seed table ships as data ([`data/supply/cost_to_find.json`]) and the estimate
is bounded to a factor around whatever seed it was handed. The clamp is not
tidiness: the numerator of a price is a scorer's opinion, so a scorer that
over-calls one family makes that family look cheap and buys it more service —
the winner's curse, one level up. The clamp bounds that to a factor, and the
universal floor bounds it again from the other side. The raw estimate is kept and
reported beside the clamped one, so the clamp is visible rather than silent.

## Regenerating the seed

The measured table is the *evidence*: `sum(minutes) / sum(units)` over a finished
run, pooled by summing both accumulators and dividing once. Averaging several
runs' live estimates instead would weight a run by how many windows it happened
to flush rather than by how much work it did.

The seed a run is handed is that table shrunk geometrically toward its own
median. Shrinkage rather than a bound, because a bound cannot tell *implausible*
from *the thing the run was run to find out* — at the edge it reports the bound
and discards the measurement. Shrinkage never discards: every partition keeps its
measured order and `ALPHA` of its log-distance from the median, so a tenfold
signal survives as a fivefold one. The knob is confidence in the population, not
a plausibility opinion about any partition.

A partition that produced less than one whole class-4's worth of currency is not
priced. It carries the seed price and is stamped `defaulted`: `minutes/0` is not
a large price, it is no measurement — and writing the row out of the table
entirely would make "never served" indistinguishable from "never tracked".
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

from fractal_wallpapers.paths import repo_root
from fractal_wallpapers.supply.currency import CLASS_WEIGHT
from fractal_wallpapers.supply.partitions import ALL_PARTITIONS

SCHEMA = 1

#: Active minutes per unit of currency, for a partition nothing has measured.
SEED_PRICE = 3.0

#: The per-served-batch smoothing weight, applied to the minutes and the units
#: accumulators alike. A window's pull on the price is therefore units-weighted:
#: exactly this weight for a batch carrying as much currency as the accumulator
#: already holds, and less for a thinner one.
PRICE_EMA = 0.15

#: How much currency the seed price is worth as evidence — one class 4 — so the
#: first comparable batch displaces about `PRICE_EMA` of it.
PRICE_SEED_UNITS = 1.0

#: The denominator's floor: the smallest credit there is. It is what bounds a run
#: of fruitless batches — the partition prices as if one class 3 were about to
#: arrive, not as if nothing ever would.
PRICE_MIN_UNITS = CLASS_WEIGHT[3]

#: The factor the live estimate may stray from its seed by, when no shipped table
#: says otherwise.
PRICE_CLAMP = 4.0

#: Fruitless minutes before a partition is capped out of service.
CAP_MINUTES = 25.0

#: The evidence floor a row must clear to be priced rather than defaulted: one
#: whole class-4's worth of currency. Not a new number — that is already the
#: definition of one unit, and "at least one whole unit in the denominator" is the
#: weakest statement that separates a rate from a fraction of a single class 3.
MIN_UNITS = CLASS_WEIGHT[4]

#: The shrinkage weight on the measured price, in log space. One would be the raw
#: measured table; zero a flat table at the median, the measurement discarded.
ALPHA = 0.9

#: The band the live estimate may occupy around a regularized seed.
REGULARIZED_CLAMP = 16.0


def seed_table_path() -> Path:
    """The seed table a run is handed."""
    return repo_root() / "data" / "supply" / "cost_to_find.json"


def measured_table_path() -> Path:
    """The measured table the seed is derived from. Evidence; nothing reads it
    at run time."""
    return repo_root() / "data" / "supply" / "cost_to_find_measured.json"


class PriceTableError(ValueError):
    """A price table is missing, is not one, or prices nothing."""


def load_table(path: Path | None = None) -> dict:
    """A price table, proved to be one before anything is derived from it."""
    path = seed_table_path() if path is None else Path(path)
    if not path.is_file():
        raise PriceTableError(
            f"{path} is missing — there is no cost-to-find seed to run on. Regenerate it "
            f"from a finished run: fractal-wallpapers derive-prices --run <dir> --regularize"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise PriceTableError(f"{path}: schema {document.get('schema')!r}, expected {SCHEMA}")
    if not (document.get("prices") or {}):
        raise PriceTableError(f"{path}: empty `prices` block; nothing to run on")
    return document


class CostToFind:
    """Per-partition active minutes per unit of currency, measured as a run goes.

    Three counters per partition and they answer different questions, which is why
    none of them is shared: the **window** is minutes and units since the last
    sample, the **dry clock** is minutes since the last credit and is what caps a
    partition out of service, and the **totals** are what a later derivation reads
    to regenerate the seed table.
    """

    def __init__(self, partitions=ALL_PARTITIONS, config: dict | None = None):
        config = config or {}
        table = config.get("prices") or {}
        default = float(config.get("seed_price", SEED_PRICE))
        self.partitions = list(partitions)
        self.seed = {p: float(table.get(p, default)) for p in self.partitions}
        self.ema = float(config.get("price_ema", PRICE_EMA))
        self.clamp = float(config.get("price_clamp", PRICE_CLAMP))
        self.cap_minutes = float(config.get("cap_minutes", CAP_MINUTES))
        self.min_units = float(config.get("price_min_units", PRICE_MIN_UNITS))
        # At or above `min_units`, so the estimate starts at exactly the seed: the
        # seed is a price, and the pair (seed × units, units) is how much evidence
        # it is being given.
        self.seed_units = max(
            float(config.get("price_seed_units", PRICE_SEED_UNITS)), self.min_units
        )
        self.raw = dict(self.seed)
        self.ema_minutes = {p: self.seed[p] * self.seed_units for p in self.partitions}
        self.ema_units = dict.fromkeys(self.partitions, self.seed_units)
        self.minutes = dict.fromkeys(self.partitions, 0.0)
        self.units = dict.fromkeys(self.partitions, 0.0)
        self.dry_minutes = dict.fromkeys(self.partitions, 0.0)
        self.window_minutes = dict.fromkeys(self.partitions, 0.0)
        self.window_units = dict.fromkeys(self.partitions, 0.0)
        self.samples = dict.fromkeys(self.partitions, 0)
        self.capped: set = set()

    # ------------------------------------------------------------ the price

    def price(self, partition: str) -> float:
        """The estimate, clamped into its band around the seed."""
        low = self.seed[partition] / self.clamp
        high = self.seed[partition] * self.clamp
        return min(max(self.raw[partition], low), high)

    def prices(self) -> dict:
        return {p: self.price(p) for p in self.partitions}

    # -------------------------------------------------------- the accounting

    def charge(self, partition: str, minutes: float) -> bool:
        """Account active minutes to a partition. Returns whether it just capped.

        A partition that burns `cap_minutes` with no credit is capped out of
        service until something re-opens it: an unbounded stall on a queue full of
        dead ground would otherwise eat that partition's whole share of the run.
        """
        self.minutes[partition] += minutes
        self.dry_minutes[partition] += minutes
        self.window_minutes[partition] += minutes
        if partition not in self.capped and self.dry_minutes[partition] >= self.cap_minutes:
            self.capped.add(partition)
            return True
        return False

    def credit(self, partition: str, units: float) -> None:
        """Currency just found in a partition.

        Zero units is not a credit and must not reset the dry clock, or a
        partition producing nothing but refusals would never cap. The estimate
        moves in [`end_window`] and never here: a find is an event and a price is
        a rate, so one find is not one sample.
        """
        if units <= 0:
            return
        self.units[partition] += units
        self.window_units[partition] += units
        self.dry_minutes[partition] = 0.0
        self.capped.discard(partition)

    @staticmethod
    def sample_weight(ema: float, units: float, units_ema: float) -> float:
        """How hard a window carrying `units` pulls the price.

        The ratio-of-averages update is algebraically a sample average on
        `minutes/units` at this weight, so the rule is a pure function rather than
        something inferred from a run: monotone in `units`, inside `[0, 1)`, and
        exactly `ema` when the window carries as much currency as the accumulator
        already holds.
        """
        denominator = (1.0 - ema) * units_ema + ema * max(0.0, units)
        return (ema * max(0.0, units) / denominator) if denominator > 0 else 0.0

    def end_window(self) -> dict:
        """Close the price window: one step for every partition with charged
        minutes in it. Called once per served batch.

        Returns `{partition: sample}` for every window closed, where the sample is
        that window's own minutes-per-unit rate, or `None` for a fruitless window —
        which has no rate but did move the price. A caller can log what moved
        rather than diff two price tables.
        """
        taken = {}
        for partition in self.partitions:
            minutes = self.window_minutes[partition]
            units = self.window_units[partition]
            if minutes <= 0:
                continue
            a = self.ema
            self.ema_minutes[partition] = (1 - a) * self.ema_minutes[partition] + a * minutes
            self.ema_units[partition] = (1 - a) * self.ema_units[partition] + a * units
            self.raw[partition] = self.ema_minutes[partition] / max(
                self.ema_units[partition], self.min_units
            )
            self.samples[partition] += 1
            self.window_minutes[partition] = 0.0
            self.window_units[partition] = 0.0
            taken[partition] = (minutes / units) if units > 0 else None
        return taken

    def reopen_caps(self) -> None:
        """Let every capped partition back into service."""
        for partition in self.capped:
            self.dry_minutes[partition] = 0.0
        self.capped.clear()

    # ------------------------------------------------------------- the state

    def state(self) -> dict:
        return {
            "seed": self.seed,
            "raw": self.raw,
            "ema_minutes": self.ema_minutes,
            "ema_units": self.ema_units,
            "minutes": self.minutes,
            "units": self.units,
            "dry_minutes": self.dry_minutes,
            "window_minutes": self.window_minutes,
            "window_units": self.window_units,
            "samples": self.samples,
            "capped": sorted(self.capped),
        }

    def load_state(self, state: dict) -> None:
        for name in (
            "seed",
            "raw",
            "ema_minutes",
            "ema_units",
            "minutes",
            "units",
            "dry_minutes",
            "window_minutes",
            "window_units",
        ):
            getattr(self, name).update({p: float(v) for p, v in (state.get(name) or {}).items()})
        self.samples.update({p: int(v) for p, v in (state.get("samples") or {}).items()})
        self.capped = set(state.get("capped", []))

    def summary(self) -> dict:
        return {
            "price": {p: round(v, 4) for p, v in sorted(self.prices().items())},
            "price_raw": {p: round(v, 4) for p, v in sorted(self.raw.items())},
            "seed": {p: round(v, 4) for p, v in sorted(self.seed.items())},
            "clamped": sorted(
                p for p in self.partitions if abs(self.price(p) - self.raw[p]) > 1e-9
            ),
            "units_found": {p: round(v, 3) for p, v in sorted(self.units.items())},
            "minutes_spent": {p: round(v, 3) for p, v in sorted(self.minutes.items())},
            # The aggregate the estimate is an estimate OF, quoted beside it:
            # reading the two together is what makes a mis-estimate visible.
            "price_aggregate": {
                p: round(self.minutes[p] / self.units[p], 4)
                for p in sorted(self.partitions)
                if self.units[p] > 0
            },
            "samples": {p: v for p, v in sorted(self.samples.items()) if v},
            # The denominator the price is quoted over, and whether the floor is
            # holding it up. A floored partition's price is a censored reading,
            # not a measured rate, and that should not need the state to recover.
            "evidence": {p: round(v, 4) for p, v in sorted(self.ema_units.items())},
            "censored": sorted(p for p, v in self.ema_units.items() if v < self.min_units),
            "capped": sorted(self.capped),
            "clamp_factor": self.clamp,
        }


# --------------------------------------------------------------------------- #
# Regenerating the seed
# --------------------------------------------------------------------------- #


def pool(blocks) -> tuple[dict, dict]:
    """`(minutes, units)` summed per partition across finished runs."""
    minutes: dict = {}
    units: dict = {}
    for block in blocks:
        for partition, value in (block.get("minutes_spent") or {}).items():
            minutes[partition] = minutes.get(partition, 0.0) + float(value)
        for partition, value in (block.get("units_found") or {}).items():
            units[partition] = units.get(partition, 0.0) + float(value)
    for partition in set(minutes) | set(units):
        minutes.setdefault(partition, 0.0)
        units.setdefault(partition, 0.0)
    return minutes, units


def derive(blocks, sources, partitions=ALL_PARTITIONS) -> dict:
    """The measured table, plus the provenance that separates a measured row from
    a defaulted one without re-running the derivation."""
    minutes, units = pool(blocks)
    prices, raw, defaulted, thin = {}, {}, [], []
    for partition in partitions:
        found, spent = units.get(partition, 0.0), minutes.get(partition, 0.0)
        if found > 0:
            raw[partition] = round(spent / found, 3)
        if found < MIN_UNITS:
            prices[partition] = SEED_PRICE
            defaulted.append(partition)
            if found > 0:
                thin.append(partition)
            continue
        prices[partition] = round(spent / found, 3)

    measured = [p for p in partitions if p not in defaulted]
    if not measured:
        named = [s.get("name", "?") if isinstance(s, dict) else str(s) for s in sources]
        raise PriceTableError(
            f"no partition in {named} is priceable — none reached {MIN_UNITS} units of "
            f"currency, so every row would be the flat seed, and a table byte-identical to "
            f"the seed reports itself as a measurement it is not."
        )
    return {
        "schema": SCHEMA,
        "_doc": (
            "MEASURED cost to find, per partition: active minutes per unit of currency. "
            "Evidence; nothing reads it at run time. Regenerate with "
            "`fractal-wallpapers derive-prices`; never hand-edit a row."
        ),
        "prices": prices,
        "seed_price": SEED_PRICE,
        # Written at derivation time, so the smoothing rate reaches a run through
        # a regeneration rather than through an edit to a shipped table.
        "price_ema": PRICE_EMA,
        "price_clamp": PRICE_CLAMP,
        "cap_minutes": CAP_MINUTES,
        "_provenance": {
            "estimand": "sum(minutes) / sum(units), pooled across the source runs",
            "source_runs": list(sources),
            "minutes": {p: round(minutes.get(p, 0.0), 3) for p in partitions},
            "units": {p: round(units.get(p, 0.0), 3) for p in partitions},
            "price_raw": raw,
            "measured": measured,
            "defaulted": defaulted,
            "thin": thin,
            "min_units": MIN_UNITS,
        },
    }


def shrink(price: float, target: float, alpha: float = ALPHA) -> float:
    """One price, shrunk geometrically toward `target`. THE formula, in one place.

    Geometric and not arithmetic because a price is a rate: the distance between
    0.1 and 1.0 minutes per unit is the same as between 1.0 and 10.0.
    """
    return math.exp(alpha * math.log(price) + (1.0 - alpha) * math.log(target))


def spread(prices) -> float:
    """`max/min` over a set of prices — the quantity `ALPHA` is chosen against."""
    values = [float(v) for v in prices]
    low = min(values)
    return (max(values) / low) if low > 0 else math.inf


def regularize(
    table: dict, *, alpha: float = ALPHA, clamp: float = REGULARIZED_CLAMP, source: str = ""
) -> dict:
    """The seed a run is handed: the measured table shrunk toward its own median.

    The measured rows set the shrink target and are the only rows shrunk. A
    defaulted row passes through at the seed price — shrinking it would
    manufacture a price for a partition nobody priced, and letting it into the
    median would drag the target toward the flat seed by however many partitions
    went unserved.

    Seed only. The in-run estimate is untouched and converges on whatever the run
    measures; regularizing that would be a run that cannot learn its own costs.
    """
    prices = {p: float(v) for p, v in (table.get("prices") or {}).items()}
    provenance = table.get("_provenance") or {}
    defaulted = set(provenance.get("defaulted") or [])
    measured = [p for p in prices if p not in defaulted]
    if not measured:
        raise PriceTableError(
            "every row in the source table is defaulted, so there is no measured population "
            "to shrink toward and no measurement to shrink. Regularizing it would produce a "
            "flat table wearing a derived name."
        )
    target = float(statistics.median(prices[p] for p in measured))
    out, columns = {}, {}
    for partition in sorted(prices):
        if partition in defaulted:
            out[partition] = prices[partition]
        else:
            out[partition] = round(shrink(prices[partition], target, alpha), 4)
        columns[partition] = {
            "measured": prices[partition],
            "regularized": out[partition],
            "status": "defaulted" if partition in defaulted else "measured",
        }
    return {
        "schema": SCHEMA,
        "_doc": (
            "The cost-to-find SEED a run is handed: the measured table shrunk geometrically "
            "toward its own median price. Regenerate with `fractal-wallpapers derive-prices "
            "--regularize`; never hand-edit a row, and never edit the measured table."
        ),
        "prices": out,
        "seed_price": float(table.get("seed_price", SEED_PRICE)),
        "price_ema": float(table.get("price_ema", PRICE_EMA)),
        "price_clamp": float(clamp),
        "cap_minutes": float(table.get("cap_minutes", CAP_MINUTES)),
        "_provenance": {
            "estimand": "the measured seed, shrunk toward the measured median in LOG space",
            "formula": "seed = exp(alpha·ln(price) + (1−alpha)·ln(median(measured prices)))",
            "alpha": alpha,
            "price_clamp": float(clamp),
            "price_clamp_applies_to": ("the in-run estimate only; it moves no price in this file"),
            "shrink_target": "median",
            "shrink_target_value": round(target, 6),
            "source_table": source,
            "source_measured": measured,
            "source_defaulted": sorted(defaulted),
            "columns": columns,
            "spread_measured": round(spread([prices[p] for p in measured]), 3),
            "spread_regularized": round(spread([out[p] for p in measured]), 3),
        },
    }


__all__ = [
    "ALPHA",
    "CAP_MINUTES",
    "MIN_UNITS",
    "PRICE_CLAMP",
    "PRICE_EMA",
    "PRICE_MIN_UNITS",
    "PRICE_SEED_UNITS",
    "REGULARIZED_CLAMP",
    "SEED_PRICE",
    "CostToFind",
    "PriceTableError",
    "derive",
    "load_table",
    "measured_table_path",
    "pool",
    "regularize",
    "seed_table_path",
    "shrink",
    "spread",
]
