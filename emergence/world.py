#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
El mundo — objetos, no conceptos.

Aqui NO existe `CONCEPT_ROLES`. El mundo no contiene "agua" ni "fruto":
contiene tipos latentes que generan instancias, y cada instancia es un
punto en un espacio sensorial continuo mas una afordancia oculta (lo que
le pasa a quien la consume) y un lugar (lo que cuesta llegar).

El agente solo ve el vector de rasgos, con ruido. Nunca ve `kind`,
`affordance` ni el nombre de nada. Esos campos existen unicamente para
que NOSOTROS podamos medir desde fuera si sus categorias corresponden a
algo real.

UQBAR
-----
El mundo se carga de un JSON (`worlds/*.json`), no esta cableado en el
codigo. Eso separa la definicion del mundo del mecanismo, permite
versionarlo y hace comparables los experimentos entre mundos.

La linea que ese fichero no cruza: contiene FISICA, no significados.
Vectores sensoriales, afordancias, costes, abundancias. Nunca palabras,
conceptos ni enseñanzas. Meter ahi un inventario de saberes seria repetir
el error de `CONCEPT_ROLES = ["sol", "agua", ...]` con mas ceremonia: lo
que los agentes deben descubrir no se les puede entregar en un fichero.

Diseño intencional del espacio: hay pares CONFUNDIBLES. `fruto_dulce` y
`fruto_amargo` son casi identicos a la vista y solo se separan por olfato
y gusto; `bestia` y `acechante` igual. Un agente de vigilancia gruesa los
mezcla y se envenena. Esa es la presion que empuja la formacion de
conceptos finos, y viene de la supervivencia, no de una funcion objetivo.
"""

import json
import os

import numpy as np

# afordancias: lo que el mundo le hace a quien lo consume
FOOD = "alimento"
WATER = "agua"
TOXIC = "toxico"
PREDATOR = "depredador"
INERT = "inerte"

WORLDS_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "worlds")
DEFAULT_WORLD = "uqbar"


class Kind:
    """Tipo latente. Los agentes no tienen acceso a esto."""

    __slots__ = ("name", "prototype", "spread", "affordance", "payoff",
                 "abundance", "regions")

    def __init__(self, name, prototype, spread, affordance, payoff, abundance,
                 regions=None):
        self.name = name
        self.prototype = np.asarray(prototype, dtype=float)
        self.spread = spread
        self.affordance = affordance
        self.payoff = payoff          # delta de energia al consumir
        self.abundance = abundance    # peso de muestreo
        self.regions = regions        # None = crece en todas partes

    def sample(self, rng):
        return np.clip(self.prototype + rng.noise(len(self.prototype),
                                                  self.spread), 0.0, 1.0)


class Thing:
    """Una instancia concreta percibida en un episodio."""

    __slots__ = ("features", "kind", "affordance", "payoff", "place", "travel")

    def __init__(self, features, kind, place=0, travel=0.0):
        self.features = features
        self.kind = kind                     # solo para metricas
        self.affordance = kind.affordance    # solo para metricas
        self.payoff = kind.payoff            # el agente lo descubre sufriendolo
        self.place = place                   # indice de lugar
        self.travel = travel                 # lo que cuesta llegar


class WorldSpec:
    """Lo que dice el JSON. Fisica pura."""

    def __init__(self, data):
        self.name = data.get("name", "?")
        self.senses = [tuple(s) for s in data["senses"]]
        self.dim = len(self.senses)
        self.places = [(p["name"], float(p["cost"])) for p in data["places"]]
        # Fase 9: coordenadas. Si el mundo no las trae, se colocan en
        # circulo por coste — un mundo viejo sigue cargando.
        import math as _m
        self.coords = []
        for i, p in enumerate(data["places"]):
            if "x" in p and "y" in p:
                self.coords.append((float(p["x"]), float(p["y"])))
            else:
                a = 2 * _m.pi * i / max(1, len(data["places"]))
                r = 0.1 + 0.4 * float(p["cost"]) / 6.0
                self.coords.append((0.5 + r * _m.cos(a), 0.5 + r * _m.sin(a)))
        self.kinds = [Kind(k["name"], k["prototype"], k["spread"],
                           k["affordance"], k["payoff"], k["abundance"],
                           k.get("regions"))
                      for k in data["kinds"]]
        for k in self.kinds:
            if len(k.prototype) != self.dim:
                raise ValueError(
                    f"{self.name}: '{k.name}' tiene {len(k.prototype)} rasgos "
                    f"y el mundo declara {self.dim} sentidos")

    @property
    def n_places(self):
        return len(self.places)


def load_spec(name_or_path=DEFAULT_WORLD):
    path = name_or_path
    if not os.path.isfile(path):
        path = os.path.join(WORLDS_DIR, f"{name_or_path}.json")
    with open(path, encoding="utf-8") as fh:
        return WorldSpec(json.load(fh))


class World:
    def __init__(self, rng, spec=None):
        self.rng = rng
        self.spec = spec if spec is not None else load_spec()
        self.kinds = self.spec.kinds
        self.dim = self.spec.dim
        self.n_places = self.spec.n_places
        self.place_names = [n for n, _ in self.spec.places]
        self.place_costs = [c for _, c in self.spec.places]
        self.coords = np.asarray(self.spec.coords, dtype=float)
        # que puede aparecer en cada region
        self._por_region = []
        for r in range(self.n_places):
            self._por_region.append(
                [k for k in self.kinds
                 if k.affordance != PREDATOR
                 and (k.regions is None or r in k.regions)])
        self._prey = [k for k in self.kinds if k.affordance != PREDATOR]
        self._pred = [k for k in self.kinds if k.affordance == PREDATOR]
        if not self._prey or not self._pred:
            raise ValueError(f"{self.spec.name}: hacen falta presas y depredadores")
        self._prey_w = self._cumulative(self._prey)
        self._spread = None
        self._medio = None
        self._pred_w = self._cumulative(self._pred)

    @staticmethod
    def _cumulative(pool):
        acc, out = 0.0, []
        for k in pool:
            acc += k.abundance
            out.append(acc)
        return out

    def _pick(self, pool, cum):
        r = self.rng.random() * cum[-1]
        for k, upto in zip(pool, cum):
            if r <= upto:
                return k
        return pool[-1]

    def _instance(self, k, pl=None):
        if pl is None:
            pl = self.rng.randrange(self.n_places)
        return Thing(k.sample(self.rng), k, pl, self.place_costs[pl])

    def region_de(self, pos):
        """La region mas cercana a una posicion."""
        d = ((self.coords - pos) ** 2).sum(1)
        return int(d.argmin())

    def sample_thing(self, place=None):
        """Algo que aparece. Si se da region, solo lo que crece alli.

        Ahi esta el reparto del saber: quien no ha pisado el bosque no ha
        visto nunca lo que crece en el bosque.
        """
        if place is None:
            return self._instance(self._pick(self._prey, self._prey_w))
        pool = self._por_region[place]
        if not pool:
            return self._instance(self._pick(self._prey, self._prey_w), place)
        cum = self._cumulative(pool)
        return self._instance(self._pick(pool, cum), place)

    def sample_predator(self):
        return self._instance(self._pick(self._pred, self._pred_w))

    def make(self, kind, place=0, rng=None):
        """Instancia concreta de un tipo en un lugar. Solo para metricas.

        Acepta un `rng` ajeno a proposito: medir no debe consumir el flujo
        aleatorio del mundo, o el acto de observar alteraria la corrida.
        """
        return Thing(kind.sample(self.rng if rng is None else rng), kind,
                     place, self.place_costs[place])

    def probe_set(self, rng, per_kind=12):
        """Bateria fija de estimulos para medir a los agentes desde fuera.

        No forma parte de la simulacion: es nuestro instrumento de medida.
        """
        return [self.make(k, 0, rng) for k in self.kinds
                for _ in range(per_kind)]

    def spread(self, rng):
        """Desviacion tipica por dimension de todo lo que hay en el mundo.

        Se calcula una vez y se guarda: es la vara con la que un agente
        decide si la nube de una palabra es estrecha. No es informacion
        privilegiada — cualquiera que haya visto mucho mundo tiene una
        nocion de cuanta variedad hay — pero calcularla en cada episodio
        seria absurdo.
        """
        if self._spread is None:
            import numpy as np
            xs = [self.make(k, 0, rng).features
                  for k in self.kinds for _ in range(25)]
            X = np.stack(xs)
            self._spread = np.std(X, axis=0)
            self._medio = X.mean(axis=0)
        return self._spread

    def medio(self, rng):
        """El punto medio del mundo. Relleno para lo que no se describe."""
        if self._medio is None:
            self.spread(rng)
        return self._medio

    def separation_report(self):
        """Distancias entre prototipos — util para calibrar la vigilancia."""
        out = []
        for i, a in enumerate(self.kinds):
            for b in self.kinds[i + 1:]:
                out.append((float(np.linalg.norm(a.prototype - b.prototype)),
                            a.name, b.name))
        out.sort()
        return out


if __name__ == "__main__":
    import sys

    from .console import setup
    from .fastrand import FastRandom

    setup()
    w = World(FastRandom(0), load_spec(sys.argv[1] if len(sys.argv) > 1
                                       else DEFAULT_WORLD))
    print(f"mundo '{w.spec.name}': {len(w.kinds)} tipos latentes, "
          f"{w.n_places} lugares, {w.dim} dimensiones sensoriales")
    print("lugares: " + ", ".join(f"{n}({c})" for n, c in w.spec.places))
    print("\npares mas confundibles (distancia entre prototipos):")
    for d, a, b in w.separation_report()[:6]:
        print(f"  {d:.3f}  {a} / {b}")
    print("\npares mas distintos:")
    for d, a, b in w.separation_report()[-3:]:
        print(f"  {d:.3f}  {a} / {b}")
    t = w.sample_thing()
    print("\nuna muestra de lo que percibe un agente (sin etiqueta):")
    print("  " + ", ".join(f"{n}={v:.2f}"
                           for (_, n), v in zip(w.spec.senses, t.features)))
    print(f"  (era: {t.kind.name}, {t.affordance}, en {w.place_names[t.place]}"
          f" — el agente NO ve esta linea)")
