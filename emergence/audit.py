#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carta de la lengua — ¿es esto un idioma?

Este modulo NO es parte de la simulacion. Coge una poblacion al final de
una corrida y la somete, criterio por criterio, a la lista de propiedades
que un lingüista pediria para llamar «lengua» a un sistema.

Cada criterio devuelve un veredicto y un numero que lo respalda. La
regla que me impongo: si algo no se puede medir, se declara NO MEDIDO, y
si sale mal, sale mal. Un informe que solo sabe decir que si no sirve
para nada — y menos en un proyecto cuya gracia es que las cosas puedan
fallar.

Tres niveles de veredicto:

    SI        hay evidencia cuantitativa a favor
    PARCIAL   existe el fenomeno pero debil o incompleto
    NO        no esta, o lo esta por construccion nuestra y no emergio
"""

from collections import Counter, defaultdict

from .events import ACTION_NAME, ACTIONS, BEFORE, NOW
from .metrics import (levenshtein, naming_table, signal_for, spearman,
                      topographic_similarity)
from .syntax import CORE_ORDERS, ORDER_NAME, V_ACT, V_CAT, V_PLACE, V_TENSE

SI, PARCIAL, NO, NM = "SI", "PARCIAL", "NO", "NO MEDIDO"


class Finding:
    def __init__(self, name, verdict, value, note):
        self.name = name
        self.verdict = verdict
        self.value = value
        self.note = note


def _f(name, verdict, value, note):
    return Finding(name, verdict, value, note)


# ---------------------------------------------------------------------

def inventario(agents, cfg):
    """1. Inventario finito de unidades basicas."""
    from .phonology import CODAS, NUCLEI, ONSETS
    n = len(ONSETS) * len(NUCLEI) * (1 + len(CODAS))
    formas = set()
    for a in agents:
        formas |= set(a.gram.voc[V_CAT].by_form)
        formas |= set(a.gram.voc[V_ACT].by_form)
    return _f("inventario de unidades", SI, len(ONSETS) + len(NUCLEI) + len(CODAS),
              f"{len(ONSETS)} ataques + {len(NUCLEI)} nucleos + {len(CODAS)} codas "
              f"= {n} silabas posibles; {len(formas)} morfos distintos en uso")


def doble_articulacion(agents):
    """13. Doble articulacion: unidades sin significado que forman unidades con el."""
    seg = Counter()
    formas = set()
    for a in agents:
        for v in (V_CAT, V_ACT, V_PLACE, V_TENSE):
            formas |= set(a.gram.voc[v].by_form)
    for f in formas:
        for ch in f:
            seg[ch] += 1
    if not formas:
        return _f("doble articulacion", NO, 0.0, "no hay morfos")
    reuso = sum(seg.values()) / max(1, len(seg))
    v = SI if (len(seg) < len(formas) and reuso > 3) else PARCIAL
    return _f("doble articulacion", v, reuso,
              f"{len(seg)} segmentos sin significado se recombinan en "
              f"{len(formas)} morfos con significado (reuso medio {reuso:.1f}x)")


def lexico(agents, cfg):
    """2. Lexico: unidades con significado."""
    pares = sum(len(a.gram.voc[V_CAT].strong_pairs()) for a in agents)
    n = pares / max(1, len(agents))
    return _f("lexico", SI if n >= 3 else PARCIAL, n,
              f"{n:.1f} asociaciones forma-significado firmes por agente")


def arbitrariedad(agents, world, rng):
    """10. Arbitrariedad: forma y significado no guardan relacion natural.

    Se mide al reves que la composicionalidad: correlacionamos distancia
    SENSORIAL entre tipos con distancia entre sus morfos. Si el idioma
    fuera iconico, los tipos parecidos sonarian parecido y saldria alto.
    Cerca de cero significa arbitrario, que es lo que debe pasar: las
    formas se acuñaron al azar.
    """
    import numpy as np
    modal = {}
    tabla = naming_table(agents, world, rng, 6)
    for k in world.kinds:
        c = tabla.get(k.name)
        if c:
            modal[k.name] = c.most_common(1)[0][0]
    nombres = list(modal)
    if len(nombres) < 4:
        return _f("arbitrariedad", NM, 0.0, "muy pocos tipos con nombre")
    proto = {k.name: k.prototype for k in world.kinds}
    ds, dm = [], []
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            a, b = nombres[i], nombres[j]
            ds.append(float(np.linalg.norm(proto[a] - proto[b])))
            x, y = modal[a], modal[b]
            dm.append(levenshtein(x, y) / max(len(x), len(y), 1))
    r = spearman(ds, dm)
    return _f("arbitrariedad", SI if abs(r) < 0.25 else PARCIAL, r,
              f"correlacion forma~sentido = {r:+.3f} (0 = arbitrario puro)")


def convencionalidad(coherence):
    """11. Convencionalidad: la comunidad comparte las asociaciones."""
    v = SI if coherence >= 0.5 else (PARCIAL if coherence >= 0.25 else NO)
    return _f("convencionalidad", v, coherence,
              f"coherencia lexica intra-tribu = {coherence:.3f} "
              f"(fraccion que usa la misma forma para lo mismo)")


def composicionalidad(topsim, composed):
    """5+9. Composicionalidad y sistematicidad."""
    v = SI if topsim >= 0.30 else (PARCIAL if topsim >= 0.12 else NO)
    return _f("composicionalidad", v, topsim,
              f"similitud topografica = {topsim:+.3f}; "
              f"{composed:.0%} de las señales se construyen por partes")


def morfologia(agents):
    """3a. Morfologia: hay reglas para formar palabras."""
    con = sum(1 for a in agents if a.gram.has_rules())
    frac = con / max(1, len(agents))
    v = SI if frac >= 0.6 else (PARCIAL if frac >= 0.2 else NO)
    return _f("morfologia", v, frac,
              f"{frac:.0%} de los agentes han inducido fronteras de morfo")


def sintaxis(agents):
    """3b+4. Sintaxis: el orden significa, y la comunidad comparte cual.

    Si todos convergen al mismo orden, el orden es una convencion que
    carga significado. Si cada uno tiene el suyo, no hay sintaxis: hay
    ruido posicional.
    """
    if not agents:
        return _f("sintaxis", NM, 0.0, "sin poblacion")
    votos = Counter(a.gram.best_order() for a in agents)
    top, n = votos.most_common(1)[0]
    cuota = n / len(agents)
    conf = sum(a.gram.order_confidence() for a in agents) / len(agents)
    v = SI if (cuota >= 0.7 and conf >= 0.3) else (PARCIAL if cuota >= 0.45 else NO)
    reparto = ", ".join(f"{ORDER_NAME[o]} {c/len(agents):.0%}"
                        for o, c in votos.most_common(3))
    return _f("sintaxis (orden convergente)", v, cuota,
              f"orden dominante {ORDER_NAME[top]} en {cuota:.0%} de la tribu "
              f"(confianza media {conf:.2f}); reparto: {reparto}")


def productividad(agents, world, cfg):
    """6. Productividad: infinitas expresiones con recursos finitos."""
    if not agents:
        return _f("productividad", NM, 0.0, "sin poblacion")
    a = max(agents, key=lambda x: x.gram.size())
    morfos = sum(len(a.gram.voc[v].by_form) for v in range(4))
    cats = len(a.concepts)
    espacio = len(ACTIONS) * max(1, cats) * world.n_places * 2
    return _f("productividad", SI if espacio > 10 * max(1, morfos) else PARCIAL,
              espacio,
              f"con {morfos} morfos puede expresar ~{espacio} significados "
              f"distintos ({len(ACTIONS)} acciones x {cats} categorias x "
              f"{world.n_places} lugares x 2 tiempos)")


def desplazamiento(rates):
    """12. Desplazamiento: hablar de lo que no esta delante."""
    past = rates.get("past_rate", 0.0)
    anchor = rates.get("anchor_shared", 0.0)
    v = SI if past >= 0.10 else (PARCIAL if past > 0.02 else NO)
    return _f("desplazamiento", v, past,
              f"{past:.0%} de los enunciados hablan del pasado; "
              f"{anchor:.0%} de ellos se anclan en memoria compartida")


def transmision_cultural(agents):
    """19. Transmision cultural: se aprende de otros, no se hereda."""
    return _f("transmision cultural", SI, 1.0,
              "el hijo nace sin categorias ni palabras; solo hereda la "
              "vigilancia perceptiva. La lengua se adquiere viviendo")


def testimonio(rates):
    """Aprender del mundo por lo que otros cuentan (base de la cultura)."""
    t = rates.get("testimony_rate", 0.0)
    v = SI if t >= 0.05 else (PARCIAL if t > 0.005 else NO)
    return _f("saber transmitido", v, t,
              f"{t:.1%} de los relatos del pasado enseñan al oyente algo "
              f"del mundo que no habia vivido")


def variacion(dist):
    """17. Variacion: dialectos distintos en comunidades separadas."""
    if dist is None:
        return _f("variacion (dialectos)", NM, 0.0, "una sola tribu")
    v = SI if dist >= 0.5 else PARCIAL
    return _f("variacion (dialectos)", v, dist,
              f"distancia lexica entre tribus = {dist:.2f} "
              f"(1.00 = ninguna palabra en comun)")


def cambio(n_shifts):
    """18. Cambio: los significados se mueven con el tiempo."""
    v = SI if n_shifts >= 2 else (PARCIAL if n_shifts >= 1 else NO)
    return _f("cambio semantico", v, float(n_shifts),
              f"{n_shifts} palabras cambiaron de referente dominante")


def ambiguedad(agents):
    """23. Ambigüedad: una forma con varios significados."""
    if not agents:
        return _f("polisemia", NM, 0.0, "sin poblacion")
    p = sum(a.gram.voc[V_CAT].polysemy() for a in agents) / len(agents)
    v = SI if p > 1.05 else (PARCIAL if p > 1.0 else NO)
    return _f("polisemia", v, p,
              f"{p:.2f} significados fuertes por forma")


def creatividad(rates):
    """16. Creatividad: se producen enunciados nunca oidos."""
    nov = rates.get("novel_rate", 0.0)
    ok = rates.get("novel_success", 0.0)
    v = SI if nov >= 0.15 else (PARCIAL if nov > 0.03 else NO)
    return _f("creatividad", v, nov,
              f"{nov:.0%} de las señales expresan combinaciones que el "
              f"hablante nunca habia dicho (aciertos {ok:.2f})")


def recursividad(rates, agents):
    """7. Recursividad: una estructura dentro de otra igual.

    Se mide, no se declara: cuantos enunciados llevan una oracion encajada
    y que fraccion se reconoce como tal. Que exista el mecanismo no basta;
    si nadie lo usa o nadie lo entiende, no hay recursividad, hay codigo.
    """
    q = rates.get("quote_rate", 0.0)
    ok = rates.get("quote_understood", 0.0)
    marca = sum(1 for a in agents
                if a.gram.voc[V_ACT].produce(4) is not None) / max(1, len(agents))
    if q < 0.005:
        return _f("recursividad", NO, q, "el encaje existe pero no se usa")
    v = SI if (q >= 0.03 and ok >= 0.3) else PARCIAL
    return _f("recursividad", v, q,
              f"{q:.1%} de los enunciados encajan una oracion dentro de otra "
              f"('dijo que...'); {ok:.0%} se reconocen como tal; "
              f"{marca:.0%} de los agentes tienen complementante")


def metalinguistica(rates, agents):
    """16. Metalinguistica: la lengua hablando de sus propios signos.

    Se mide el acto «[palabra] se-dice [descripcion]»: cuantos se emiten y
    en cuantos el oyente se queda con la palabra. Que exista el mecanismo
    no basta — si nadie lo aprende, hay codigo y no metalenguaje.
    """
    m = rates.get("meta_rate", 0.0)
    ok = rates.get("meta_learned", 0.0)
    if m < 0.002:
        return _f("metalingüistica", NO, m, "el acto existe pero no se usa")
    v = SI if (m >= 0.01 and ok >= 0.15) else PARCIAL
    return _f("metalingüistica", v, ok,
              f"{m:.1%} de los enunciados enseñan una palabra "
              f"(«esto se dice X: verde, amargo»); el oyente se la queda "
              f"en el {ok:.1%} de los casos")


def pragmatica(agents, world):
    """8. Pragmatica: el contexto cambia la interpretacion.

    No basta con que el mecanismo este puesto: se comprueba si alguna
    forma polisemica se LEE distinto segun la region. Cero significa que
    no hay ambigüedad real que resolver, por mucho contexto que se mire.
    """
    if not agents:
        return _f("pragmatica", NM, 0.0, "sin poblacion")
    cambian = total = 0
    for a in agents:
        voc = a.gram.voc[V_CAT]
        for forma, cats in voc.by_form.items():
            if len(cats) < 2:
                continue
            total += 1
            lecturas = set()
            for reg in range(world.n_places):
                ctx = a.contexto_de(reg)
                if ctx is None:
                    continue
                c, _ = voc.best_for(forma, ctx)
                if c is not None:
                    lecturas.add(c)
            if len(lecturas) > 1:
                cambian += 1
    frac = cambian / max(1, total)
    v = SI if frac >= 0.05 else (PARCIAL if frac > 0.005 else NO)
    return _f("pragmatica", v, frac,
              f"{cambian} de {total} formas polisemicas se leen distinto "
              f"segun donde se digan ({frac:.1%})")


def no_implementado():
    return [
        _f("orden de circunstanciales", NO, 0.0,
           "lugar y tiempo van siempre al final porque lo fijamos nosotros. "
           "Solo emerge el orden de los argumentos"),
    ]


# ---------------------------------------------------------------------

def audit(pop, world, rng, last, semantic_logs, coherence, dist):
    """Pasa toda la lista y devuelve los hallazgos."""
    agents = pop.living()
    cfg = pop.cfg
    shifts = sum(len(sl.shifts()) for sl in semantic_logs)
    out = [
        inventario(agents, cfg),
        doble_articulacion(agents),
        lexico(agents, cfg),
        arbitrariedad(agents, world, rng),
        convencionalidad(coherence),
        morfologia(agents),
        sintaxis(agents),
        composicionalidad(last.get("topsim", 0.0), last.get("said_composed", 0.0)),
        productividad(agents, world, cfg),
        creatividad(last),
        desplazamiento(last),
        testimonio(last),
        ambiguedad(agents),
        variacion(dist),
        cambio(shifts),
        transmision_cultural(agents),
        recursividad(last, agents),
        pragmatica(agents, world),
        metalinguistica(last, agents),
    ]
    out.extend(no_implementado())
    return out


def report(findings):
    line = "=" * 74
    print("\n" + line)
    print("CARTA DE LA LENGUA  —  ¿cumple los criterios de un idioma?")
    print(line)
    tally = Counter(f.verdict for f in findings)
    for f in findings:
        print(f"  [{f.verdict:^9}] {f.name}")
        print(f"              {f.note}")
    print("\n  " + "  ".join(f"{k}: {v}" for k, v in
                             sorted(tally.items(), key=lambda kv: -kv[1])))
    total = sum(tally.values())
    print(f"  {tally.get(SI,0)}/{total} criterios con evidencia a favor, "
          f"{tally.get(PARCIAL,0)} parciales, {tally.get(NO,0)} no cumplidos.")
    return tally


# ---------------------------------------------------------------------
# Auditoria sobre varias semillas
#
# Un informe de una sola corrida dice poco: la variacion entre semillas de
# este modelo es del mismo orden que muchos de los efectos. Aqui cada
# criterio se acompaña de su media, su desviacion y —lo mas informativo—
# EN CUANTAS de las N corridas salio SI. Un criterio que sale SI en 11 de
# 12 no es lo mismo que uno que sale SI en 6, aunque la media coincida.
# ---------------------------------------------------------------------

def audit_many(cfg, n_tribes, generations, seeds):
    from .metrics import lexical_distance
    from .run import simulate

    print(f"CARTA DE LA LENGUA  —  {seeds} semillas x {generations} "
          f"generaciones, mundo '{cfg.world}', banda {cfg.max_pop}\n")
    por_criterio = {}
    orden = []
    vivas = 0
    for seed in range(1, seeds + 1):
        recs, st = simulate("language", seed, cfg, n_tribes, generations,
                            metrics_every=max(1, generations // 2))
        pop, world, rng = st["pop"], st["world"], st["rng"]
        if pop.extinct():
            print(f"  semilla {seed:2d}  EXTINTA")
            continue
        vivas += 1
        d = None
        if n_tribes > 1 and pop.tribes[0].living() and pop.tribes[1].living():
            d = lexical_distance(pop.tribes[0].living(),
                                 pop.tribes[1].living(), world, rng)
        hallazgos = audit(pop, world, rng, recs[-1], st["semantic"],
                          recs[-1].get("coherence", 0.0), d)
        for f in hallazgos:
            if f.name not in por_criterio:
                por_criterio[f.name] = {"v": [], "ver": Counter()}
                orden.append(f.name)
            por_criterio[f.name]["v"].append(f.value)
            por_criterio[f.name]["ver"][f.verdict] += 1
        print(f"  semilla {seed:2d}  "
              + " ".join(f"{f.verdict[0]}" for f in hallazgos), flush=True)

    if not vivas:
        print("\ntodas las corridas se extinguieron")
        return

    from .metrics import mean, stdev
    line = "=" * 78
    print("\n" + line)
    print(f"RESULTADO   ({vivas} corridas con supervivientes)")
    print(line)
    tally = Counter()
    for nombre in orden:
        d = por_criterio[nombre]
        vs = [x for x in d["v"] if isinstance(x, (int, float))]
        si = d["ver"].get(SI, 0)
        pa = d["ver"].get(PARCIAL, 0)
        no = d["ver"].get(NO, 0) + d["ver"].get(NM, 0)
        # el veredicto agregado exige mayoria clara, no una corrida afortunada
        if si >= 0.7 * vivas:
            v = SI
        elif si + pa >= 0.6 * vivas:
            v = PARCIAL
        else:
            v = NO
        tally[v] += 1
        val = f"{mean(vs):+.3f} ± {stdev(vs):.3f}" if vs else "—"
        print(f"  [{v:^9}] {nombre:<34} {val:>18}   "
              f"SI en {si}/{vivas}")
    print("\n" + "  ".join(f"{k}: {n}" for k, n in tally.most_common()))
    tot = sum(tally.values())
    print(f"  {tally.get(SI,0)}/{tot} criterios con evidencia, "
          f"{tally.get(PARCIAL,0)} parciales, {tally.get(NO,0)} no cumplidos.")
    print("\nEl veredicto agregado exige SI en al menos el 70% de las")
    print("  corridas. Un criterio que sale bien en la mitad no es un")
    print("  criterio cumplido: es uno que depende de la semilla.")
