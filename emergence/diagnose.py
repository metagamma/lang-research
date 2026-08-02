#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
¿Por que la coherencia lexica se queda en 0.53?

Cuatro fenomenos consecutivos han chocado contra ese techo — recursividad,
descripciones, transmision cultural, vocabulario atributivo — asi que no
es una limitacion de ninguna fase: es la del modelo. Antes de escribir una
fase entera para arreglarlo hay que saber cual de las tres causas manda.

CAUSA 1 — auto-refuerzo de la palabra propia
    Cuando alguien emite su palabra y hay co-observacion, la refuerzan LOS
    DOS: el oyente y el hablante. En el juego de nombres clasico el
    hablante solo refuerza si el otro acerto. Aqui no hay señal de fracaso
    para el lexico, asi que la palabra privada de un recien nacido se
    confirma sola cada vez que la usa, la entienda alguien o no.

CAUSA 2 — divergencia conceptual (irreducible)
    La coherencia mide «misma forma para el mismo tipo latente», pero cada
    agente tiene su propia particion. Si A parte el fruto en dos categorias
    y B en una, usaran palabras distintas LEGITIMAMENTE. Si el techo que
    impone esto ya esta cerca de 0.53, no hay nada que arreglar en el
    lexico y el problema esta en la formacion de conceptos.

CAUSA 3 — ruido de induccion
    `_chunk` y `_align` pueden proponer segmentaciones espurias e inyectar
    formas variantes dentro de un mismo agente.

Las tres se distinguen con medidas baratas. La 3 se ve mirando si un mismo
agente es consistente consigo mismo; la 2, comparando la coherencia global
con la de los agentes que categorizan el tipo de forma pura; la 1,
contando que fraccion de lo que la gente DICE se lo invento ella.
"""

from collections import Counter, defaultdict

from .metrics import form_for


def consistencia_intra(agents, world, rng, por_tipo=10):
    """¿Dice un mismo agente siempre lo mismo ante el mismo tipo?

    Si esto ya es bajo, la incoherencia no esta entre agentes sino DENTRO
    de cada uno, y la causa seria el ruido de induccion o categorias
    inestables — no el juego de nombres.
    """
    scores = []
    for a in agents:
        for k in world.kinds:
            formas = Counter()
            for _ in range(por_tipo):
                f = form_for(a, world.make(k, 0, rng))
                if f:
                    formas[f] += 1
            tot = sum(formas.values())
            if tot >= por_tipo // 2:
                scores.append(formas.most_common(1)[0][1] / tot)
    return sum(scores) / len(scores) if scores else 0.0


def pureza_categorial(agents, world, rng, por_tipo=8):
    """Para cada agente y tipo: ¿le asigna UNA categoria, y solo a el?

    Devuelve (fraccion_estable, coherencia_global, coherencia_entre_puros).

    Si la coherencia sube mucho al restringirse a los agentes que
    categorizan ese tipo de forma limpia, el techo lo pone la divergencia
    conceptual y no el lexico.
    """
    cat_de = defaultdict(dict)      # (agente, tipo) -> categoria modal
    estable = 0
    total = 0
    for a in agents:
        for k in world.kinds:
            votos = Counter()
            for _ in range(por_tipo):
                c = a.concepts.classify(a.perceive(world.make(k, 0, rng)))
                if c is not None:
                    votos[c] += 1
            total += 1
            if not votos:
                continue
            c, n = votos.most_common(1)[0]
            if n / sum(votos.values()) >= 0.8:
                estable += 1
                cat_de[k.name][a.id] = (a, c)

    glob, puros = [], []
    for k in world.kinds:
        # coherencia global sobre este tipo
        todas = Counter()
        for a in agents:
            f = form_for(a, world.make(k, 0, rng))
            if f:
                todas[f] += 1
        if todas:
            glob.append(todas.most_common(1)[0][1] / sum(todas.values()))
        # coherencia solo entre los que lo categorizan de forma estable
        sub = Counter()
        for a, c in cat_de[k.name].values():
            f = a.gram.cat.produce(c)
            if f:
                sub[f] += 1
        if sum(sub.values()) >= 3:
            puros.append(sub.most_common(1)[0][1] / sum(sub.values()))
    m = lambda xs: sum(xs) / len(xs) if xs else 0.0
    return estable / max(1, total), m(glob), m(puros)


def origen_de_lo_que_se_dice(agents, world, rng, por_tipo=6):
    """De lo que la gente DICE, ¿cuanto se lo invento ella misma?

    Es la comprobacion directa de la causa 1. Si la mayoria de las formas
    que se emiten son de cosecha propia, el auto-refuerzo esta ganando a
    la adopcion y el lexico no puede converger.
    """
    tally = Counter()
    for a in agents:
        for k in world.kinds:
            for _ in range(por_tipo):
                c = a.concepts.classify(a.perceive(world.make(k, 0, rng)))
                if c is None:
                    continue
                f = a.gram.cat.produce(c)
                if not f:
                    continue
                par = (f, c)
                if par in a.gram.cat.born_invented:
                    tally["propia (acuñada por el)"] += 1
                elif par in a.gram.cat.born_extended:
                    tally["propia (metafora)"] += 1
                else:
                    tally["adoptada (la oyo)"] += 1
    return tally


def report(agents, world, rng):
    line = "=" * 74
    print("\n" + line)
    print("DIAGNOSTICO DEL TECHO DE COHERENCIA")
    print(line)

    c = consistencia_intra(agents, world, rng)
    print(f"\n  1. Consistencia INTRA-agente: {c:.3f}")
    print("     (¿dice cada uno siempre lo mismo ante lo mismo?)")
    if c < 0.7:
        print("     -> BAJA: la incoherencia empieza dentro de cada cabeza.")
    else:
        print("     -> alta: cada agente es coherente consigo mismo;")
        print("        el problema esta ENTRE agentes.")

    est, glob, puros = pureza_categorial(agents, world, rng)
    print(f"\n  2. Divergencia conceptual")
    print(f"     categorizacion estable:        {est:.3f}")
    print(f"     coherencia global:             {glob:.3f}")
    print(f"     coherencia entre los 'puros':  {puros:.3f}")
    if puros > glob + 0.12:
        print("     -> el techo lo pone la particion, no el lexico.")
    else:
        print("     -> la divergencia conceptual NO explica el techo.")

    t = origen_de_lo_que_se_dice(agents, world, rng)
    tot = sum(t.values())
    print(f"\n  3. Origen de lo que se dice  (n={tot})")
    for k, v in t.most_common():
        print(f"     {k:<28} {v:5d}  ({v/max(1,tot):.1%})")
    propia = sum(v for k, v in t.items() if k.startswith("propia"))
    if tot and propia / tot > 0.5:
        print("     -> MAYORIA de cosecha propia: el auto-refuerzo gana")
        print("        a la adopcion. Causa 1 confirmada.")
    else:
        print("     -> mayoria adoptada: la adopcion funciona.")
    return c, (est, glob, puros), t


def variantes(agents, world, rng, por_tipo=8):
    """¿Como se reparten las palabras rivales de cada tipo?

    Dos patologias distintas se ven aqui, y piden arreglos OPUESTOS:

      pocas variantes grandes  -> fallo de ruptura de simetria. La
                                  inhibicion lateral no logra que una gane.
      cola larga de variantes  -> inyeccion continua de formas nuevas.

    Aplicar el arreglo de una a la otra empeora las cosas, asi que sin
    este dato cualquier fase seria una apuesta.
    """
    filas = []
    for k in world.kinds:
        c = Counter()
        for a in agents:
            for _ in range(por_tipo):
                f = form_for(a, world.make(k, 0, rng))
                if f:
                    c[f] += 1
        tot = sum(c.values())
        if tot < 6:
            continue
        cuotas = [n / tot for _, n in c.most_common()]
        filas.append({"tipo": k.name, "n_variantes": len(c),
                      "cuotas": cuotas, "top": cuotas[0]})
    return filas


def report_variantes(filas):
    print("\n  DISTRIBUCION DE VARIANTES POR TIPO")
    print(f"  {'tipo':<17}{'variantes':>10}  reparto (cuotas de las 5 mayores)")
    for f in filas:
        rep = " ".join(f"{q:.2f}" for q in f["cuotas"][:5])
        print(f"  {f['tipo']:<17}{f['n_variantes']:>10}  {rep}")
    if not filas:
        return
    med_var = sum(f["n_variantes"] for f in filas) / len(filas)
    med_top = sum(f["top"] for f in filas) / len(filas)
    # cuantas variantes acumulan el 80% del uso
    efectivas = []
    for f in filas:
        acc = n = 0
        for q in f["cuotas"]:
            acc += q
            n += 1
            if acc >= 0.8:
                break
        efectivas.append(n)
    med_ef = sum(efectivas) / len(efectivas)
    print(f"\n  variantes por tipo: {med_var:.1f}   cuota de la mayoritaria: {med_top:.2f}")
    print(f"  variantes que acumulan el 80% del uso: {med_ef:.1f}")
    if med_ef <= 3.5:
        print("  -> POCAS Y GRANDES: fallo de ruptura de simetria.")
    else:
        print("  -> COLA LARGA: inyeccion continua de formas nuevas.")
