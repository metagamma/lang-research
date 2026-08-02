#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 5 — composicionalidad por cuello de botella de transmision.

El significado ya tiene partes: (categoria, lugar). La pregunta es si la
SEÑAL acaba teniendo partes tambien, y eso no se programa.

Cada agente guarda tres almacenes, los tres con la misma maquinaria de
pesos e inhibicion lateral de la Fase 3:

    hol    cadena  <->  (categoria, lugar)      señal entera, opaca
    cat    morfo   <->  categoria               trozo que dice QUE es
    place  morfo   <->  lugar                   trozo que dice DONDE esta

Al nacer, un agente solo puede guardar cadenas enteras: para el, una
señal es un bloque sin costuras. Los almacenes de morfos empiezan vacios
y solo se llenan por INDUCCION (`_chunk`), comparando pares que ha oido:

    "vrataku" = (fruto, valle)
    "vratalen" = (fruto, loma)
     ^^^^^ prefijo comun -> quiza "vrata" signifique fruto
           y "ku"/"len" sean los lugares

Nadie le dice donde estan las fronteras. Las tiene que encontrar
alineando lo que oyo. Un agente que nunca las encuentre sigue siendo
perfectamente viable: hablara holisticamente y punto.

POR QUE EMERGE (o no)
---------------------
El espacio de significados es |categorias| x 4 lugares. Ningun agente
llega a oir todas las combinaciones: se muere antes. Ese es el cuello de
botella, y no hay que fabricarlo — sale solo de que la vida es corta y
el mundo grande.

Cuando a un hablante le toca nombrar una combinacion que nunca ha oido:

  * si solo tiene señales enteras, no tiene nada que decir y se inventa
    una cadena que el oyente jamas ha escuchado -> no se entiende.
  * si ha inducido morfos, construye la señal juntando piezas que el
    oyente YA conoce por separado -> se entiende a la primera.

La composicionalidad no gana porque la premiemos: gana porque generaliza
a lo que no se ha visto, y lo que no se ha visto es la mayor parte.

LO QUE SI LE DAMOS (y hay que decirlo)
--------------------------------------
El ORDEN esta fijado: el morfo de categoria va delante y el de lugar
detras. Que el orden de las palabras tambien emerja es otro problema, y
no lo hemos resuelto aqui. La afirmacion que sostiene este modulo es mas
estrecha: emerge la SEGMENTACION de la señal en partes con significado
propio, no su sintaxis.

Tambien le damos la capacidad de alinear cadenas y quedarse con prefijos
y sufijos comunes. Es una capacidad general de deteccion de regularidad,
no una regla lingüistica: no sabe que son palabras ni que son morfemas.
"""

from .lexicon import Lexicon
from .phonology import coin

HOLISTIC = "hol"
COMPOSED = "comp"
PARTIAL = "part"


def _common_prefix(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return a[:n]


def _common_suffix(a, b):
    n = 0
    for x, y in zip(reversed(a), reversed(b)):
        if x != y:
            break
        n += 1
    return a[len(a) - n:] if n else ""


class Grammar:
    def __init__(self, cfg, rng):
        self.cfg = cfg
        self.rng = rng
        self.hol = Lexicon(cfg, rng)      # cadena <-> (cat, lugar)
        self.cat = Lexicon(cfg, rng)      # morfo  <-> cat
        self.place = Lexicon(cfg, rng)    # morfo  <-> lugar
        self.heard = []                   # [(cadena, cat, lugar)] muestra reciente
        self.produced = {HOLISTIC: 0, COMPOSED: 0}

    # -- produccion ----------------------------------------------------
    def express(self, cat, place):
        """(cadena, modo) o (None, None). NO cuenta: sirve para medir.

        Prueba PRIMERO la señal entera. Es la opcion conservadora: la
        composicion solo entra cuando la memoria holistica no cubre el
        caso, que es exactamente el hueco donde puede demostrar que sirve
        para algo. Si empezaramos por componer, la composicionalidad
        ganaria por decreto nuestro y no por merito suyo.
        """
        whole = self.hol.produce((cat, place))
        if whole is not None and self.hol.w[(whole, (cat, place))] >= self.cfg.lex_confidence:
            return whole, HOLISTIC
        mc = self.cat.produce(cat)
        mp = self.place.produce(place)
        if mc and mp:
            return mc + mp, COMPOSED
        return (whole, HOLISTIC) if whole is not None else (None, None)

    def produce(self, cat, place):
        """Como `express`, pero contabilizando lo que se dijo de verdad."""
        s, mode = self.express(cat, place)
        if mode:
            self.produced[mode] += 1
        return s, mode

    def invent(self, cat, place):
        """Nada que decir: hay que crear. Componiendo o de una pieza.

        Si ya tiene alguno de los dos morfos, lo reutiliza e inventa solo
        el que falta. Si no tiene ninguno, `p_compose` decide si estrena
        una gramatica o suelta un bloque opaco.
        """
        mc = self.cat.produce(cat)
        mp = self.place.produce(place)
        if mc or mp or self.rng.random() < self.cfg.p_compose:
            mc = mc or self.cat.invent(cat)
            mp = mp or self.place.invent(place)
            self.produced[COMPOSED] += 1
            return mc + mp, COMPOSED
        form = coin(self.rng)
        self.hol._set(form, (cat, place), self.cfg.lex_init_w)
        self.produced[HOLISTIC] += 1
        return form, HOLISTIC

    # -- comprension ---------------------------------------------------
    def parse(self, s):
        """(cat, lugar, modo). Cualquiera de los dos puede ser None.

        Devolver (cat, None) no es un fallo: es media señal entendida, y
        con media señal ya se puede decidir mejor que a ciegas. Ese
        entendimiento parcial es la ventaja concreta de tener partes.
        """
        m = self.hol.interpret(s)
        if m is not None:
            return m[0], m[1], HOLISTIC

        # En vez de recorrer TODOS los morfos conocidos preguntando si son
        # prefijo de `s`, recorremos los prefijos de `s` preguntando si son
        # morfos conocidos. El conjunto de cortes considerados es el mismo,
        # pero el coste pasa de O(morfos) a O(longitud de la señal): deja
        # de crecer cuando crece el vocabulario. Con un mundo grande esa
        # diferencia es la que decide si el modelo es medible o no.
        best, bw = None, 0.0
        cat_forms, place_forms = self.cat.by_form, self.place.by_form
        for cut in range(self.cfg.morph_min, len(s) + 1):
            morph = s[:cut]
            if morph not in cat_forms:
                continue
            c = self.cat.interpret(morph)
            if c is None:
                continue
            rest = s[cut:]
            wc = self.cat.w[(morph, c)]
            p = self.place.interpret(rest) if rest in place_forms else None
            if p is not None:
                w = wc + self.place.w[(rest, p)]
                if w > bw:
                    best, bw = (c, p, COMPOSED), w
            elif wc > bw and best is None:
                best, bw = (c, None, PARTIAL), wc
        return best if best else (None, None, None)

    # -- aprendizaje ---------------------------------------------------
    def observe(self, s, cat, place):
        """Co-observacion: oi `s` y luego vi que era (cat, lugar)."""
        self.hol.reward(s, (cat, place))
        self.heard.append((s, cat, place))
        if len(self.heard) > self.cfg.grammar_memory:
            self.heard.pop(0)
        self._chunk(s, cat, place)
        # EL CUELLO DE BOTELLA. La memoria de señales enteras es finita:
        # cuando se llena, lo mas flojo se olvida. Los morfos inducidos NO
        # se tocan, porque son pocos y sirven para todo. Ahi esta la
        # asimetria que puede favorecer a una gramatica sobre una lista.
        if self.cfg.hol_capacity > 0:
            self.hol.trim(self.cfg.hol_capacity)

    def _chunk(self, s, cat, place):
        """Induccion: buscar la costura comparando con lo ya oido.

        Solo mira pares que difieren en UN atributo. Si dos señales
        hablan de la misma cosa en sitios distintos, lo que comparten al
        principio es candidato a nombrar la cosa; lo que las diferencia
        al final, a nombrar el sitio. Y simetricamente.

        No hay ninguna nocion de morfema aqui dentro. Es deteccion de
        regularidad sobre cadenas.
        """
        lo = self.cfg.morph_min
        n = hits = 0
        for (s2, c2, p2) in reversed(self.heard):
            n += 1
            if n > self.cfg.chunk_window:
                break
            if s2 == s:
                continue
            if c2 == cat and p2 != place:
                pre = _common_prefix(s, s2)
                if len(pre) >= lo and len(s) - len(pre) >= lo and len(s2) - len(pre) >= lo:
                    self.cat.reward(pre, cat)
                    self.place.reward(s[len(pre):], place)
                    self.place.reward(s2[len(pre):], p2)
                    hits += 1
            elif p2 == place and c2 != cat:
                suf = _common_suffix(s, s2)
                if len(suf) >= lo and len(s) - len(suf) >= lo and len(s2) - len(suf) >= lo:
                    self.place.reward(suf, place)
                    self.cat.reward(s[:len(s) - len(suf)], cat)
                    self.cat.reward(s2[:len(s2) - len(suf)], c2)
                    hits += 1
            # Basta con unas pocas confirmaciones por señal oida. Antes se
            # re-derivaba la misma frontera desde toda la memoria en cada
            # co-observacion: mucho trabajo repetido y, peor, la inhibicion
            # lateral se aplicaba una y otra vez por un solo dato nuevo.
            # Oir una cosa no deberia reordenarte el idioma entero.
            if hits >= self.cfg.chunk_max_hits:
                break

    def penalize(self, s, cat, place, factor):
        self.hol.penalize(s, (cat, place), factor)

    # -- introspeccion --------------------------------------------------
    def size(self):
        return self.hol.size() + self.cat.size() + self.place.size()

    def compositional_share(self):
        t = self.produced[HOLISTIC] + self.produced[COMPOSED]
        return self.produced[COMPOSED] / t if t else 0.0

    def knows_whole(self, cat, place):
        """¿Tiene una señal entera fiable para esta combinacion?

        Si no, tendra que componer o inventar. Es exactamente la condicion
        que dispara la primera rama de `express`, y por eso es la unica
        definicion honesta de "combinacion nueva": la que obliga a hacer
        algo distinto de tirar de memoria.
        """
        w = self.hol.produce((cat, place))
        return w is not None and self.hol.w[(w, (cat, place))] >= self.cfg.lex_confidence

    def has_rules(self):
        return bool(self.cat.by_form) and bool(self.place.by_form)
