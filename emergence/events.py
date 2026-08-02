#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 6 — sucesos: predicados, participantes y tiempo.

Hasta aqui solo existia un acto de habla: «hay X en L». Con eso se puede
tener lexico y morfologia, pero no sintaxis, porque nunca hay dos cosas
que ordenar. Un idioma de etiquetas referenciales no es un idioma.

Un SUCESO tiene la forma

    (accion, participante1, participante2, lugar, tiempo)

y de ahi salen tres propiedades que antes eran imposibles:

SINTAXIS
    Con dos participantes del mismo tipo, el orden tiene que cargar con
    el papel de cada uno. «el acechante mato a la gente» y «la gente mato
    al acechante» usan las MISMAS piezas y significan cosas opuestas. Si
    el orden no significara nada, la señal seria ambigua y costaria vidas.

DESPLAZAMIENTO
    Un suceso ocurrio en una generacion concreta. Contarlo despues es
    hablar de algo que el oyente no esta viendo y quiza no vio nunca.
    Ahi empieza a ser posible que el conocimiento sobreviva a quien lo
    adquirio.

PRODUCTIVIDAD
    |acciones| x |categorias|^2 x |lugares| x |tiempos| son decenas de
    miles de significados a partir de unas pocas decenas de morfos. El
    espacio deja de ser memorizable por construccion, no por un tope que
    le hayamos puesto nosotros.

Lo que NO se da hecho: las acciones no llevan nombre. Un agente percibe
que algo ha pasado y categoriza a los participantes con SU particion; la
palabra para «comio» tiene que emerger igual que la palabra para «fruto».
"""

from collections import deque

# --- acciones: lo que puede pasar en el mundo -------------------------
# Son tipos de suceso, no palabras. El agente los distingue porque tienen
# consecuencias distintas, igual que distingue el fruto dulce del amargo.
HAY = 0      # existe algo en un sitio
COMIO = 1    # alguien se alimento de algo
DAÑO = 2     # algo hizo daño al ser comido
MATO = 3     # algo acabo con alguien
DIJO = 4     # alguien conto ESTO -> su argumento es OTRO SUCESO (Fase 7)
ACTIONS = (HAY, COMIO, DAÑO, MATO, DIJO)
ACTION_NAME = {HAY: "hay", COMIO: "comio", DAÑO: "daño", MATO: "mato",
               DIJO: "dijo"}
ARITY = {HAY: 1, COMIO: 1, DAÑO: 1, MATO: 1, DIJO: 1}

# DIJO es la unica accion cuyo argumento no es una categoria sino un
# suceso entero. Ahi esta la recursividad: la misma estructura dentro de
# si misma, y sin tope teorico — «dijo que dijo que hay fruto».
#
# Y no es un adorno gramatical: sirve para algo. Sin ella, un agente que
# aprende algo de oidas y luego lo recuenta lo presenta como propio, y el
# rumor se amplifica sin control. Con ella se puede marcar la diferencia
# entre lo que uno vio y lo que a uno le contaron, y descontar lo segundo.

# Por que COMIO y DAÑO son sucesos DISTINTOS y no uno con dos desenlaces:
# porque un testigo los distingue mirando. Ve a alguien comer y seguir
# tan campante, o ve a alguien comer y doblarse de dolor. Son dos cosas
# distintas que pasan en el mundo, y el agente las individua por su
# consecuencia observable — exactamente igual que individua el fruto
# dulce del amargo.
#
# Meterlos en un solo suceso «comio» era lo que rompia el testimonio: el
# valor asociado promediaba banquetes con envenenamientos y salia -0.1,
# o sea nada. Un relato que no distingue esas dos cosas no informa.

# --- tiempo -----------------------------------------------------------
NOW = 0
BEFORE = 1
TENSE_NAME = {NOW: "ahora", BEFORE: "antes"}
TENSES = (NOW, BEFORE)


class Event:
    """Un suceso tal como lo puede percibir un testigo.

    Guarda las COSAS, no categorias: cada testigo las categorizara con su
    propia particion, y dos testigos pueden discrepar. Eso es deliberado —
    es el mismo problema referencial de siempre, ahora con papeles.
    """

    __slots__ = ("action", "t1", "t2", "place", "gen")

    def __init__(self, action, t1, t2, place, gen):
        self.action = action
        self.t1 = t1          # Thing o None
        self.t2 = t2          # Thing o None
        self.place = place
        self.gen = gen

    def __repr__(self):
        a = self.t1.kind.name if self.t1 else "-"
        b = self.t2.kind.name if self.t2 else "-"
        return f"<{ACTION_NAME[self.action]} {a} {b} @{self.place} g{self.gen}>"


class Memory:
    """Memoria episodica, en DOS compartimentos: lo vivido y lo contado.

    No es un refinamiento cosmetico. Con un solo saco, cada episodio deja
    un recuerdo propio y el testimonio ajeno queda enterrado: al recordar
    algo salia de oidas 1 de cada 25 veces, y el discurso referido no
    llegaba nunca a repetirse lo suficiente como para que la tribu
    aprendiera a marcarlo.

    Separarlos tambien es lo correcto: lo que uno vio y lo que a uno le
    contaron no son la misma clase de saber, y de hecho el modelo ya los
    trata distinto al aprender (`testimony_lr` < `value_lr`). Que
    compartieran almacen era la incoherencia.

    Ambos compartimentos estan acotados: nadie recuerda su vida entera, y
    ese olvido es lo que hace que contar las cosas sirva para algo.
    """

    def __init__(self, capacity):
        self.lived = deque(maxlen=capacity)
        self.told = deque(maxlen=max(4, capacity // 3))

    @property
    def items(self):
        return list(self.lived) + list(self.told)

    def add(self, action, c1, c2, place, gen, hearsay=False):
        (self.told if hearsay else self.lived).append(
            (action, c1, c2, place, gen, hearsay))

    def recall(self, rng, gen, min_age=1):
        """Un suceso del pasado. None si no hay ninguno bastante viejo.

        Se sortea primero de que compartimento se tira. Lo contado pesa
        menos que lo vivido — uno habla sobre todo de lo suyo — pero deja
        de ser invisible.
        """
        cajas = []
        for caja, peso in ((self.lived, 2.0), (self.told, 1.0)):
            viejos = [e for e in caja if gen - e[4] >= min_age]
            if viejos:
                cajas.append((viejos, peso))
        if not cajas:
            return None
        total = sum(w for _, w in cajas)
        r = rng.random() * total
        acc = 0.0
        for viejos, w in cajas:
            acc += w
            if r <= acc:
                return rng.choice(viejos)
        return rng.choice(cajas[-1][0])

    def __len__(self):
        return len(self.lived) + len(self.told)


def meaning(action, c1, c2, place, tense):
    """El significado que una señal debe transportar."""
    return (action, c1, c2, place, tense)


def tense_of(gen_now, gen_event):
    return NOW if gen_now == gen_event else BEFORE
