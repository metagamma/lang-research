#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
La consola de Windows llega en cp1252 por defecto y revienta con los
acentos y los bloques del sparkline. Esto lo arregla una vez, en el
arranque de los dos puntos de entrada.
"""

import sys

# rampa de densidad; toda ella ASCII, se ve igual en cualquier terminal
RAMP = " .:-=+*#%@"


def setup():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass    # entorno sin consola reconfigurable: seguimos igual


def bar(value, lo, hi, ramp=RAMP):
    span = (hi - lo) or 1.0
    i = int((value - lo) / span * (len(ramp) - 1))
    return ramp[max(0, min(len(ramp) - 1, i))]
