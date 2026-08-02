#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exportador para el visor web.

Escribe los tres ficheros del contrato de datos de `client/SPEC.md`. El
cliente no sabe nada de Python: lee estos y ya.

    world.json       el mundo tal cual (sentidos, lugares, tipos)
    frames.jsonl     un episodio por linea  -> vista de mundo
    snapshots.jsonl  el estado cada N generaciones -> vista de laboratorio

POR QUE DOS FICHEROS Y NO UNO
-----------------------------
Los frames dan el MOVIMIENTO y las instantaneas dan el ESTADO. Hacen falta
los dos porque el visor tiene que poder saltar a la generacion 40 sin
haber reproducido las 39 anteriores: reconstruir el estado acumulando
cuarenta mil episodios en el navegador seria absurdo.

SOBRE EL TAMAÑO
---------------
Una corrida de 80 generaciones son ~64.000 episodios. Con claves de una o
dos letras y sin espacios, cada linea ronda los 110 bytes: unos 7 MB. Es
mucho para cargarlo de golpe en el navegador, asi que `--every` permite
quedarse con una fraccion de los episodios. La vista de mundo no necesita
verlos todos — necesita ver lo que pasa.

Las claves van abreviadas a proposito. No es microoptimizacion gratuita:
es la diferencia entre 7 MB y 20 MB, y el cliente los lee una vez.
"""

import json
import os

from .metrics import lexical_coherence, naming_table, topographic_similarity


class Recorder:
    """Acumula episodios y los escribe como JSONL.

    Se le pasa a la simulacion y esta le va entregando cada episodio. No
    interviene en nada: solo mira y apunta.
    """

    def __init__(self, path, every=1):
        self.fh = open(path, "w", encoding="utf-8")
        self.every = max(1, every)
        self.n = 0
        self.written = 0

    def frame(self, gen, tribe, sp, li, rec):
        self.n += 1
        if self.n % self.every:
            return
        d = {"g": gen, "t": tribe, "sp": sp, "li": li,
             "k": rec.get("kind"), "pl": rec.get("place")}
        if rec.get("signal"):
            d["sig"] = rec["signal"]
            d["mode"] = rec.get("said")
        if rec.get("understood"):
            d["und"] = 1
        if rec.get("acted"):
            d["act"] = 1
        if rec.get("chose_well"):
            d["ok"] = 1
        if rec.get("past"):
            d["past"] = 1
        if rec.get("descrito"):
            d["desc"] = 1
        if rec.get("type") == "alarm":
            d["alarm"] = 1
        self.fh.write(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
        self.fh.write("\n")
        self.written += 1

    def close(self):
        self.fh.close()


def _variantes(agents, world, rng, per_kind=6):
    """Reparto de palabras rivales por tipo.

    Va en las instantaneas porque es lo que hace visible el fallo de
    ruptura de simetria — dos palabras al 0.46 para la misma cosa. Una
    tabla que solo enseñe la mayoritaria oculta justo el fenomeno.
    """
    out = {}
    for kind, counts in naming_table(agents, world, rng, per_kind).items():
        tot = sum(counts.values())
        if tot:
            out[kind] = [[f, round(n / tot, 3)] for f, n in counts.most_common(6)]
    return out


def snapshot(gen, pop, world, rng, rec):
    """Estado de la poblacion en esta generacion."""
    # Las claves del contrato van sin acentos ni eñes a proposito. Un
    # fichero de datos que cruza lenguajes no es sitio para eso.
    tribus = []
    for t in pop.tribes:
        vivos = t.living()
        if not vivos:
            tribus.append(None)
            continue
        tribus.append({
            "n": len(vivos),
            "coherencia": round(lexical_coherence(vivos, world, rng, 6), 4),
            "nombres": _variantes(vivos, world, rng),
            "agentes": [{"id": a.id, "e": round(a.energy, 1), "edad": a.age,
                         "cats": len(a.concepts), "lex": a.gram.size()}
                        for a in vivos],
        })
    return {
        "g": gen,
        "pop": rec.get("pop"),
        "exito": round(rec.get("success", 0.0), 4),
        "coherencia": round(rec.get("coherence", 0.0), 4),
        "topsim": round(rec.get("topsim", 0.0), 4),
        "senal": round(rec.get("signal_rate", 0.0), 4),   # sin acento: es una clave de datos
        "tribus": tribus,
    }


def export(cfg, mode, seed, n_tribes, generations, outdir,
           every=1, snap_every=5):
    """Corre una simulacion y escribe los tres ficheros."""
    from .run import PROBE_SEED, simulate
    from .fastrand import FastRandom
    from .world import load_spec

    os.makedirs(outdir, exist_ok=True)

    # 1. el mundo, tal cual
    spec_path = os.path.join(outdir, "world.json")
    origen = cfg.world if os.path.isfile(cfg.world) else None
    if origen is None:
        from .world import WORLDS_DIR
        origen = os.path.join(WORLDS_DIR, f"{cfg.world}.json")
    with open(origen, encoding="utf-8") as fh:
        datos = json.load(fh)
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1)

    # 2. los episodios
    rec = Recorder(os.path.join(outdir, "frames.jsonl"), every)
    snaps = []

    def al_terminar_generacion(gen, pop, world, rng_metric, fila):
        if gen % snap_every == 0 or gen == 1 or gen == generations:
            snaps.append(snapshot(gen, pop, world, rng_metric, fila))

    records, st = simulate(mode, seed, cfg, n_tribes, generations,
                           metrics_every=snap_every,
                           recorder=rec, on_generation=al_terminar_generacion)
    rec.close()

    with open(os.path.join(outdir, "snapshots.jsonl"), "w",
              encoding="utf-8") as fh:
        for s in snaps:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")

    tam = {f: os.path.getsize(os.path.join(outdir, f)) / 1e6
           for f in ("world.json", "frames.jsonl", "snapshots.jsonl")}
    print(f"  {outdir}")
    print(f"    world.json       {tam['world.json']:6.2f} MB")
    print(f"    frames.jsonl     {tam['frames.jsonl']:6.2f} MB  "
          f"({rec.written} de {rec.n} episodios, 1 de cada {every})")
    print(f"    snapshots.jsonl  {tam['snapshots.jsonl']:6.2f} MB  "
          f"({len(snaps)} instantaneas)")
    if tam["frames.jsonl"] > 8:
        print("    AVISO: pesado para el navegador. Sube --every.")
    return records, st
