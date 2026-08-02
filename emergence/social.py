#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Experimento — ¿rompe la amplificacion de mayorias el techo de coherencia?

El diagnostico mostro que el 0.53 no era un proceso a medio camino sino un
EQUILIBRIO: ~3 palabras vivas por cosa, repartidas y a veces empatadas
exactamente (0.46/0.46). Las tres causas que yo sospechaba quedaron
refutadas por los datos — cada agente es consistente consigo mismo (0.957),
adopta el 90% de lo que dice, y la divergencia conceptual solo aporta 0.036.

Lo que faltaba era ROMPER LA SIMETRIA. La inhibicion lateral es local: cada
uno refuerza lo que oye y debilita el resto en su cabeza, asi que en una
banda de ocho con encuentros al azar nadie llega a ver cual es la mayoria y
un empate 3-3 no se deshace nunca.

`social_exp` hace que al hablar pese CUANTA GENTE DISTINTA usa cada forma,
no cuantas veces se ha oido. Una ventaja 3-2 pasa a ser detectable.

LO QUE DE VERDAD SE MIDE AQUI
-----------------------------
Subir la coherencia no es el objetivo; es el medio. Cuatro mecanismos
estan construidos y funcionando al ralenti porque colgaban de ese techo:
composicionalidad, comprension de oraciones encajadas, descripciones y
vocabulario atributivo.

Si la coherencia sube y esos cuatro no se mueven, el techo no era la
coherencia y me habre vuelto a equivocar de diagnostico. Por eso se miden
los cuatro, no solo el numero que estamos empujando.
"""

import itertools
import random

from .attributes import restricciones
from .config import Config
from .episodes import MODE_LANGUAGE
from .metrics import bootstrap_diff, cliffs_delta, mean, stdev


def _solape_adjetivos(pop, world, rng):
    """Jaccard medio entre los inventarios atributivos de la tribu."""
    inv = {}
    for t in pop.tribes:
        for a in t.living():
            inv[a.id] = set(restricciones(a.gram, world.spread(rng)))
    pares = [len(inv[x] & inv[y]) / max(1, len(inv[x] | inv[y]))
             for x, y in itertools.combinations(inv, 2)
             if inv[x] or inv[y]]
    return mean(pares) if pares else 0.0


def run(cfg, n_tribes, generations, seeds, niveles):
    from .run import simulate

    print(f"AMPLIFICACION DE MAYORIAS  —  {seeds} semillas x "
          f"{len(niveles)} niveles x {generations} generaciones\n")
    arms = {}
    for e in niveles:
        filas = []
        for seed in range(1, seeds + 1):
            c = Config(**cfg.to_dict())
            c.social_exp = e
            recs, st = simulate(MODE_LANGUAGE, seed, c, n_tribes,
                                generations, metrics_every=generations // 2)
            if st["pop"].extinct():
                continue
            cola = recs[-12:]
            fin = recs[-1]
            filas.append({
                "coherencia": fin.get("coherence", 0.0),
                "exito": mean([r["success"] for r in cola]),
                "topsim": fin.get("topsim", 0.0),
                "encajes": mean([r["quote_understood"] for r in cola]),
                "descripciones": mean([r["desc_understood"] for r in cola]),
                "adjetivos": _solape_adjetivos(st["pop"], st["world"],
                                               st["rng"]),
                "pob": fin["pop"],
            })
            print(f"  e={e:<4} semilla {seed:2d}  "
                  f"coher={filas[-1]['coherencia']:.3f} "
                  f"exito={filas[-1]['exito']:.3f} "
                  f"topsim={filas[-1]['topsim']:+.3f} "
                  f"encajes={filas[-1]['encajes']:.2f} "
                  f"adj={filas[-1]['adjetivos']:.3f}", flush=True)
        arms[e] = filas

    base = min(niveles)
    rng = random.Random(7331)
    print("\n" + "=" * 74)
    print(f"RESULTADO   (contra social_exp={base}, que es el modelo actual)")
    print("=" * 74)
    claves = [("coherencia", "coherencia lexica"),
              ("exito", "decisiones acertadas"),
              ("topsim", "composicionalidad"),
              ("encajes", "comprension de encajes"),
              ("descripciones", "comprension de descripciones"),
              ("adjetivos", "solapamiento adjetival")]
    for k, etiqueta in claves:
        print(f"\n  {etiqueta}")
        for e in niveles:
            xs = [f[k] for f in arms.get(e, [])]
            if xs:
                print(f"    e={e:<5} {mean(xs):8.3f}  ± {stdev(xs):.3f}  (n={len(xs)})")
        ys = [f[k] for f in arms.get(base, [])]
        for e in niveles:
            if e == base or not arms.get(e) or not ys:
                continue
            xs = [f[k] for f in arms[e]]
            obs, lo, hi = bootstrap_diff(xs, ys, rng, 4000)
            sig = "SI" if (lo > 0 or hi < 0) else "no"
            print(f"    e={e} - e={base} = {obs:+7.3f}  "
                  f"IC95[{lo:+.3f}, {hi:+.3f}]  "
                  f"delta={cliffs_delta(xs, ys):+.2f}  ¿distinto? {sig}")

    print("\n  Lo que decide si el diagnostico era bueno no es la primera")
    print("  fila sino las cuatro ultimas: si la coherencia sube y los")
    print("  mecanismos que colgaban de ella no se mueven, el techo no era")
    print("  la coherencia.")
