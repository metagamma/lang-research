#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lectura de los JSONL que produce run.py.

Sin dependencias externas: dibuja en el terminal. Si algun dia hace falta
matplotlib, los datos ya estan en un formato que cualquier cosa puede leer.

    python -m emergence.analyze data/run.jsonl
    python -m emergence.analyze data/ablation.jsonl --metric pop
"""

import argparse
import json
from collections import defaultdict

from .console import bar, setup

SERIES = [
    ("pop", "poblacion"),
    ("energy", "energia media"),
    ("success", "decisiones acertadas"),
    ("signal_rate", "episodios con señal"),
    ("understood_rate", "señales entendidas"),
    ("alarm_death_rate", "muertes por alarma"),
    ("coherence", "coherencia lexica"),
    ("topsim", "similitud topografica (composicionalidad)"),
    ("said_composed", "señales emitidas por composicion"),
    ("parsed_partial", "señales entendidas a medias"),
    ("novel_rate", "combinaciones nunca dichas antes"),
    ("novel_success", "aciertos en combinacion nueva"),
    ("coverage", "cobertura del espacio de significados"),
    ("prediction", "prediccion (cat~afordancia)"),
    ("alignment", "alineamiento conceptual"),
    ("categories", "categorias por agente"),
    ("lex_polysemy", "polisemia"),
    ("lex_synonymy", "sinonimia"),
]


def load(path):
    cfg, rows = None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            if "_config" in d:
                cfg = d["_config"]
            else:
                rows.append(d)
    return cfg, rows


def spark(values, width=56):
    vals = [v for v in values if v is not None]
    if not vals:
        return "(sin datos)"
    lo, hi = min(vals), max(vals)
    # remuestreo a `width` cubos
    out = []
    n = len(vals)
    for i in range(width):
        a, b = int(i * n / width), max(int(i * n / width) + 1, int((i + 1) * n / width))
        chunk = vals[a:b] or [vals[min(a, n - 1)]]
        out.append(bar(sum(chunk) / len(chunk), lo, hi))
    return "|" + "".join(out) + f"|  [{lo:.2f} -> {hi:.2f}]"


def curve(rows, key):
    """Media por generacion sobre todas las semillas del mismo modo."""
    acc = defaultdict(list)
    for r in rows:
        v = r.get(key)
        if v is not None:
            acc[r["gen"]].append(v)
    return [sum(acc[g]) / len(acc[g]) for g in sorted(acc)]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="emergence.analyze")
    ap.add_argument("path")
    ap.add_argument("--metric", default=None,
                    help="una sola metrica en vez de todas")
    args = ap.parse_args(argv)
    setup()

    cfg, rows = load(args.path)
    modes = sorted({r["mode"] for r in rows})
    seeds = sorted({r["seed"] for r in rows})
    print(f"{args.path}: {len(rows)} filas, modos={modes}, {len(seeds)} semillas\n")

    series = [s for s in SERIES if args.metric in (None, s[0])]
    if not series:
        print(f"  '{args.metric}' no es una metrica conocida. Disponibles: "
              + ", ".join(k for k, _ in SERIES))
        return 1
    drawn = 0
    for key, label in series:
        printed = False
        for mode in modes:
            sub = [r for r in rows if r["mode"] == mode]
            c = curve(sub, key)
            if not c:
                continue
            if not printed:
                print(f"  {label}")
                printed = True
            print(f"    {mode:<9} {spark(c)}")
        if printed:
            drawn += 1
            print()

    if not drawn:
        print("  Este fichero no trae esas metricas. Las caras (coherencia,")
        print("  prediccion, alineamiento, polisemia) solo se calculan con")
        print("  `sim --out`; `ablation` corre con metrics_every=0 por coste.")

    if cfg:
        print("  parametros clave: " + ", ".join(
            f"{k}={cfg[k]}" for k in
            ("metabolic_cost", "episodes_per_gen", "max_pop", "vigilance",
             "lex_inhib_form", "lex_inhib_meaning") if k in cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
