#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 1 — los conceptos emergen.

Cada agente mantiene SU PROPIA particion del espacio sensorial. No hay
una lista de conceptos compartida en ningun sitio del programa: un
concepto es un prototipo dentro de la cabeza de un agente concreto.

Consecuencia importante: dos agentes de la misma tribu no tienen las
mismas categorias. Cuando uno dice una forma, el otro la asocia a SU
categoria, que puede no coincidir. El problema referencial es real.

Algoritmo: clustering incremental con vigilancia (familia ART), con dos
detalles que importan.

1. RADIO POR CATEGORIA. No hay un unico umbral global: cada categoria
   lleva el suyo. Empiezan todos en el valor del gen `vigilance`.

2. MATCH TRACKING. Cuando el agente descubre que una categoria mezcla
   cosas que se comportan distinto (comio dos veces lo "mismo" y una le
   alimento y la otra le envenenó), esa categoria ENCOGE su radio y nace
   una categoria nueva sobre el ejemplo discrepante.

   Sin el encogimiento, partir no sirve de nada: el prototipo viejo se
   queda en medio de las dos realidades y vuelve a capturarlas a las dos
   en el siguiente encuentro. Era el fallo que mantenia a los agentes
   confundiendo el fruto dulce con el amargo indefinidamente.

Resultado: la particion se afila SOLO donde el mundo castiga no
distinguir, y se queda gruesa donde da igual. Nadie le dice al agente
cuantas categorias debe tener ni donde estan las fronteras.

La vigilancia inicial es un GEN heredable (ver agent.py). Lo que
evoluciona por seleccion natural no es el idioma sino la resolucion
perceptiva de partida: la facultad, no la lengua.
"""

import math

import numpy as np


class ConceptSpace:
    """Particion del espacio sensorial de UN agente.

    Los prototipos viven en una matriz preasignada (max_categorias x DIM)
    y cada categoria es una FILA de esa matriz. Asi la distancia a todas
    se calcula de una vez, en vez de una llamada por prototipo, y como las
    filas son vistas, moverlas al asimilar actualiza la matriz sin copiar
    nada. El coste deja de crecer linealmente con el numero de conceptos,
    que es lo que empezaba a doler con mundos grandes.
    """

    def __init__(self, vigilance, lr, rng, max_categories=40,
                 radius_min=0.12, dim=9):
        self.vigilance = vigilance
        self.lr = lr
        self.rng = rng
        self.max_categories = max_categories
        self.radius_min = radius_min
        self.dim = dim
        self._P = np.zeros((max_categories, self.dim))   # prototipos
        self._R = np.zeros(max_categories)               # radios
        self._R2 = np.zeros(max_categories)              # radios al cuadrado
        self.n = 0
        self.counts = []
        self.provisional = set()   # nacidas de una descripcion

    # -- vistas comodas -------------------------------------------------
    @property
    def protos(self):
        return self._P[:self.n]

    @property
    def radii(self):
        return self._R[:self.n]

    # -- consulta -------------------------------------------------------
    def _sqdists(self, x):
        """Distancias AL CUADRADO a todos los prototipos.

        Se trabaja en cuadrados a proposito: comparar contra radios al
        cuadrado da el mismo orden y ahorra una raiz por prototipo en el
        camino mas caliente del modelo. `einsum` hace la suma de productos
        en una pasada, sin materializar la matriz de diferencias al
        cuadrado. La raiz solo se paga cuando alguien pide la distancia de
        verdad, que es raro.
        """
        diff = self._P[:self.n] - x
        return np.einsum("ij,ij->i", diff, diff)

    def _match(self, x):
        """Categoria que ACEPTA x (la mas cercana de las que llegan)."""
        if self.n == 0:
            return None, float("inf")
        d2 = self._sqdists(x)
        ok = d2 <= self._R2[:self.n]
        if not ok.any():
            return None, float(np.sqrt(d2.min()))
        dd = np.where(ok, d2, np.inf)
        i = int(dd.argmin())
        return i, float(np.sqrt(dd[i]))

    def nearest(self, x):
        """La mas cercana, acepte o no. Para diagnostico."""
        if self.n == 0:
            return None, float("inf")
        d2 = self._sqdists(x)
        i = int(d2.argmin())
        return i, float(np.sqrt(d2[i]))

    def classify(self, x):
        """Categoriza SIN aprender. None si nada la acepta.

        Se usa solo para medir (metrics.py), nunca dentro de la simulacion.
        """
        i, _ = self._match(x)
        return i

    def classify_many(self, X):
        """Como `classify` pero para una matriz (m, dim) de estimulos.

        Medir implica clasificar cientos de sondas por agente. Hacerlo de
        una en una era el gasto principal de la instrumentacion — mas caro
        que la simulacion que pretendia observar. Aqui las distancias
        salen de un solo producto de matrices:

            |x - p|^2  =  |x|^2  - 2 x.p  +  |p|^2

        Tampoco aprende nada, igual que `classify`.
        """
        n = self.n
        m = len(X)
        if n == 0 or m == 0:
            return [None] * m
        P = self._P[:n]
        d2 = ((X * X).sum(1)[:, None] - 2.0 * (X @ P.T)
              + (P * P).sum(1)[None, :])
        dd = np.where(d2 <= self._R2[:n], d2, np.inf)
        idx = dd.argmin(1)
        hit = np.isfinite(dd[np.arange(m), idx])
        return [int(i) if h else None for i, h in zip(idx, hit)]

    # -- aprendizaje ----------------------------------------------------
    def categorize(self, x):
        """Categoriza y aprende. Siempre devuelve una categoria."""
        i, _ = self._match(x)
        if i is None:
            if self.n < self.max_categories:
                return self._new(x, self.vigilance)
            i, _ = self.nearest(x)      # techo cognitivo: asimila a la fuerza
        self._assimilate(i, x)
        return i

    def _new(self, x, radius):
        i = self.n
        self._P[i] = x
        r = max(self.radius_min, radius)
        self._R[i] = r
        self._R2[i] = r * r
        self.counts.append(1)
        self.n += 1
        return i

    def _set_radius(self, i, r):
        r = max(self.radius_min, r)
        self._R[i] = r
        self._R2[i] = r * r

    def _assimilate(self, i, x):
        self._P[i] += self.lr * (x - self._P[i])
        self.counts[i] += 1

    def split(self, x, blame):
        """`blame` mezclaba dos realidades. Traza la frontera y abre una nueva.

        Regla del punto medio: la frontera cae a mitad de camino entre el
        prototipo culpable y el ejemplo que lo desmintio. Ni mas ni menos.

        Es autolimitada, y esa es la gracia: en cuanto los dos conceptos
        quedan separados dejan de darse sorpresas mutuas y los radios se
        estabilizan. Un factor de encogimiento fijo, en cambio, seguia
        recortando en cada sorpresa y acababa pulverizando la particion en
        decenas de categorias diminutas, cada una con demasiado pocos datos
        para estimar su valor. La tribu entera se extinguia por eso.

        Lo dispara el daño recibido (agent.learn_value), no una instruccion
        externa ni un objetivo de clasificacion.
        """
        if blame is None or not (0 <= blame < self.n):
            return self._new(x, self.vigilance)

        d = float(np.linalg.norm(x - self._P[blame]))
        half = max(self.radius_min, d * 0.5)
        self._set_radius(blame, min(float(self._R[blame]), half))
        if self.n >= self.max_categories:
            return self.categorize(x)
        return self._new(x, min(self.vigilance, half))

    def install_described(self, constraints, relleno, radius):
        """Crear una categoria a partir de una DESCRIPCION, sin haberla visto.

        Las dimensiones que la descripcion fija van a su valor; las que no
        menciona van al valor medio del mundo, que es lo unico razonable
        cuando no se dice nada de ellas. El radio nace ancho porque el
        concepto esta infra-especificado: se ha oido una descripcion, no
        se ha visto una cosa.

        Nace PROVISIONAL. Un concepto que llega por el oido es una
        hipotesis perceptiva, no un hecho: si el mundo nunca le presenta
        nada que encaje, se descarta. Sin esa condicion, el lenguaje
        podria instalar creencias arbitrarias en cabezas ajenas y
        habriamos roto justo la disciplina que hace creible todo lo demas.
        """
        if self.n >= self.max_categories:
            return None
        x = np.array(relleno, dtype=float)
        for d, v in constraints.items():
            if 0 <= d < self.dim:
                x[d] = v
        i = self._new(x, radius)
        self.provisional.add(i)
        return i

    def confirm(self, i):
        """El mundo presento algo que encaja: deja de ser una hipotesis."""
        self.provisional.discard(i)

    def nearest_among(self, cat, candidates, max_dist):
        """El vecino conceptual mas cercano a `cat`, dentro de `max_dist`.

        Base de la extension metaforica (Fase 4): para nombrar algo que aun
        no tiene nombre, el agente mira que concepto SUYO se le parece mas
        y del que ya sepa hablar. La similitud es la del espacio sensorial,
        que es la unica que el agente puede percibir.
        """
        if not (0 <= cat < self.n):
            return None, float("inf")
        cand = [c for c in candidates if c != cat and 0 <= c < self.n]
        if not cand:
            return None, float("inf")
        idx = np.fromiter(cand, dtype=int, count=len(cand))
        d = np.sqrt(((self._P[idx] - self._P[cat]) ** 2).sum(1))
        j = int(d.argmin())
        return (int(idx[j]), float(d[j])) if d[j] <= max_dist else (None, float(d[j]))

    # -- introspeccion --------------------------------------------------
    def __len__(self):
        return self.n

    def mean_radius(self):
        return float(self._R[:self.n].mean()) if self.n else 0.0

    def alive(self, min_count=2):
        return [i for i, c in enumerate(self.counts) if c >= min_count]
