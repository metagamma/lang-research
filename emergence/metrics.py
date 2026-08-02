#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instrumentacion.

Todo lo que hay aqui se ejecuta DESDE FUERA de la simulacion, sobre una
bateria fija de estimulos (`world.probe_set`), y siempre con
`classify()` en vez de `categorize()` para no contaminar lo que mide.

Los agentes nunca ven nada de este modulo. Las etiquetas de tipo latente
y de afordancia se usan solo aqui: son nuestra vara de medir, no
informacion disponible para ellos.
"""

import math
from collections import Counter, defaultdict

import numpy as np

from .events import HAY, NOW

# el mundo llega como argumento: nada de constantes globales


def _say(agent, cat, place):
    """Lo que este agente diria de «hay un X en L». Sin aprender nada."""
    return agent.gram.express((HAY, cat, None, place, NOW))[0]


def stack(things):
    """Matriz (m, dim) con los rasgos de una lista de estimulos."""
    return np.stack([t.features for t in things]) if things else np.empty((0, 0))


# ---------------------------------------------------------------------
# informacion mutua normalizada entre dos particiones
# ---------------------------------------------------------------------

def nmi(a, b):
    """NMI in [0,1]. 1 = particiones equivalentes, 0 = independientes."""
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    n = len(pairs)
    if n == 0:
        return 0.0
    ca = Counter(x for x, _ in pairs)
    cb = Counter(y for _, y in pairs)
    cab = Counter(pairs)

    def H(c):
        return -sum((v / n) * math.log(v / n) for v in c.values() if v)

    Ha, Hb = H(ca), H(cb)
    if Ha <= 1e-12 or Hb <= 1e-12:
        return 1.0 if (Ha <= 1e-12 and Hb <= 1e-12) else 0.0
    info = 0.0
    for (x, y), v in cab.items():
        pxy = v / n
        info += pxy * math.log(pxy / ((ca[x] / n) * (cb[y] / n)))
    return max(0.0, min(1.0, info / math.sqrt(Ha * Hb)))


# ---------------------------------------------------------------------
# lecturas sobre la poblacion
# ---------------------------------------------------------------------

def partition_of(agent, probes, X=None):
    return agent.concepts.classify_many(stack(probes) if X is None else X)


def prediction_score(agents, probes):
    """¿Predicen las categorias de un agente lo que el mundo le hara?

    NMI entre su particion y la afordancia real. Es la traduccion directa
    del "improves prediction" del axioma. Nadie optimiza esta cifra.
    """
    truth = [p.affordance for p in probes]
    if not agents:
        return 0.0
    X = stack(probes)
    return sum(nmi(partition_of(a, probes, X), truth) for a in agents) / len(agents)


def concept_alignment(agents, probes, rng, max_pairs=60):
    """¿Trocean el mundo igual dos agentes distintos?"""
    if len(agents) < 2:
        return 0.0
    X = stack(probes)
    parts = {}
    total, n = 0.0, 0
    for _ in range(max_pairs):
        a, b = rng.sample(agents, 2)
        for ag in (a, b):
            if ag.id not in parts:
                parts[ag.id] = partition_of(ag, probes, X)
        total += nmi(parts[a.id], parts[b.id])
        n += 1
    return total / max(1, n)


def form_for(agent, thing):
    """La parte de la señal que denota QUE es (sin aprender del estimulo).

    Si el agente tiene morfo de categoria, ese; si aun habla por bloques,
    la señal entera. Asi la tabla de nombres sigue siendo legible tanto
    en una lengua holistica como en una compuesta.
    """
    cat = agent.concepts.classify(agent.perceive(thing))
    if cat is None:
        return None
    m = agent.gram.cat.produce(cat)
    if m:
        return m
    return _say(agent, cat, thing.place)


def signal_for(agent, thing):
    """La señal COMPLETA que emitiria: (que es) + (donde esta)."""
    cat = agent.concepts.classify(agent.perceive(thing))
    if cat is None:
        return None
    return _say(agent, cat, thing.place)


def naming_table(agents, world, rng, per_kind=8, max_agents=30):
    """kind -> Counter(forma) sobre una muestra de la poblacion dada."""
    if len(agents) > max_agents:
        agents = rng.sample(agents, max_agents)
    table = defaultdict(Counter)
    for k in world.kinds:
        things = [world.make(k, 0, rng) for _ in range(per_kind)]
        X = stack(things)
        for a in agents:
            for t, c in zip(things, a.classify_batch(X)):
                if c is None:
                    continue
                f = a.gram.cat.produce(c) or _say(a, c, t.place)
                if f:
                    table[k.name][f] += 1
    return table


def lexical_coherence(agents, world, rng, per_kind=8):
    """Fraccion de la tribu que usa la MISMA forma para el mismo tipo.

    Promediada sobre tipos que reciben nombre. Es la medida clasica de
    convergencia lexica, pero calculada sobre tipos latentes del mundo,
    no sobre conceptos regalados a los agentes.
    """
    table = naming_table(agents, world, rng, per_kind)
    scores = []
    for kind, counts in table.items():
        tot = sum(counts.values())
        if tot == 0:
            continue
        scores.append(counts.most_common(1)[0][1] / tot)
    return sum(scores) / len(scores) if scores else 0.0


def naming_coverage(agents, world, rng, per_kind=8):
    """Que fraccion de las ocasiones produce ALGUNA forma (¿se nombra?).

    Prediccion del modelo: los tipos inertes se quedan sin nombre. Nadie
    lo programa; simplemente hablar de ellos no compensa.
    """
    out = {}
    for k in world.kinds:
        things = [world.make(k, 0, rng) for _ in range(per_kind)]
        X = stack(things)
        hits, tot = 0, 0
        for a in agents:
            for t, c in zip(things, a.classify_batch(X)):
                tot += 1
                if c is None:
                    continue
                if a.gram.cat.produce(c) or _say(a, c, t.place):
                    hits += 1
        out[k.name] = hits / max(1, tot)
    return out


def lexicon_stats(agents):
    if not agents:
        return {"synonymy": 0.0, "polysemy": 0.0, "size": 0.0,
                "metaphor": 0.0, "composed": 0.0, "rules": 0.0}
    n = len(agents)
    return {
        "synonymy": sum(a.lex.synonymy() for a in agents) / n,
        "polysemy": sum(a.lex.polysemy() for a in agents) / n,
        "size": sum(a.gram.size() for a in agents) / n,
        "metaphor": sum(a.lex.metaphor_share() for a in agents) / n,
        # Fase 5
        "composed": sum(a.gram.compositional_share() for a in agents) / n,
        "rules": sum(1 for a in agents if a.gram.has_rules()) / n,
    }


# ---------------------------------------------------------------------
# Fase 5 — ¿tiene partes la señal?
# ---------------------------------------------------------------------

def levenshtein(a, b):
    if a == b:
        return 0
    if not a or not b:
        return len(a) or len(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                           prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(xs, ys):
    if len(xs) < 3:
        return 0.0
    rx, ry = _ranks(xs), _ranks(ys)
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx and dy else 0.0


def topographic_similarity(agents, world, rng, per_cell=3, max_agents=24):
    """Correlacion entre distancia de SIGNIFICADO y distancia de SEÑAL.

    Es la medida canonica de composicionalidad. Un idioma holistico da
    ~0: significados parecidos llevan cadenas sin ningun parecido, porque
    cada bloque se acuño aparte. Un idioma compuesto da alto: cambiar un
    solo atributo del significado cambia un solo trozo de la señal.

    Los significados se toman como (tipo latente, lugar), que es la unica
    referencia comun a todos los agentes; la señal, la que produce la
    mayoria de la poblacion. Nada de esto lo ve nadie desde dentro.
    """
    if len(agents) < 2:
        return 0.0
    # Muestreamos hablantes en vez de censarlos: la señal MODAL de 24
    # agentes ya estima bien la de la poblacion, y el coste deja de crecer
    # con ella. Sin este tope, un mundo con 40 tipos y 8 lugares vuelve la
    # medicion mas cara que la propia simulacion.
    if len(agents) > max_agents:
        agents = rng.sample(agents, max_agents)
    meanings, signals = [], []
    for ki, k in enumerate(world.kinds):
        for pl in range(world.n_places):
            things = [world.make(k, pl, rng) for _ in range(per_cell)]
            X = stack(things)
            votes = Counter()
            for a in agents:
                for c in a.classify_batch(X):
                    if c is None:
                        continue
                    sig = _say(a, c, pl)
                    if sig:
                        votes[sig] += 1
            if votes:
                meanings.append((ki, pl))
                signals.append(votes.most_common(1)[0][0])
    if len(meanings) < 4:
        return 0.0

    md, sd = [], []
    for i in range(len(meanings)):
        for j in range(i + 1, len(meanings)):
            a, b = meanings[i], meanings[j]
            md.append((a[0] != b[0]) + (a[1] != b[1]))
            x, y = signals[i], signals[j]
            sd.append(levenshtein(x, y) / max(len(x), len(y), 1))
    return spearman(md, sd)


def generalization(agents, world, rng, per_cell=3):
    """¿Cuantas combinaciones (tipo, lugar) sabe expresar la poblacion?

    Cobertura del espacio de significados. Un idioma holistico solo cubre
    lo que le ha dado tiempo a oir; uno compuesto cubre tambien lo que
    nunca se dijo, porque lo arma con piezas.
    """
    if not agents:
        return 0.0
    hits = tot = 0
    for k in world.kinds:
        for pl in range(world.n_places):
            things = [world.make(k, pl, rng) for _ in range(per_cell)]
            X = stack(things)
            a = rng.choice(agents)
            for c in a.classify_batch(X):
                tot += 1
                if c is not None and _say(a, c, pl):
                    hits += 1
    return hits / max(1, tot)


# ---------------------------------------------------------------------
# Fase 4 — cambio semantico
# ---------------------------------------------------------------------

def form_kind_table(agents, world, rng, per_kind=8):
    """forma -> Counter(tipo latente al que se le aplica).

    Es `naming_table` del reves. Con esto se puede seguir a QUE se refiere
    una palabra a lo largo de las generaciones, que es lo unico que
    permite decir si su significado cambio.
    """
    inv = defaultdict(Counter)
    for kind, counts in naming_table(agents, world, rng, per_kind).items():
        for form, n in counts.items():
            inv[form][kind] += n
    return inv


def dominant_meanings(agents, world, rng, per_kind=8, min_uses=4):
    """forma -> (tipo dominante, cuota). Descarta lo residual."""
    out = {}
    for form, counts in form_kind_table(agents, world, rng, per_kind).items():
        total = sum(counts.values())
        if total < min_uses:
            continue
        kind, n = counts.most_common(1)[0]
        out[form] = (kind, n / total)
    return out


class SemanticLog:
    """Diario de significados. Compara instantaneas para detectar deriva.

    No interviene en nada: solo mira. Cada instantanea es el tipo latente
    dominante de cada forma viva en esa generacion.
    """

    def __init__(self):
        self.snapshots = []          # [(gen, {forma: (tipo, cuota)})]

    def record(self, gen, agents, world, rng, per_kind=6):
        if agents:
            self.snapshots.append((gen, dominant_meanings(agents, world, rng,
                                                          per_kind)))

    def shifts(self, min_share=0.5):
        """Formas que sobreviven pero han cambiado de referente.

        Devuelve (forma, gen_inicial, tipo_inicial, gen_final, tipo_final).
        Solo cuenta si en ambos extremos el dominio era claro: si nunca
        significo nada nitido, cambiar de moda no es cambio semantico.
        """
        if len(self.snapshots) < 2:
            return []
        gen_last, last = self.snapshots[-1]
        out = []
        for form, (kind_now, share_now) in last.items():
            if share_now < min_share:
                continue
            for gen0, snap in self.snapshots:          # primera aparicion nitida
                first = snap.get(form)
                if first and first[1] >= min_share:
                    if first[0] != kind_now:
                        out.append((form, gen0, first[0], gen_last, kind_now))
                    break
        return out


def lexical_distance(tribe_a, tribe_b, world, rng, per_kind=6):
    """Fraccion de tipos en los que dos tribus usan formas modales distintas."""
    ta = naming_table(tribe_a, world, rng, per_kind)
    tb = naming_table(tribe_b, world, rng, per_kind)
    kinds = [k.name for k in world.kinds]
    diff, comparable = 0, 0
    for k in kinds:
        ca, cb = ta.get(k), tb.get(k)
        if not ca or not cb:
            continue
        comparable += 1
        if ca.most_common(1)[0][0] != cb.most_common(1)[0][0]:
            diff += 1
    return diff / comparable if comparable else 0.0


def zipf_profile(agents, top=15):
    c = Counter()
    for a in agents:
        c.update(a.lex.use)
    return c.most_common(top)


# ---------------------------------------------------------------------
# estadistica para la ablacion
# ---------------------------------------------------------------------

def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def bootstrap_diff(xs, ys, rng, iters=8000):
    """IC 95% bootstrap para mean(xs) - mean(ys)."""
    obs = mean(xs) - mean(ys)
    if not xs or not ys:
        return obs, 0.0, 0.0
    diffs = []
    for _ in range(iters):
        a = mean([xs[rng.randrange(len(xs))] for _ in xs])
        b = mean([ys[rng.randrange(len(ys))] for _ in ys])
        diffs.append(a - b)
    diffs.sort()
    lo = diffs[int(0.025 * iters)]
    hi = diffs[min(iters - 1, int(0.975 * iters))]
    return obs, lo, hi


def cliffs_delta(xs, ys):
    """Tamaño de efecto no parametrico en [-1,1]."""
    if not xs or not ys:
        return 0.0
    gt = lt = 0
    for x in xs:
        for y in ys:
            if x > y:
                gt += 1
            elif x < y:
                lt += 1
    return (gt - lt) / (len(xs) * len(ys))
