#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRIBUS, PERCEPCION Y MITOS  —  evolucion de lenguajes anclados en los sentidos.

Idea (de Dante):
  Los agentes PERCIBEN el mundo con cuatro sentidos (vista, olfato, gusto,
  tacto). El mundo tiene "cosas" cuya firma sensorial se genera por entropia.
  Los agentes deben INVENTAR palabras para nombrar lo que perciben y
  comunicarselo entre si (lenguaje anclado en la percepcion).

  La poblacion vive en TRIBUS AISLADAS: dentro de cada tribu la gente se
  comunica y converge a un lexico comun, pero las tribus casi no se hablan
  entre si -> cada una inventa PALABRAS DISTINTAS para las MISMAS cosas.
  Nacen idiomas diferentes para un mismo mundo (como latin -> es/fr/it).

  De la recombinacion azarosa de conceptos surgen SIMBOLOS y MITOS
  (artefactos de entropia): pequeños relatos que ligan cosas y sentidos.
  Los mitos que "resuenan" se cuentan, se adoptan y sobreviven generaciones;
  una palabra muy usada en los mitos se vuelve un SIMBOLO.

Mecanica central: el "naming game" (Steels) -> converge a lexico compartido.

Uso:
    python tribes_perception_myth.py --tribes 3 --tribe-size 30 --generations 20
"""

import random
import argparse
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# FONOLOGIA (para acuñar palabras)
# ---------------------------------------------------------------------------

ONSETS = list("bdfgklmnprstvz") + ["br", "dr", "kr", "tr", "pl", "sl", "vr"]
VOWELS_L = list("aeiou")
ORDER = 2
START, END = "^", "$"
VOWELS = set("aeiou")


def coin(rng):
    n = rng.randint(2, 3)
    w = ""
    for _ in range(n):
        w += rng.choice(ONSETS) + rng.choice(VOWELS_L)
    if rng.random() < 0.4:
        w += rng.choice("nrsl")
    return w


# ---------------------------------------------------------------------------
# EL MUNDO: cosas con firma sensorial generada por ENTROPIA
# ---------------------------------------------------------------------------

SENSES = ["vista", "olfato", "gusto", "tacto"]

SENSORY_PRIMITIVES = {
    "vista":  ["brillante", "oscuro", "rojo", "azul", "verde", "palido"],
    "olfato": ["dulce", "acre", "floral", "podrido", "terroso", "fresco"],
    "gusto":  ["amargo", "dulce", "salado", "acido", "insipido", "picante"],
    "tacto":  ["aspero", "suave", "frio", "calido", "humedo", "punzante"],
}

# conceptos = cosas del mundo (rol semantico + firma sensorial aleatoria)
CONCEPT_ROLES = ["sol", "agua", "fruto", "piedra", "fuego",
                 "flor", "bestia", "noche", "arbol", "sangre"]


def make_world(rng, n_concepts):
    world = {}
    roles = rng.sample(CONCEPT_ROLES, k=min(n_concepts, len(CONCEPT_ROLES)))
    for role in roles:
        sig = {s: rng.choice(SENSORY_PRIMITIVES[s]) for s in SENSES}
        world[role] = sig
    return world


# ---------------------------------------------------------------------------
# AGENTE
# ---------------------------------------------------------------------------

class Agent:
    def __init__(self, rng):
        self.rng = rng
        self.word_for = {}      # concepto(role) -> palabra
        self.myths = Counter()  # mito(texto) -> fuerza

    def name(self, role):
        """Devuelve su palabra para un concepto; la acuña si no tiene."""
        if role not in self.word_for:
            self.word_for[role] = coin(self.rng)
        return self.word_for[role]

    def hear_name(self, role, word):
        """Naming game: alinea su palabra hacia la del hablante."""
        if role not in self.word_for:
            self.word_for[role] = word
        elif self.word_for[role] != word:
            # con cierta prob adopta la del otro (convergencia)
            if self.rng.random() < 0.5:
                self.word_for[role] = word


# ---------------------------------------------------------------------------
# MITOS Y SIMBOLOS (artefactos de entropia)
# ---------------------------------------------------------------------------

MYTH_TEMPLATES = [
    "{a} nacio del {sa} y dio {sb} al {b}",
    "cuando el {a} es {sa}, el {b} despierta",
    "el {a} y el {b} son hermanos de {sc}",
    "quien prueba el {a} {sa} vera el {b}",
    "del {a} {sa} vino el {b} y la {c}",
]


def make_myth(agent, world, rng):
    roles = list(agent.word_for.keys())
    if len(roles) < 2:
        return None
    picks = rng.sample(roles, k=min(3, len(roles)))
    a = picks[0]
    b = picks[1]
    c = picks[2] if len(picks) > 2 else picks[0]
    tmpl = rng.choice(MYTH_TEMPLATES)
    # los mitos usan las PALABRAS del agente + rasgos SENSORIALES del mundo
    text = tmpl.format(
        a=agent.name(a), b=agent.name(b), c=agent.name(c),
        sa=world[a][rng.choice(SENSES)],
        sb=world[b][rng.choice(SENSES)],
        sc=world[c][rng.choice(SENSES)],
    )
    return text


# ---------------------------------------------------------------------------
# SIMULACION
# ---------------------------------------------------------------------------

def run(n_tribes, tribe_size, generations, n_concepts, contact, seed):
    rng = random.Random(seed)
    world = make_world(rng, n_concepts)

    print("EL MUNDO (firmas sensoriales generadas por entropia):")
    for role, sig in world.items():
        desc = ", ".join(f"{s}:{v}" for s, v in sig.items())
        print(f"  {role:<8} -> {desc}")
    print()

    # crear tribus aisladas
    tribes = [[Agent(rng) for _ in range(tribe_size)] for _ in range(n_tribes)]
    myth_origin = {}   # mito -> generacion de nacimiento

    for gen in range(1, generations + 1):
        for ti, tribe in enumerate(tribes):
            # --- naming game dentro de la tribu (percepcion -> palabra) ---
            for _ in range(tribe_size * 6):
                a, b = rng.sample(tribe, 2)
                role = rng.choice(list(world.keys()))   # ambos perciben la cosa
                w = a.name(role)
                b.hear_name(role, w)

            # --- creacion y difusion de mitos ---
            for _ in range(max(2, tribe_size // 10)):
                teller = rng.choice(tribe)
                myth = make_myth(teller, world, rng)
                if not myth:
                    continue
                teller.myths[myth] += 1
                if myth not in myth_origin:
                    myth_origin[myth] = gen
                # se lo cuenta a algunos; si resuena, lo adoptan
                for listener in rng.sample(tribe, k=min(5, tribe_size)):
                    if rng.random() < 0.6:
                        listener.myths[myth] += 1

        # --- contacto raro entre tribus (prestamo de palabras) ---
        if contact > 0 and n_tribes > 1:
            for _ in range(contact):
                t1, t2 = rng.sample(range(n_tribes), 2)
                a = rng.choice(tribes[t1])
                b = rng.choice(tribes[t2])
                role = rng.choice(list(world.keys()))
                b.hear_name(role, a.name(role))

        # --- muerte y reproduccion dentro de cada tribu ---
        for ti, tribe in enumerate(tribes):
            # fitness = cuanto coincide su lexico con el de la tribu (comunicar bien)
            consensus = {}
            for role in world:
                votes = Counter(ag.word_for.get(role) for ag in tribe
                                if role in ag.word_for)
                if votes:
                    consensus[role] = votes.most_common(1)[0][0]
            def fitness(ag):
                return sum(1 for r, w in ag.word_for.items()
                           if consensus.get(r) == w)
            tribe.sort(key=fitness, reverse=True)
            survivors = tribe[:tribe_size // 2]
            children = []
            while len(survivors) + len(children) < tribe_size:
                p1, p2 = rng.sample(survivors, 2)
                child = Agent(rng)
                # hereda lexico de los padres (con mutacion ocasional)
                for role in world:
                    src = p1 if rng.random() < 0.5 else p2
                    if role in src.word_for:
                        if rng.random() < 0.08:            # mutacion: nueva palabra
                            child.word_for[role] = coin(rng)
                            myth_origin.setdefault(f"__w_{child.word_for[role]}", gen)
                        else:
                            child.word_for[role] = src.word_for[role]
                # hereda algunos mitos
                pool = list(p1.myths) + list(p2.myths)
                for m in rng.sample(pool, k=min(3, len(pool))) if pool else []:
                    child.myths[m] += 1
                children.append(child)
            tribes[ti] = survivors + children

    # ---------------------------------------------------------------------
    # RESULTADOS
    # ---------------------------------------------------------------------
    print("=" * 68)
    print("LENGUAJES EMERGENTES: como nombra cada tribu las mismas cosas")
    print("=" * 68)
    header = "  concepto  | " + " | ".join(f"Tribu {i+1}" for i in range(n_tribes))
    print(header)
    print("  " + "-" * (len(header)))
    for role in world:
        cols = []
        for tribe in tribes:
            votes = Counter(ag.word_for.get(role) for ag in tribe
                            if role in ag.word_for)
            word = votes.most_common(1)[0][0] if votes else "???"
            cols.append(f"{word:<8}")
        print(f"  {role:<10}| " + " | ".join(cols))

    print("\n" + "=" * 68)
    print("MITOS SUPERVIVIENTES por tribu (los mas contados)")
    print("=" * 68)
    for ti, tribe in enumerate(tribes):
        allm = Counter()
        for ag in tribe:
            allm.update(ag.myths)
        print(f"\n  --- Tribu {ti+1} ---")
        if not allm:
            print("    (sin mitos)")
        for myth, strength in allm.most_common(3):
            age = generations - myth_origin.get(myth, generations)
            print(f"    \"{myth}\"")
            print(f"       (contado x{strength}, edad {age} gen)")

    print("\n" + "=" * 68)
    print("SIMBOLOS: palabras que dominan los mitos de cada tribu")
    print("=" * 68)
    for ti, tribe in enumerate(tribes):
        wordcount = Counter()
        for ag in tribe:
            for myth in ag.myths:
                for tok in myth.split():
                    wordcount[tok] += 1
        # cruzar con el lexico para saber que concepto es
        lex = {}
        for role in world:
            votes = Counter(ag.word_for.get(role) for ag in tribe if role in ag.word_for)
            if votes:
                lex[votes.most_common(1)[0][0]] = role
        top = [(w, c) for w, c in wordcount.most_common(20) if w in lex][:2]
        if top:
            for w, c in top:
                print(f"  Tribu {ti+1}: '{w}' (= {lex[w]}) se volvio simbolo "
                      f"central de sus mitos")
        else:
            print(f"  Tribu {ti+1}: aun sin simbolo dominante")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tribes", type=int, default=3)
    ap.add_argument("--tribe-size", type=int, default=30)
    ap.add_argument("--generations", type=int, default=20)
    ap.add_argument("--concepts", type=int, default=7)
    ap.add_argument("--contact", type=int, default=0,
                    help="prestamos entre tribus por gen (0 = aisladas)")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    run(args.tribes, args.tribe_size, args.generations,
        args.concepts, args.contact, args.seed)


if __name__ == "__main__":
    main()
