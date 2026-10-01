# Chapter 1 — The Big Picture

## 1.1 The problem in one paragraph

Burning fossil fuels (petrol, diesel, coal, gas) releases **CO₂**, the main cause of climate
change. Cities produce most of it. To cut emissions, a city first needs to know **how much it
emits and where**. Today that number comes from **inventories**: spreadsheets built from fuel
sales, factory records and population data. They are slow (1–2 years late), coarse (whole cities
or states), and often disagree with each other. For Pune, we found two respected inventories that
differ by a factor of **3.2**. So: **can we measure a city's CO₂ emissions from space instead?**

## 1.2 Why that's hard

CO₂ is everywhere: about **420 ppm** (420 molecules of CO₂ per million molecules of air), all
over the planet. A city like Pune adds only a tiny extra bump on top, roughly **0.1 ppm** in the
column of air above and downwind of it. That's like spotting one extra drop of ink in a bathtub
that is already blue. CO₂ satellites exist (NASA's OCO-2 and OCO-3), but they are noisy (each
measurement wobbles by ~0.5–1 ppm) and only occasionally look at Pune.

## 1.3 The clever trick: use NO₂ as a "tracer"

When fuel burns, it releases CO₂ **and** also **NO₂** (nitrogen dioxide, a brown polluting gas).
NO₂ is much easier to see from space:
- there's very little of it in clean air, so a city's NO₂ **stands out clearly**;
- it only survives **a few hours** before chemistry destroys it, so the NO₂ you see is fresh,
  local and recent, not from some other continent;
- the European satellite instrument **TROPOMI** measures it **every day** at high resolution.

So the plan (from the base paper, Xie et al. 2026, which did this for Shandong, China) is:
1. Measure how much **NO₂** (really NOx, see chapter 2) the city emits, from satellite images.
2. Multiply by how much **CO₂ is emitted per unit of NOx** (a "ratio" taken from an inventory).
3. That gives CO₂.

**The weak point:** step 2. The ratio depends on *what* is burning (a truck, a factory boiler,
a household stove) and varies about threefold. The base paper says this ratio is its **largest
single source of error**.

## 1.4 Our project's question

> Can **combining several satellites** (NO₂ + CO₂ + CO) plus **weather** plus
> **human-activity maps** estimate urban CO₂ better than relying on NO₂ alone?

Our study area is a **33 km strip along the Old Mumbai–Pune Highway**, from Shivajinagar to
Talegaon Dabhade. It was chosen because factories (MIDC industrial areas at Bhosari, Chinchwad,
Talegaon) and heavy traffic sit side by side, a hard test for telling sources apart.

## 1.5 What we actually did (Phase 1), in one picture

```
 SATELLITE NO₂ (TROPOMI, 1,004 days)    WIND (ERA5, every overpass)
            │                                   │
            └──────────┬────────────────────────┘
                       ▼
    1. Where is the source?  (calm-day average → peak in central Pune)
    2. How much NOx?         (rotate every day by its wind → average → fit a plume curve)
                             → 0.66 kg/s NOx, lifetime 1.1 h (after the D19 fix)
    3. Where exactly?        (flux-divergence map → two hotspots: Pune core + Pimpri-Chinchwad)
                             → corridor = 21% of the city
                       │
                       ▼
    4. NOx → CO₂ using an inventory ratio (EDGAR: 172 kg CO₂ per kg NOx)
                             → 2.83 Mt CO₂/yr ± 32%
                       │
          ┌────────────┴─────────────┐
          ▼                          ▼
 5. Check with CO₂ satellites   6. Constrain the ratio with CO satellite data
    (OCO-3/OCO-2, 8 days)          (TROPOMI CO, 907 days)
    → Pune is too small to see.    → Pune emits more CO per NOx than the inventory says
      Gives only an upper limit.     → CO:NOx 16.7 ≈ inventory's → ratio 163
                                   → 2.79 Mt CO₂/yr (annual) [1.79–4.36]  ← HEADLINE
```

## 1.6 The answers so far

1. **Pune + Pimpri-Chinchwad emit about 2.8 million tonnes of fossil CO₂ per year** (annual mean; 95% range 1.8–4.4).
   The two inventories say 3.6 (EDGAR) and 11.8 (ODIAC), and ODIAC is ruled out by our range.
2. **The biggest source is central Pune** (Swargate/Camp), just outside our corridor. The second
   is **Pimpri–Chinchwad**, inside it. The corridor emits about **21%** of the metro's total.
3. **CO₂ satellites can't see Pune yet.** The plume (~0.1 ppm) is smaller than the instrument noise
   (~0.5–1 ppm). They only tell us Pune emits *less than* ~7–14 Mt/yr.
4. **Adding TROPOMI CO measurably improves the estimate**: it shrinks the biggest error term from 25% to
   about 10%. **That is the answer to the research question for Phase 1:** multi-satellite data help, but
   through CO, not through direct CO₂ measurement.
5. **Testing caught our own mistake:** the first plume fit reached too far downwind and included a second
   source, underestimating NOx by ~20%. It was found, fixed and documented (D19; chapter 7).

## 1.7 How the project is organised in time

The proposal has **8 phases over 26 weeks**:
- **Feasibility (weeks 0–2):** four checks that the data exist (chapter 5).
- **Phase 1:** the NO₂ → CO₂ baseline. **Done** (chapter 6).
- **Phase 2:** collect human-activity layers (night lights, roads, buildings) on a 1 km grid.
- **Phase 3:** build "labels" (a CO₂ value for each 1 km cell).
- **Phases 4–6:** machine learning experiments A/B/C/D: does adding each data source help?
- **Phase 7:** validation and uncertainty.
- **Phase 8:** write-up.

## 1.8 One idea to hold on to

Everything we did follows one rule, from the proposal's success criteria: **every number must
be checked before it is trusted, and every claim must not exceed what the data supports.** That's
why we tested every method on fake data with known answers first (chapter 6). It's why we
reported "OCO can't see Pune" rather than forcing a result. And it's why chapter 7 lists all
our mistakes. Examiners reward this.
