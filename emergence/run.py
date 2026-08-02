#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punto de entrada.

    python -m emergence.run sim       --generations 80 --seed 1
    python -m emergence.run sim       --mode mute --generations 80 --seed 1
    python -m emergence.run ablation  --seeds 10 --generations 80

El experimento que justifica el proyecto es `ablation`: los mismos
mundos, los mismos parametros, las mismas semillas, y un unico cambio
--- si el canal transmite o no. Si las tribus con lenguaje no viven
mejor, el modelo lo dira.
"""

import argparse
import json
import os
import random
import sys

from .audit import audit, report as audit_report
from .config import Config
from .culture import informe_A, informe_B, prueba_A, prueba_B
from .console import setup as _console_setup
from .episodes import Channel, MODE_LANGUAGE, MODE_MUTE, MODE_NOISE, MODES
from .fastrand import FastRandom
from .metrics import (SemanticLog, bootstrap_diff, cliffs_delta,
                      concept_alignment, generalization, lexical_coherence,
                      lexical_distance, lexicon_stats, mean, naming_coverage,
                      naming_table, prediction_score, stdev,
                      topographic_similarity, zipf_profile)
from .tribe import Population
from .world import World, load_spec

PROBE_SEED = 20260801        # bateria de medida fija: la misma para todo


def simulate(mode, seed, cfg, n_tribes, generations, metrics_every=5,
             verbose=False, recorder=None, on_generation=None):
    """Una corrida. Devuelve (registros_por_generacion, estado_final)."""
    # streams independientes: el mundo y los estimulos no dependen del modo
    rng_world = FastRandom(seed * 7919 + 11)
    rng_agents = FastRandom(seed)
    rng_channel = FastRandom(seed * 104729 + 7)
    rng_probe = FastRandom(PROBE_SEED)
    rng_metric = FastRandom(PROBE_SEED + 1)

    spec = load_spec(cfg.world)
    cfg.dim, cfg.n_places = spec.dim, spec.n_places
    world = World(rng_world, spec)
    probes = world.probe_set(rng_probe, per_kind=10)
    channel = Channel(mode, cfg, rng_channel)
    pop = Population(n_tribes, cfg, rng_agents)

    records = []
    slog = [SemanticLog() for _ in range(n_tribes)]
    for gen in range(1, generations + 1):
        acc, births = pop.step(world, channel, rng_agents, gen, recorder)
        summ = pop.summary()
        rec = {"gen": gen, "mode": mode, "seed": seed, "births": births}
        rec.update(summ)
        rec.update(acc.rates())
        rec["deaths_total"] = sum(pop.deaths().values())

        last = (gen == generations)
        if metrics_every and (gen % metrics_every == 0 or last or gen == 1):
            alive = pop.living()
            rec["prediction"] = prediction_score(alive[:40], probes)
            rec["alignment"] = concept_alignment(alive, probes, rng_metric)
            # la coherencia es INTRA-tribu: cada tribu es una comunidad de
            # habla distinta. Medirla sobre la poblacion entera la topa
            # artificialmente en ~1/n_tribus, porque tribus aisladas
            # inventan palabras distintas para lo mismo — que es justo el
            # fenomeno que queremos observar, no un fallo de convergencia.
            per_tribe = [lexical_coherence(t.living(), world, rng_metric, 6)
                         for t in pop.tribes if t.living()]
            rec["coherence"] = mean(per_tribe)
            rec.update({("lex_" + k): v for k, v in lexicon_stats(alive).items()})
            rec["topsim"] = topographic_similarity(alive, world, rng_metric)
            rec["coverage"] = generalization(alive, world, rng_metric)
            for ti, t in enumerate(pop.tribes):
                slog[ti].record(gen, t.living(), world, rng_metric)
        records.append(rec)
        if on_generation is not None:
            on_generation(gen, pop, world, rng_metric, rec)

        if verbose:
            print(f"  gen {gen:3d} pop={summ['pop']:3d} "
                  f"E={summ['energy']:5.1f} exito={rec['success']:.2f} "
                  f"señal={rec['signal_rate']:.2f} cats={summ['categories']:.1f}")
        if pop.extinct():
            break

    return records, {"pop": pop, "world": world, "rng": rng_metric,
                     "channel": channel, "semantic": slog}


# ---------------------------------------------------------------------
# informe final legible
# ---------------------------------------------------------------------

def report(records, state, cfg, n_tribes):
    pop, world, rng = state["pop"], state["world"], state["rng"]
    alive = pop.living()
    line = "=" * 72

    print("\n" + line)
    print("ESTADO FINAL")
    print(line)
    if not alive:
        print("  EXTINCION: no queda nadie.")
        return
    s = pop.summary()
    print(f"  poblacion viva     {s['pop']}")
    print(f"  energia media      {s['energy']:.1f}")
    print(f"  categorias/agente  {s['categories']:.1f}")
    print(f"  vigilancia media   {s['vigilance']:.3f}   "
          f"(inicial {cfg.vigilance:.2f})")
    d = pop.deaths()
    print("  muertes            " +
          (", ".join(f"{k}={v}" for k, v in d.most_common()) or "ninguna"))

    last = records[-1]
    print(f"\n  prediccion (NMI categoria~afordancia)  {last.get('prediction', 0):.3f}")
    print(f"  alineamiento conceptual entre agentes  {last.get('alignment', 0):.3f}")
    print(f"  coherencia lexica                      {last.get('coherence', 0):.3f}")
    print(f"  sinonimia (formas por significado)     {last.get('lex_synonymy', 0):.2f}")
    print(f"  polisemia (significados por forma)     {last.get('lex_polysemy', 0):.2f}")

    # --- como nombra cada tribu el mundo ---
    print("\n" + line)
    print("LENGUAS EMERGENTES  —  como nombra cada tribu lo que el mundo contiene")
    print(line)
    tables = []
    covers = []
    for t in pop.tribes:
        ag = t.living()
        tables.append(naming_table(ag, world, rng, 6) if ag else {})
        covers.append(naming_coverage(ag, world, rng, 6) if ag else {})

    head = f"  {'tipo latente':<15}{'afordancia':<12}" + "".join(
        f"{'tribu ' + str(i + 1):<18}" for i in range(n_tribes))
    print(head)
    print("  " + "-" * (len(head) - 2))
    for k in world.kinds:
        cols = []
        for ti in range(n_tribes):
            counts = tables[ti].get(k.name)
            cov = covers[ti].get(k.name, 0.0)
            if not counts or cov < 0.20:
                cols.append(f"{'—':<18}")
            else:
                form, c = counts.most_common(1)[0]
                share = c / sum(counts.values())
                cols.append(f"{form + f' ({share:.0%})':<18}")
        print(f"  {k.name:<15}{k.affordance:<12}" + "".join(cols))
    print("\n  '—' = ese tipo no recibe nombre estable. No esta prohibido")
    print("      nombrarlo: sencillamente no compensa el coste de hablar.")

    if n_tribes > 1:
        print(f"\n  distancia lexica entre tribu 1 y 2: "
              f"{lexical_distance(pop.tribes[0].living(), pop.tribes[1].living(), world, rng):.2f}"
              f"   (1.00 = ninguna palabra en comun)")

    # --- gramatica (Fase 5) ---
    print("\n" + line)
    print("GRAMATICA  —  ¿tiene partes la señal?")
    print(line)
    print(f"  similitud topografica                  {last.get('topsim', 0):+.3f}")
    print("    (0 = señales sin parecido entre significados parecidos;")
    print("     alto = cambiar un atributo cambia un solo trozo)")
    print(f"  cobertura del espacio de significados  {last.get('coverage', 0):.3f}")
    print(f"  agentes con reglas de segmentacion     {last.get('lex_rules', 0):.2f}")
    print(f"  señales emitidas por composicion       {last.get('said_composed', 0):.2f}")
    print(f"  señales entendidas por composicion     {last.get('parsed_composed', 0):.2f}")
    print(f"  señales entendidas a medias            {last.get('parsed_partial', 0):.2f}")
    print(f"\n  combinaciones (cosa, lugar) nunca dichas antes: "
          f"{last.get('novel_rate', 0):.2f}")
    print(f"    aciertos en esas                     {last.get('novel_success', 0):.3f}")
    print(f"    aciertos en las ya conocidas         {last.get('known_success', 0):.3f}")

    ejemplo = next((a for a in alive if a.gram.has_rules()), None)
    if ejemplo is not None:
        cats = sorted(ejemplo.gram.cat.by_cat)[:3]
        places = sorted(ejemplo.gram.place.by_cat)[:3]
        print(f"\n  gramatica del agente {ejemplo.id}:")
        print("    morfos de COSA:  " + ", ".join(
            f"cat{c}={ejemplo.gram.cat.produce(c)!r}" for c in cats))
        print("    morfos de LUGAR: " + ", ".join(
            f"{world.place_names[p]}={ejemplo.gram.place.produce(p)!r}"
            for p in places if p < world.n_places))
        if cats and places:
            c, p = cats[0], places[0]
            comp = ejemplo.gram.cat.produce(c) + ejemplo.gram.place.produce(p)
            dice, modo = ejemplo.gram.express(c, p)
            print(f"    compondria {comp!r} para (cat{c}, {world.place_names[p]});"
                  f" de hecho dice {dice!r} ({modo})")
    else:
        print("\n  ningun agente ha inducido reglas: la lengua sigue siendo")
        print("  una lista de bloques opacos.")

    # --- metafora y cambio semantico (Fase 4) ---
    print("\n" + line)
    print("METAFORA  —  palabras estiradas hacia un concepto vecino")
    print(line)
    print(f"  fraccion del lexico nacida por extension: "
          f"{last.get('lex_metaphor', 0):.2f}"
          f"   (p_metaphor={cfg.p_metaphor:.2f})")
    shown = 0
    for a in alive:
        for (form, cat) in a.lex.born_extended:
            if a.lex.w.get((form, cat), 0) < cfg.lex_confidence:
                continue
            otras = [c for c in a.lex.by_form.get(form, ())
                     if c != cat and a.lex.w[(form, c)] >= cfg.lex_confidence]
            if not otras:
                continue
            v = a.value.get(cat)
            v0 = a.value.get(otras[0])
            print(f"  agente {a.id}: '{form}' cubre cat{otras[0]}"
                  f"{'' if v0 is None else f' (valor {v0:+.1f})'}"
                  f" y se estiro a cat{cat}"
                  f"{'' if v is None else f' (valor {v:+.1f})'}")
            shown += 1
            break
        if shown >= 5:
            break
    if not shown:
        print("  ninguna extension sobrevive con fuerza.")

    print("\n" + line)
    print("CAMBIO SEMANTICO  —  palabras que hoy se refieren a otra cosa")
    print(line)
    any_shift = False
    for ti, sl in enumerate(state["semantic"]):
        for form, g0, k0, g1, k1 in sl.shifts():
            print(f"  tribu {ti + 1}: '{form}'  gen {g0}: {k0}  ->  "
                  f"gen {g1}: {k1}")
            any_shift = True
    if not any_shift:
        print("  ninguna palabra ha cambiado de referente dominante.")

    # --- polisemia observada ---
    print("\n" + line)
    print("POLISEMIA OBSERVADA  (formas con mas de un significado fuerte)")
    print(line)
    found = 0
    for a in alive:
        for form, cats in a.lex.by_form.items():
            strong = [c for c in cats if a.lex.w[(form, c)] >= cfg.lex_confidence]
            if len(strong) > 1:
                desc = ", ".join(f"cat{c}(valor {a.value.get(c, 0):+.1f})"
                                 for c in strong)
                print(f"  agente {a.id}: '{form}' -> {desc}")
                found += 1
                break
        if found >= 6:
            break
    if not found:
        print("  ninguna. La inhibicion lateral por forma esta ganando.")

    # --- zipf ---
    print("\n" + line)
    print("FORMAS MAS EMITIDAS")
    print(line)
    for form, c in zipf_profile(alive, 10):
        print(f"  {form:<14} x{c}")


# ---------------------------------------------------------------------
# ablacion
# ---------------------------------------------------------------------

def outcome(records, generations):
    """Variable de resultado: media del ultimo tercio de la corrida."""
    if not records:
        return {"pop": 0.0, "energy": 0.0, "success": 0.0, "alarm_death": 1.0}
    cut = max(1, len(records) - max(1, generations // 3))
    tail = records[cut:]
    # si se extinguio antes de tiempo, las generaciones que faltan valen 0
    missing = generations - len(records)
    pops = [r["pop"] for r in tail] + [0.0] * missing
    return {
        "pop": mean(pops),
        "energy": mean([r["energy"] for r in tail]),
        "success": mean([r["success"] for r in tail]),
        "alarm_death": mean([r["alarm_death_rate"] for r in tail]),
    }


def ablation(cfg, n_tribes, generations, seeds, out=None):
    arms = {m: [] for m in MODES}
    all_records = []
    print(f"ABLACION  —  {seeds} semillas x {len(MODES)} brazos x "
          f"{generations} generaciones\n")
    for seed in range(1, seeds + 1):
        row = []
        for mode in MODES:
            recs, state = simulate(mode, seed, cfg, n_tribes, generations,
                                   metrics_every=0)
            o = outcome(recs, generations)
            arms[mode].append(o)
            all_records.extend(recs)
            row.append(f"{mode[:4]} pob={o['pop']:5.1f} exito={o['success']:.2f}")
        print(f"  semilla {seed:2d}  " + " | ".join(row))

    if out:
        _dump(out, cfg, all_records)

    rng = random.Random(4242)
    print("\n" + "=" * 72)
    print("RESULTADO")
    print("=" * 72)
    for key, label, better in [("pop", "poblacion sostenida", "mas"),
                               ("energy", "energia media", "mas"),
                               ("success", "decisiones acertadas", "mas"),
                               ("alarm_death", "muertes por depredador", "menos")]:
        print(f"\n  {label}  (mejor = {better})")
        for mode in MODES:
            xs = [o[key] for o in arms[mode]]
            print(f"    {mode:<9} {mean(xs):8.3f}  ± {stdev(xs):.3f}")
        lang = [o[key] for o in arms[MODE_LANGUAGE]]
        for ctrl in (MODE_MUTE, MODE_NOISE):
            ys = [o[key] for o in arms[ctrl]]
            obs, lo, hi = bootstrap_diff(lang, ys, rng, 4000)
            d = cliffs_delta(lang, ys)
            sig = "SI" if (lo > 0 or hi < 0) else "no"
            print(f"    language - {ctrl:<6} = {obs:+7.3f}  "
                  f"IC95[{lo:+.3f}, {hi:+.3f}]  delta={d:+.2f}  "
                  f"¿distinto de 0? {sig}")

    print("\n  El brazo 'noise' emite señales igual de frecuentes pero sin")
    print("  informacion. Separa SEÑALAR de INFORMAR: si language solo")
    print("  ganara a mute, podria ser un efecto del ruido y no del sentido.")
    print("\n  Nota: en 'mute' nadie paga speak_cost, asi que el brazo de")
    print("  control tiene una pequeña ventaja energetica. La comparacion")
    print("  es conservadora a proposito.")


# ---------------------------------------------------------------------
# Fase 4: ¿la metafora se gana su sitio?
# ---------------------------------------------------------------------

def metaphor_experiment(cfg, n_tribes, generations, seeds, levels):
    """Mismo mundo, misma semilla; solo cambia si se pueden estirar palabras.

    Estirar reutiliza algo que la tribu ya entiende (barato de aprender)
    pero mete ambiguedad (caro de usar). Cual gana no se puede razonar
    desde el sillon: hay que medirlo.
    """
    print(f"METAFORA  —  {seeds} semillas x {len(levels)} niveles x "
          f"{generations} generaciones\n")
    arms = {}
    for p in levels:
        rows = []
        for seed in range(1, seeds + 1):
            c = Config(**cfg.to_dict())
            c.p_metaphor = p
            recs, state = simulate(MODE_LANGUAGE, seed, c, n_tribes,
                                   generations, metrics_every=5)
            o = outcome(recs, generations)
            tail = [r for r in recs if "coherence" in r][-3:]
            shifts = sum(len(sl.shifts()) for sl in state["semantic"])
            rows.append({
                "pop": o["pop"], "success": o["success"],
                "coherence": mean([r["coherence"] for r in tail]),
                "polysemy": mean([r["lex_polysemy"] for r in tail]),
                "share": mean([r["lex_metaphor"] for r in tail]),
                "shifts": float(shifts),
            })
        arms[p] = rows
        print(f"  p_metaphor={p:.2f}  pob={mean([r['pop'] for r in rows]):5.1f}  "
              f"exito={mean([r['success'] for r in rows]):.3f}  "
              f"coher={mean([r['coherence'] for r in rows]):.3f}  "
              f"polisemia={mean([r['polysemy'] for r in rows]):.2f}  "
              f"lexico_metaforico={mean([r['share'] for r in rows]):.2f}  "
              f"derivas={mean([r['shifts'] for r in rows]):.1f}")

    base = min(levels)
    rng = random.Random(4243)
    print("\n" + "=" * 72)
    print(f"CONTRA p_metaphor={base:.2f} (sin metafora)")
    print("=" * 72)
    for key, label in [("pop", "poblacion"), ("success", "aciertos"),
                       ("coherence", "coherencia"), ("polysemy", "polisemia")]:
        print(f"\n  {label}")
        for p in levels:
            if p == base:
                continue
            xs = [r[key] for r in arms[p]]
            ys = [r[key] for r in arms[base]]
            obs, lo, hi = bootstrap_diff(xs, ys, rng, 4000)
            sig = "SI" if (lo > 0 or hi < 0) else "no"
            print(f"    p={p:.2f} - p={base:.2f} = {obs:+7.3f}  "
                  f"IC95[{lo:+.3f}, {hi:+.3f}]  "
                  f"delta={cliffs_delta(xs, ys):+.2f}  ¿distinto? {sig}")


def bottleneck_experiment(cfg, n_tribes, generations, seeds, capacities):
    """Fase 5: ¿aprieta el cuello de botella a favor de la composicion?

    La prediccion de Kirby: cuanto menos puede memorizar un aprendiz, mas
    composicional se vuelve la lengua, porque una lista de bloques opacos
    no se puede completar por generalizacion y una gramatica si.

    El mando es `hol_capacity`: cuantas señales ENTERAS caben en memoria.
    Los morfos inducidos no ocupan ese cupo, y esa asimetria es toda la
    presion. Nada mas cambia — ni la economia, ni la demografia, ni el
    mundo — asi que la comparacion es limpia.

    (La primera version usaba la esperanza de vida como mando. No servia:
    casi nadie llega a morir de viejo, se mueren antes de hambre o de
    depredador, asi que `max_age` apenas alteraba la muestra que oye un
    aprendiz. Era un experimento sin poder para detectar nada.)

    Es una prediccion que puede fallar: si la composicionalidad no sube al
    apretar, el mecanismo no es el que decimos que es.
    """
    print(f"CUELLO DE BOTELLA  —  {seeds} semillas x {len(capacities)} "
          f"capacidades de memoria x {generations} generaciones\n")
    arms = {}
    for cap in capacities:
        rows = []
        for seed in range(1, seeds + 1):
            c = Config(**cfg.to_dict())
            c.hol_capacity = cap
            recs, _ = simulate(MODE_LANGUAGE, seed, c, n_tribes, generations,
                               metrics_every=10)
            tail = [r for r in recs if "topsim" in r][-3:]
            span = recs[-25:]
            rows.append({
                "topsim": mean([r["topsim"] for r in tail]),
                "coverage": mean([r["coverage"] for r in tail]),
                "rules": mean([r["lex_rules"] for r in tail]),
                "composed": mean([r["said_composed"] for r in span]),
                "novel": mean([r["novel_rate"] for r in span]),
                "novel_ok": mean([r["novel_success"] for r in span]),
                "known_ok": mean([r["known_success"] for r in span]),
                "pop": mean([r["pop"] for r in span]),
            })
        arms[cap] = rows
        etiq = "inf" if cap == 0 else str(cap)
        print(f"  memoria={etiq:>4}  topsim={mean([r['topsim'] for r in rows]):+.3f}  "
              f"reglas={mean([r['rules'] for r in rows]):.2f}  "
              f"compuestas={mean([r['composed'] for r in rows]):.2f}  "
              f"cobertura={mean([r['coverage'] for r in rows]):.2f}  "
              f"nuevas={mean([r['novel'] for r in rows]):.2f}  "
              f"pob={mean([r['pop'] for r in rows]):5.1f}")

    base = 0 if 0 in capacities else max(capacities)
    rng = random.Random(4244)
    print("\n" + "=" * 72)
    print(f"CONTRA memoria={'inf' if base == 0 else base} (el cuello mas flojo)")
    print("=" * 72)
    for key, label in [("topsim", "similitud topografica"),
                       ("composed", "señales compuestas"),
                       ("coverage", "cobertura de significados")]:
        print(f"\n  {label}")
        for cap in capacities:
            if cap == base:
                continue
            xs = [r[key] for r in arms[cap]]
            ys = [r[key] for r in arms[base]]
            obs, lo, hi = bootstrap_diff(xs, ys, rng, 4000)
            sig = "SI" if (lo > 0 or hi < 0) else "no"
            print(f"    memoria={cap:>4} - {'inf' if base == 0 else base} = "
                  f"{obs:+7.3f}  IC95[{lo:+.3f}, {hi:+.3f}]  "
                  f"delta={cliffs_delta(xs, ys):+.2f}  ¿distinto? {sig}")

    print("\n  Y lo que de verdad importa: ¿sirve de algo componer?")
    for cap in capacities:
        rows = arms[cap]
        print(f"    memoria={cap:>4}  aciertos en combinacion NUEVA "
              f"{mean([r['novel_ok'] for r in rows]):.3f}   "
              f"en combinacion ya dicha {mean([r['known_ok'] for r in rows]):.3f}")


def culture_experiment(cfg, n_tribes, generations, seeds, objetivo=None):
    """¿Sobrevive un saber a quien lo adquirio?

    Se corre lo mismo con lengua y sin ella, y despues se mata a todo el
    que haya sufrido el tipo objetivo en persona. El brazo mudo no es un
    adorno: si la tribu muda tambien evita el peligro tras la purga,
    entonces lo que se esta midiendo no es cultura.
    """
    print(f"CULTURA ACUMULADA  —  {seeds} semillas x 2 brazos x "
          f"{generations} generaciones\n")
    resumen = {MODE_LANGUAGE: [], MODE_MUTE: []}
    for modo in (MODE_LANGUAGE, MODE_MUTE):
        for seed in range(1, seeds + 1):
            recs, st = simulate(modo, seed, cfg, n_tribes, generations,
                                metrics_every=0)
            pop, world, rng = st["pop"], st["world"], st["rng"]
            if pop.extinct():
                continue
            # los mas peligrosos del mundo: donde el saber vale mas
            peligros = sorted([k for k in world.kinds if k.payoff < 0],
                              key=lambda k: k.payoff)
            if not peligros:
                raise SystemExit("este mundo no tiene nada peligroso")
            blanco = next((k for k in peligros if k.name == objetivo),
                          peligros[0])
            if seed == 1:
                informe_A(prueba_A(pop, world, rng, peligros[:3]), modo)
            r = prueba_B(pop, world, rng, blanco)
            resumen[modo].append(r)
            ev = ("—" if r["evita_despues"] is None
                  else f"{r['evita_despues']:.2f}")
            print(f"  {modo[:4]} semilla {seed:2d}  purgados={r['muertos']:3d}"
                  f"  sobreviven={r['vivos']:3d}  evitan_despues={ev}"
                  f"  de_oidas={r.get('oidas_despues', 0)}", flush=True)
            if seed == 1:
                informe_B(r, modo)

    print("\n" + "=" * 72)
    print("RESULTADO")
    print("=" * 72)
    rng = random.Random(9091)
    for modo in (MODE_LANGUAGE, MODE_MUTE):
        rs = [r for r in resumen[modo] if r["vivos"] > 0]
        if not rs:
            print(f"  {modo:<9} sin supervivientes en ninguna semilla")
            continue
        print(f"  {modo:<9} evitacion antes {mean([r['evita_antes'] for r in rs]):.3f}"
              f"   DESPUES de la purga {mean([r['evita_despues'] for r in rs]):.3f}"
              f"   (n={len(rs)})")
    a = [r["evita_despues"] for r in resumen[MODE_LANGUAGE] if r["vivos"] > 0]
    b = [r["evita_despues"] for r in resumen[MODE_MUTE] if r["vivos"] > 0]
    if a and b:
        obs, lo, hi = bootstrap_diff(a, b, rng, 4000)
        sig = "SI" if (lo > 0 or hi < 0) else "no"
        print(f"\n  language - mute (tras la purga) = {obs:+.3f}  "
              f"IC95[{lo:+.3f}, {hi:+.3f}]  delta={cliffs_delta(a, b):+.2f}  "
              f"¿distinto de 0? {sig}")
        print("\n  Si esa diferencia es positiva y significativa, un saber")
        print("  sobrevivio a todos los que lo adquirieron. Si no lo es, no.")


def _dump(path, cfg, records):
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"_config": cfg.to_dict()}, ensure_ascii=False) + "\n")
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n  datos -> {path}")


def _add_config_args(ap, cfg):
    ap.add_argument("--tribe-size", type=int, default=cfg.tribe_size)
    ap.add_argument("--max-pop", type=int, default=cfg.max_pop)
    ap.add_argument("--vigilance", type=float, default=cfg.vigilance)
    ap.add_argument("--contact", type=int, default=cfg.contact)
    ap.add_argument("--alarms", type=float, default=cfg.alarms_per_agent,
                    help="encuentros con depredador por agente y generacion")
    ap.add_argument("--world", default=cfg.world)
    ap.add_argument("--episodes", type=int, default=cfg.episodes_per_gen)


def _apply(cfg, args):
    cfg.tribe_size = args.tribe_size
    cfg.max_pop = args.max_pop
    cfg.vigilance = args.vigilance
    cfg.contact = args.contact
    cfg.alarms_per_agent = args.alarms
    cfg.world = args.world
    cfg.episodes_per_gen = args.episodes
    return cfg


def main(argv=None):
    _console_setup()
    cfg = Config()
    ap = argparse.ArgumentParser(prog="emergence.run")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sim", help="una corrida con informe legible")
    p.add_argument("--mode", choices=MODES, default=MODE_LANGUAGE)
    p.add_argument("--tribes", type=int, default=2)
    p.add_argument("--generations", type=int, default=80)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--metrics-every", type=int, default=5)
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--out", default=None, help="volcado JSONL")
    _add_config_args(p, cfg)

    m = sub.add_parser("metaphor", help="Fase 4: ¿la metafora se gana su sitio?")
    m.add_argument("--tribes", type=int, default=2)
    m.add_argument("--generations", type=int, default=100)
    m.add_argument("--seeds", type=int, default=8)
    m.add_argument("--levels", type=float, nargs="+",
                   default=[0.0, 0.35, 0.7])
    _add_config_args(m, cfg)

    b = sub.add_parser("bottleneck",
                       help="Fase 5: ¿aprieta el cuello a favor de componer?")
    b.add_argument("--tribes", type=int, default=2)
    b.add_argument("--generations", type=int, default=120)
    b.add_argument("--seeds", type=int, default=8)
    b.add_argument("--capacities", type=int, nargs="+", default=[12, 25, 60, 0],
                   help="señales enteras que caben en memoria (0 = infinita)")
    _add_config_args(b, cfg)

    lv = sub.add_parser("live", help="correr indefinidamente y emitir en vivo")
    lv.add_argument("--port", type=int, default=8080)
    lv.add_argument("--tribes", type=int, default=2)
    lv.add_argument("--seed", type=int, default=3)
    lv.add_argument("--eps", type=int, default=30,
                    help="episodios por segundo emitidos a la vista de mundo")
    lv.add_argument("--snap-every", type=int, default=10)
    _add_config_args(lv, cfg)

    au = sub.add_parser("audit", help="la carta de la lengua, N semillas")
    au.add_argument("--tribes", type=int, default=2)
    au.add_argument("--generations", type=int, default=55)
    au.add_argument("--seeds", type=int, default=12)
    _add_config_args(au, cfg)

    ex = sub.add_parser("export", help="volcar una corrida para el visor web")
    ex.add_argument("--out", default="client/public/data")
    ex.add_argument("--mode", choices=MODES, default=MODE_LANGUAGE)
    ex.add_argument("--tribes", type=int, default=2)
    ex.add_argument("--generations", type=int, default=60)
    ex.add_argument("--seed", type=int, default=3)
    ex.add_argument("--every", type=int, default=1,
                    help="guardar 1 de cada N episodios")
    ex.add_argument("--snap-every", type=int, default=5)
    _add_config_args(ex, cfg)

    so = sub.add_parser("social",
                        help="¿rompe la amplificacion de mayorias el techo?")
    so.add_argument("--tribes", type=int, default=2)
    so.add_argument("--generations", type=int, default=50)
    so.add_argument("--seeds", type=int, default=10)
    so.add_argument("--levels", type=float, nargs="+", default=[0.0, 0.4, 0.8])
    _add_config_args(so, cfg)

    k = sub.add_parser("culture",
                       help="¿sobrevive un saber a quien lo adquirio?")
    k.add_argument("--tribes", type=int, default=2)
    k.add_argument("--generations", type=int, default=70)
    k.add_argument("--seeds", type=int, default=8)
    k.add_argument("--target", default=None, help="tipo latente objetivo")
    _add_config_args(k, cfg)

    a = sub.add_parser("ablation", help="el experimento")
    a.add_argument("--tribes", type=int, default=2)
    a.add_argument("--generations", type=int, default=80)
    a.add_argument("--seeds", type=int, default=10)
    a.add_argument("--out", default=None)
    _add_config_args(a, cfg)

    args = ap.parse_args(argv)
    cfg = _apply(cfg, args)

    if args.cmd == "sim":
        print(f"modo={args.mode} tribus={args.tribes} "
              f"generaciones={args.generations} semilla={args.seed}\n")
        recs, state = simulate(args.mode, args.seed, cfg, args.tribes,
                               args.generations, args.metrics_every,
                               verbose=not args.quiet)
        report(recs, state, cfg, args.tribes)
        if args.out:
            _dump(args.out, cfg, recs)
    elif args.cmd == "live":
        from .server import servir
        servir(cfg, args.tribes, args.seed, args.port, args.eps,
               args.snap_every)
    elif args.cmd == "audit":
        from .audit import audit_many
        audit_many(cfg, args.tribes, args.generations, args.seeds)
    elif args.cmd == "export":
        from .export import export
        export(cfg, args.mode, args.seed, args.tribes, args.generations,
               args.out, args.every, args.snap_every)
    elif args.cmd == "social":
        from .social import run as social_run
        social_run(cfg, args.tribes, args.generations, args.seeds,
                   sorted(args.levels))
    elif args.cmd == "culture":
        culture_experiment(cfg, args.tribes, args.generations, args.seeds,
                           args.target)
    elif args.cmd == "bottleneck":
        bottleneck_experiment(cfg, args.tribes, args.generations, args.seeds,
                              args.capacities)
    elif args.cmd == "metaphor":
        metaphor_experiment(cfg, args.tribes, args.generations, args.seeds,
                            sorted(args.levels))
    else:
        ablation(cfg, args.tribes, args.generations, args.seeds, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
