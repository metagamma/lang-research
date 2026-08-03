#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fonologia — acuñacion de formas.

Por ahora las formas son ATOMOS: cadenas opacas sin estructura interna.
Eso es deliberado. La composicionalidad no se programa aqui; tiene que
emerger en la Fase 5 (cuello de botella de transmision), y para poder
afirmar que emergio hay que partir de un sistema donde no existe.
"""

ONSETS = list("bdfgklmnprstvz") + ["br", "dr", "kr", "tr", "pl", "sl", "vr"]
NUCLEI = list("aeiou")
CODAS = list("nrsl")


def coin(rng, lo=1, hi=2):
    """Acuña una forma nueva, sin relacion con nada.

    Una o dos silabas por defecto. Antes eran dos o tres, y con cinco
    ranuras por enunciado salian señales de cuarenta caracteres: absurdas
    como palabra y carisimas de analizar, porque segmentar cuesta el
    cuadrado de la longitud. Los morfemas reales son cortos justamente
    porque se combinan.
    """
    w = ""
    for _ in range(rng.randint(lo, hi)):
        w += rng.choice(ONSETS) + rng.choice(NUCLEI)
    if rng.random() < 0.35:
        w += rng.choice(CODAS)
    return w


# --- cambio fonico (Fase 13) ------------------------------------------
#
# Las lenguas reales no solo cambian de palabra: cambian de SONIDO, y de
# forma sistematica. La lenicion —una oclusiva entre vocales se ablanda—
# ocurre en latin > castellano (vita > vida), en celta, en japones. No es
# que cada hablante deforme al azar: es que TODA la comunidad aplica la
# misma regla, y por eso la lengua sigue siendo mutuamente inteligible
# mientras deriva.
#
# Eso es lo que se modela aqui, y la distincion importa: un ruido por
# hablante rompe la lengua; una regla compartida la desplaza entera.

LENICION = {"p": "b", "t": "d", "k": "g", "b": "v", "d": "r", "g": "",
            "s": "z", "f": "v"}


def deriva(forma, rng, fuerza):
    """Aplica cambio fonico a una forma. Devuelve la forma nueva.

    Solo entre vocales, que es donde la lenicion ocurre de verdad: una
    consonante en posicion fuerte (inicio de palabra) resiste. Y una sola
    consonante por aplicacion, porque los cambios en cadena no ocurren de
    golpe.
    """
    if len(forma) < 3 or rng.random() >= fuerza:
        return forma
    sitios = [i for i in range(1, len(forma) - 1)
              if forma[i] in LENICION
              and forma[i - 1] in NUCLEI and forma[i + 1] in NUCLEI]
    if not sitios:
        return forma
    i = rng.choice(sitios)
    nueva = forma[:i] + LENICION[forma[i]] + forma[i + 1:]
    return nueva if len(nueva) >= 2 else forma
