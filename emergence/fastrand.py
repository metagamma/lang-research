#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aleatoriedad rapida para lo unico que se pide a granel: ruido sensorial.

Cada percepcion necesita un vector gaussiano de tantas componentes como
dimensiones tenga el mundo. Pedirlos de uno en uno con `random.gauss`
salia a mas de un millon de llamadas por corrida y era, con diferencia,
lo mas caro del modelo.

`FastRandom` es un `random.Random` normal — todo el codigo que hace
`rng.sample`, `rng.choice` o `rng.random` sigue funcionando igual — al que
se le añade `noise()`, que sirve vectores gaussianos de un deposito
generado por numpy en bloques grandes.

Reproducibilidad: el deposito sale de un `default_rng` derivado de la
misma semilla por `SeedSequence`, deterministicamente. No se usa `hash()`
en ningun sitio, porque en Python el hash de las cadenas cambia entre
procesos y arruinaria la reproducibilidad sin avisar.

Aviso: al cambiar de donde salen los numeros, las corridas NO coinciden
con las de antes de esta optimizacion aunque se use la misma semilla.
Siguen siendo deterministicas; simplemente son otra realizacion.
"""

import random

import numpy as np

POOL = 1 << 16


class FastRandom(random.Random):
    def __init__(self, seed=None):
        super().__init__(seed)
        self._gen = np.random.default_rng([0 if seed is None else int(seed),
                                           0x9E3779B9])
        self._pool = self._gen.standard_normal(POOL)
        self._at = 0

    def noise(self, n, sigma):
        """Vector de n gaussianas N(0, sigma)."""
        if self._at + n > POOL:
            self._pool = self._gen.standard_normal(POOL)
            self._at = 0
        out = self._pool[self._at:self._at + n] * sigma
        self._at += n
        return out

    # random.Random hace copias en getstate/setstate; no las usamos, pero
    # dejarlo explicito evita sorpresas si alguien intenta serializar.
    def __reduce__(self):
        raise TypeError("FastRandom no es serializable")
