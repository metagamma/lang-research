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
