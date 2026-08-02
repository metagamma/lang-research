#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
¿Sobrevive un saber a quien lo adquirio?

Es la pregunta que da sentido a todo lo demas. Un sistema de signos puede
cumplir los veinte criterios de un lingüista y seguir sin producir
cultura: si cada generacion tiene que aprenderlo todo mordiendo, el
lenguaje sirve para coordinarse en el momento y nada mas.

La prueba se hace en dos pasos, y el segundo no significa nada sin el
primero.

PRUEBA A — correlacional
    Para cada agente y cada tipo del mundo se clasifica su conocimiento:

        VIVIDO      lo ha sufrido en carne propia (`seen[cat] > 0`)
        DE OIDAS    tiene valor para esa categoria pero NUNCA la ha
                    experimentado — solo se lo contaron
        IGNORANTE   no tiene ni idea

    Y se pregunta: ¿evitan los de OIDAS lo toxico mejor que los
    IGNORANTES? Si no, el testimonio no transporta nada util y la prueba
    B no tiene por que salir.

PRUEBA B — intervencion (la de verdad)
    Se mata a TODOS los que tienen experiencia directa de un tipo
    peligroso. Los supervivientes, por construccion, no lo han sufrido
    jamas. ¿Siguen evitandolo?

    Con el brazo `mute` como control obligatorio: alli la purga debe
    dejar a la tribu ciega ante ese tipo. Si tambien lo evitan sin
    lenguaje, lo que estamos midiendo no es cultura sino alguna otra
    cosa — percepcion, suerte o un fallo nuestro.

Nada de esto interviene en la simulacion: se mide desde fuera, con
`classify` (que no aprende) y con `expected_gain` (que no decide nada).
La purga si interviene, obviamente — pero ocurre DESPUES de la corrida
que produjo el conocimiento, no durante.
"""

from collections import Counter

VIVIDO, OIDAS, IGNORANTE = "vivido", "de oidas", "ignorante"


def _cat_de(agent, world, kind, rng, muestras=3):
    """Que categoria usa este agente para este tipo latente. None si ninguna."""
    votos = Counter()
    for _ in range(muestras):
        c = agent.concepts.classify(agent.perceive(world.make(kind, 0, rng)))
        if c is not None:
            votos[c] += 1
    return votos.most_common(1)[0][0] if votos else None


def fuente(agent, cat):
    """Como se entero la PRIMERA vez, no como esta ahora.

    La distincion resulto decisiva. Mirando el estado actual, el grupo
    «de oidas» salia vacio siempre: en un mundo con esta densidad de
    interaccion todo el mundo acaba probandolo todo, y la experiencia
    directa tapaba el rastro de que alguien lo hubiera sabido antes por
    habérselo oido. Lo que interesa no es quien lo ha vivido, sino quien
    lo supo SIN haberlo vivido — aunque despues lo viviera.
    """
    if cat is None or cat not in agent.value:
        return IGNORANTE
    return {"vivido": VIVIDO, "oidas": OIDAS}.get(
        agent.origen.get(cat), VIVIDO)


def evita(agent, world, kind, cat):
    """¿Espera perder si se acerca? Deterministico: no sortea exploracion.

    Se mira la creencia, no la conducta, porque la conducta lleva ruido de
    exploracion y aqui lo que se pregunta es que SABE el agente.
    """
    if cat is None:
        return False
    g = agent.expected_gain(cat, 0)
    return g is not None and g < 0


def censo(agents, world, kind, rng):
    """Reparto de la tribu por fuente de conocimiento sobre un tipo."""
    out = {VIVIDO: [], OIDAS: [], IGNORANTE: []}
    for a in agents:
        cat = _cat_de(a, world, kind, rng)
        out[fuente(a, cat)].append((a, cat))
    return out


def tasa_evitacion(grupo, world, kind):
    if not grupo:
        return None
    return sum(1 for a, c in grupo if evita(a, world, kind, c)) / len(grupo)


def prueba_A(pop, world, rng, kinds):
    """¿Sirve de algo lo que a uno le cuentan?"""
    filas = []
    for k in kinds:
        c = censo(pop.living(), world, k, rng)
        filas.append({
            "tipo": k.name,
            "pago": k.payoff,
            "n_vivido": len(c[VIVIDO]),
            "n_oidas": len(c[OIDAS]),
            "n_ignorante": len(c[IGNORANTE]),
            "evita_vivido": tasa_evitacion(c[VIVIDO], world, k),
            "evita_oidas": tasa_evitacion(c[OIDAS], world, k),
            "evita_ignorante": tasa_evitacion(c[IGNORANTE], world, k),
        })
    return filas


def purga(pop, world, rng, kind):
    """Elimina a todo el que haya sufrido este tipo en persona.

    Aqui si se mira la experiencia directa real (`seen`), no la
    procedencia: se purga a quien lo VIVIO, viniera de donde viniera lo
    que supiera antes.

    Devuelve (muertos, supervivientes). Los supervivientes no tienen, por
    construccion, ni una sola experiencia directa de esta cosa.
    """
    muertos = 0
    for t in pop.tribes:
        quedan = []
        for a in t.living():
            cat = _cat_de(a, world, kind, rng)
            if cat is not None and a.seen.get(cat, 0) > 0:
                a.kill("purga")
                muertos += 1
            else:
                quedan.append(a)
        t.agents = quedan
    return muertos, len(pop.living())


def prueba_B(pop, world, rng, kind):
    """Lo que queda en pie despues de la purga."""
    antes = censo(pop.living(), world, kind, rng)
    n_antes = sum(len(v) for v in antes.values())
    ev_antes = tasa_evitacion(
        antes[VIVIDO] + antes[OIDAS] + antes[IGNORANTE], world, kind)
    muertos, vivos = purga(pop, world, rng, kind)
    if vivos == 0:
        return {"kind": kind.name, "muertos": muertos, "vivos": 0,
                "evita_antes": ev_antes, "evita_despues": None,
                "n_antes": n_antes, "nota": "no sobrevive nadie"}
    desp = censo(pop.living(), world, kind, rng)
    ev_desp = tasa_evitacion(
        desp[VIVIDO] + desp[OIDAS] + desp[IGNORANTE], world, kind)
    return {
        "kind": kind.name, "muertos": muertos, "vivos": vivos,
        "n_antes": n_antes,
        "evita_antes": ev_antes, "evita_despues": ev_desp,
        "oidas_despues": len(desp[OIDAS]),
        "ignorantes_despues": len(desp[IGNORANTE]),
        "nota": "",
    }


def informe_A(filas, modo):
    print(f"\n  PRUEBA A — ¿sirve lo que a uno le cuentan?   [{modo}]")
    print(f"  {'tipo':<16}{'pago':>6}  "
          f"{'vivido':>16}{'de oidas':>16}{'ignorante':>16}")
    for f in filas:
        def fmt(n, ev):
            return f"{n:3d} ev={ev:.2f}" if ev is not None else f"{n:3d}    —  "
        print(f"  {f['tipo']:<16}{f['pago']:>+6.0f}  "
              f"{fmt(f['n_vivido'], f['evita_vivido']):>16}"
              f"{fmt(f['n_oidas'], f['evita_oidas']):>16}"
              f"{fmt(f['n_ignorante'], f['evita_ignorante']):>16}")
    print("  ev = fraccion que espera perder si se acerca (evitacion correcta")
    print("       para lo toxico; los tres grupos ven el MISMO mundo)")


def informe_B(r, modo):
    print(f"\n  PRUEBA B — purga de los que lo vivieron   [{modo}]  "
          f"objetivo: {r['kind']}")
    print(f"    poblacion antes            {r['n_antes']}")
    print(f"    purgados (lo habian vivido){r['muertos']:>5}")
    print(f"    supervivientes             {r['vivos']:>5}")
    if r["vivos"] == 0:
        print(f"    {r['nota']}")
        return
    print(f"    lo evitaban ANTES          {r['evita_antes']:.2f}")
    print(f"    lo evitan DESPUES          {r['evita_despues']:.2f}"
          f"   <- ninguno lo ha sufrido jamas")
    print(f"    de ellos, saben de oidas   {r['oidas_despues']}"
          f"   / ignorantes {r['ignorantes_despues']}")
