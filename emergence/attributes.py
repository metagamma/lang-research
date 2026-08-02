#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sonda — ¿hay adjetivos latentes en la lengua que ya tenemos?

El objetivo final es que una descripcion pueda ENTREGAR un concepto, no
solo decir cuanto vale uno que el oyente ya tiene. Para eso hacen falta
palabras que nombren PROPIEDADES y no cosas, con las que construir un
prototipo nuevo por interseccion de restricciones.

Antes de montar toda esa maquinaria conviene saber si el terreno ya esta
preparado. Esta sonda no cambia nada del modelo: solo mira.

LA IDEA
-------
Para cada morfo se lleva la nube de vectores sensoriales de las cosas con
las que se co-observo. La FORMA de esa nube dice que clase de palabra es,
sin que nadie declare categorias gramaticales:

    estrecha en TODAS las dimensiones   -> nombra una cosa      (sustantivo)
    estrecha en UNA, ancha en el resto  -> nombra una propiedad (adjetivo)
    ancha en todas                      -> no nombra cosas      (lugar, accion)

Es el mismo estadistico para los tres casos y sale de los datos.

QUE ESPERO ENCONTRAR, dicho antes de mirar
------------------------------------------
Probablemente NO haya adjetivos: en el modelo actual un morfo denota una
categoria (nube estrecha) o un lugar/accion/tiempo (nube ancha), y nada
empuja a que exista algo intermedio. Si es asi, la conclusion es que hay
que CREAR la presion que los haga aparecer antes de construir nada.

Con una excepcion interesante: la metafora de la Fase 4 estira una
palabra hacia un concepto vecino. Un morfo estirado cubre dos prototipos
proximos — estrecho donde coinciden, ancho donde difieren. Eso es
exactamente un proto-adjetivo, y si aparece, habra salido solo.
"""

import math

import numpy as np


class Cloud:
    """Media y varianza incrementales (Welford) de los rasgos vistos."""

    __slots__ = ("n", "mean", "m2")

    def __init__(self, dim):
        self.n = 0
        self.mean = np.zeros(dim)
        self.m2 = np.zeros(dim)

    def add(self, x):
        self.n += 1
        d = x - self.mean
        self.mean += d / self.n
        self.m2 += d * (x - self.mean)

    def sd(self):
        if self.n < 2:
            return None
        return np.sqrt(self.m2 / (self.n - 1))


def record(gram, s, percept):
    """Apunta este percepto en la nube de cada morfo reconocible en `s`.

    Se atribuye a las piezas que el oyente reconoce, que es lo unico que
    el podria usar. No se le da la segmentacion correcta.
    """
    if percept is None:
        return
    hits = gram._scan(s)
    dim = len(percept)
    for voc_i, por_pos in enumerate(hits):
        for pos, entradas in por_pos.items():
            for (fin, _v, _w) in entradas:
                pieza = s[pos:fin]
                c = gram.clouds.get(pieza)
                if c is None:
                    c = gram.clouds[pieza] = Cloud(dim)
                c.add(percept)


# ---------------------------------------------------------------------

def world_spread(world, rng, per_kind=25):
    """Desviacion tipica por dimension de TODO lo que hay en el mundo.

    Es la vara con la que se decide si una nube es estrecha: estrecha
    respecto a la variedad que existe ahi fuera, no en absoluto.
    """
    xs = [world.make(k, 0, rng).features
          for k in world.kinds for _ in range(per_kind)]
    return np.std(np.stack(xs), axis=0)


def clasificar(sd, referencia, umbral=0.45, min_n=6):
    """(clase, dimensiones_estrechas) para una nube."""
    rel = sd / np.maximum(referencia, 1e-9)
    estrechas = int((rel < umbral).sum())
    total = len(rel)
    if estrechas >= total - 1:
        return "sustantivo", estrechas
    if estrechas == 0:
        return "sin anclaje", estrechas
    return "ATRIBUTIVO", estrechas


def profile(agents, world, rng, min_n=6):
    """Reparto de morfos por forma de su nube, sobre toda la poblacion."""
    ref = world_spread(world, rng)
    filas = []
    for a in agents:
        for pieza, c in a.gram.clouds.items():
            if c.n < min_n:
                continue
            sd = c.sd()
            if sd is None:
                continue
            clase, estrechas = clasificar(sd, ref)
            filas.append({"agente": a.id, "morfo": pieza, "n": c.n,
                          "clase": clase, "estrechas": estrechas,
                          "sd_rel": sd / np.maximum(ref, 1e-9)})
    return filas, ref


def report(filas, ref, world):
    from collections import Counter
    line = "=" * 74
    print("\n" + line)
    print("SONDA DE ATRIBUTOS  —  ¿hay adjetivos latentes?")
    print(line)
    if not filas:
        print("  sin morfos con nube suficiente")
        return Counter()
    tally = Counter(f["clase"] for f in filas)
    total = len(filas)
    print(f"  {total} morfos con nube observada "
          f"(>= 6 co-observaciones), sobre {len(set(f['agente'] for f in filas))} agentes\n")
    for clase, n in tally.most_common():
        print(f"    {clase:<14} {n:5d}  ({n/total:.1%})")

    print(f"\n  reparto por numero de dimensiones estrechas (de {len(ref)}):")
    hist = Counter(f["estrechas"] for f in filas)
    for k in sorted(hist):
        barra = "#" * min(50, hist[k])
        print(f"    {k:2d} dims  {hist[k]:5d}  {barra}")

    attrs = [f for f in filas if f["clase"] == "ATRIBUTIVO"]
    if attrs:
        print(f"\n  ejemplos de morfos ATRIBUTIVOS "
              f"(estrechos en pocas dimensiones):")
        nombres = [n for _, n in world.spec.senses]
        for f in sorted(attrs, key=lambda x: -x["n"])[:6]:
            cuales = [nombres[i] for i, v in enumerate(f["sd_rel"]) if v < 0.45]
            print(f"    '{f['morfo']}' (n={f['n']}) restringe: "
                  + ", ".join(cuales))
    else:
        print("\n  NINGUN morfo atributivo. La lengua actual solo tiene")
        print("  palabras-cosa y palabras-sin-anclaje-sensorial.")
    return tally


# ---------------------------------------------------------------------
# De sonda a capacidad
#
# A partir de aqui las nubes dejan de ser solo instrumentacion. Un agente
# que ha llevado la cuenta de con que cosas aparece cada palabra SABE que
# 'ii' acompaña a lo verde — no es informacion privilegiada, es lo que
# cualquier aprendiz acumula oyendo. Que nosotros lo usaramos primero
# para medir no lo convierte en trampa: lo unico que hacemos es dejar que
# el agente consulte su propia experiencia.
# ---------------------------------------------------------------------

def restricciones(gram, ref, min_n=20, umbral=0.45, max_dims=3):
    """morfo -> {dimension: valor} para los morfos ATRIBUTIVOS del agente.

    Solo los que restringen pocas dimensiones. Un morfo estrecho en todo
    nombra una cosa concreta y no sirve para describir; uno ancho en todo
    no dice nada del mundo sensible.
    """
    reales = set()
    for v in gram.voc:
        reales |= set(v.by_form)
    out = {}
    for pieza, c in gram.clouds.items():
        if pieza not in reales or c.n < min_n:
            continue
        sd = c.sd()
        if sd is None:
            continue
        rel = sd / np.maximum(ref, 1e-9)
        dims = [i for i, v in enumerate(rel) if v < umbral]
        if 1 <= len(dims) <= max_dims:
            out[pieza] = {d: float(c.mean[d]) for d in dims}
    return out


def describir(gram, prototipo, ref, n_piezas=3, min_n=20, refina=0.5):
    """Los morfos atributivos que mejor describen este prototipo.

    Se eligen por cercania en las dimensiones que cada uno restringe.

    SOBRE REPETIR DIMENSION. La primera version rechazaba cualquier morfo
    que tocara una dimension ya cubierta, razonando que «decir dos veces
    lo mismo no añade nada». Es cierto si los dos dicen lo mismo — pero
    medido resulto ser la condicion que mas descripciones mataba: 1.99
    candidatas descartadas por llamada frente a 0.70 del filtro de
    distancia, y el 16% de TODOS los casos eran «tenia una pieza y la
    segunda choco de dimension».

    Con 9 dimensiones y ~4 candidatas, lo que pasa casi siempre no es
    redundancia sino REFINAMIENTO: «lo verde» y «lo muy verde» tocan la
    misma dimension con valores distintos, y descartar el segundo no
    evitaba decir dos veces lo mismo, quitaba precision.

    Ahora se rechaza solo si el valor que aporta esta CERCA del ya
    cubierto (a menos de `refina` desviaciones). Si lo afina, entra.
    """
    cand = restricciones(gram, ref, min_n)
    if not cand:
        return [], {}
    puntuadas = []
    for pieza, cons in cand.items():
        err = sum(abs(prototipo[d] - v) / max(ref[d], 1e-9)
                  for d, v in cons.items()) / len(cons)
        puntuadas.append((err, pieza, cons))
    puntuadas.sort(key=lambda t: t[0])
    usadas, piezas, total = set(), [], {}
    for err, pieza, cons in puntuadas:
        if err > 1.0:
            continue
        aporta = any(d not in total
                     or abs(v - total[d]) / max(ref[d], 1e-9) > refina
                     for d, v in cons.items())
        if not aporta:
            continue
        piezas.append(pieza)
        for d, v in cons.items():
            total.setdefault(d, v)     # la primera fija; las demas afinan
        usadas |= set(cons)
        if len(piezas) >= n_piezas:
            break
    return piezas, total


def entender(gram, cadena, ref, min_n=20):
    """¿Es esta cadena una descripcion? Devuelve las restricciones o None.

    Se lee como descripcion solo si se parte ENTERA en morfos atributivos
    y hay al menos dos. Asi no hace falta ninguna marca especial que
    aprender: la estructura misma delata que no es un nombre.
    """
    cand = restricciones(gram, ref, min_n)
    if not cand:
        return None
    n = len(cadena)

    def rec(i, usados):
        if i == n:
            return usados if len(usados) >= 2 else None
        for j in range(i + 2, n + 1):
            pieza = cadena[i:j]
            if pieza not in cand:
                continue
            r = rec(j, usados + [pieza])
            if r is not None:
                return r
        return None

    piezas = rec(0, [])
    if piezas is None:
        return None
    cons = {}
    for pieza in piezas:
        cons.update(cand[pieza])
    return cons
