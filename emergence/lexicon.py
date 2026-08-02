#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 3 — el lexico como grafo bipartito con pesos.

El modelo anterior usaba `dict concepto -> palabra`. Un diccionario hace
imposibles la sinonimia y la polisemia: no es que faltaran, es que el
tipo de dato las prohibia.

Aqui el lexico es una matriz dispersa de pesos

        w[(forma, categoria)] in R+

y por tanto:

  * varias formas pueden apuntar a una categoria   -> SINONIMIA
  * una forma puede apuntar a varias categorias    -> POLISEMIA

Actualizacion por inhibicion lateral (Steels): al reforzar un par se
debilitan sus competidores. Dos constantes distintas, a proposito:

  inhib_form    competencia entre formas de un mismo significado. ALTA.
                Es la fuerza que hace converger a la tribu a una palabra.
  inhib_meaning competencia entre significados de una misma forma. BAJA.
                Si la pusieramos igual de alta, la polisemia seria
                imposible por construccion y volveriamos al diccionario.
                Dejandola baja, la polisemia esta PERMITIDA pero no
                impuesta: que aparezca o no es un resultado, no un
                supuesto.
"""

from collections import defaultdict

from .phonology import coin


class Lexicon:
    def __init__(self, cfg, rng):
        self.cfg = cfg
        self.rng = rng
        self.w = {}                          # (forma, cat) -> peso
        self.by_cat = defaultdict(set)       # cat -> {formas}
        self.by_form = defaultdict(set)      # forma -> {cats}
        self.use = defaultdict(int)          # forma -> veces emitida
        self.born_extended = set()           # pares nacidos por metafora
        self.born_invented = set()           # pares acuñados por el mismo
        #   ^ para saber, de lo que un agente DICE, cuanto es de
        #     cosecha propia y cuanto adopto de otros. Es la prueba
        #     directa de si el auto-refuerzo gana a la adopcion.
        self.max_len = 0                     # forma mas larga conocida
        self.heard_from = defaultdict(set)   # forma -> quienes la usan

    # -- produccion / interpretacion ------------------------------------
    def produce(self, cat):
        """La forma que este agente diria para esa categoria, o None.

        Con `social_exp > 0` no gana la de mas peso sino la que combina
        peso y DIFUSION: de cuanta gente distinta se ha oido. Es lo que
        rompe los empates que el diagnostico encontro (hasta 0.46/0.46
        entre dos palabras para lo mismo): la frecuencia bruta no
        distingue «lo dice mucho uno» de «lo dice poca gente muchas
        veces», y esa distincion es justo la que decide que variante se
        impone en una comunidad.
        """
        forms = self.by_cat.get(cat)
        if not forms:
            return None
        e = self.cfg.social_exp
        best, bs = None, -1.0
        for f in forms:
            v = self.w[(f, cat)]
            if e:
                v *= (1 + len(self.heard_from.get(f, ()))) ** e
            if v > bs or (v == bs and self.rng.random() < 0.5):
                best, bs = f, v
        return best

    def best_for(self, form, contexto=None):
        """(significado, peso) mas fuerte de esa forma, sin exigir confianza.

        `interpret` calla cuando no esta seguro, que es lo correcto para
        decidir. Pero para SEGMENTAR una cadena hace falta ver todas las
        piezas candidatas, incluidas las que aun se saben mal: si no, un
        morfo recien acuñado es invisible para el analisis hasta que se
        refuerza, y no puede reforzarse porque nadie consigue analizarlo.
        El umbral debe graduar la confianza, no la visibilidad.
        """
        cats = self.by_form.get(form)
        if not cats:
            return None, 0.0
        e = self.cfg.pragmatica
        best, bw, bruto = None, -1.0, 0.0
        for c in cats:
            v = self.w[(form, c)]
            s = v * (1.0 + e * contexto(c)) if (e and contexto) else v
            if s > bw:
                best, bw, bruto = c, s, v
        return best, bruto

    def interpret(self, form, contexto=None):
        """La categoria mas fuerte para esa forma, si supera la confianza.

        Devolver None significa "he oido algo pero no se de que habla":
        el oyente cae entonces en exploracion, no en una decision segura.

        CONTEXTO (Fase 10). `contexto` es una funcion cat -> plausibilidad
        en la situacion actual. Una forma polisemica deja de significar
        siempre lo mismo: si `vrera` cubre el fruto dulce y el amargo, y
        aqui solo salen dulces, se lee «dulce».

        Esto es pragmatica en el sentido estricto — el significado de la
        MISMA señal cambia con la situacion — y no hace falta ningun
        mecanismo nuevo: la polisemia ya existia y el oyente ya sabia
        donde esta. Solo faltaba dejarle usar lo segundo para resolver lo
        primero.
        """
        cats = self.by_form.get(form)
        if not cats:
            return None
        e = self.cfg.pragmatica
        best, bw, bruto = None, -1.0, 0.0
        for c in cats:
            v = self.w[(form, c)]
            s = v * (1.0 + e * contexto(c)) if (e and contexto) else v
            if s > bw:
                best, bw, bruto = c, s, v
        # la confianza se mide sobre el peso REAL, no sobre el realzado:
        # el contexto ayuda a elegir entre candidatas, no a fabricar
        # certeza donde no la hay.
        return best if bruto >= self.cfg.lex_confidence else None

    def invent(self, cat):
        form = coin(self.rng)
        self._set(form, cat, self.cfg.lex_init_w)
        if (form, cat) in self.w:
            self.born_invented.add((form, cat))
        return form

    def extend(self, form, cat):
        """Fase 4: estirar una forma que ya existe hacia un significado nuevo.

        No es un caso especial de `invent`: la forma ya tiene dueño. Al
        engancharla a una segunda categoria, este agente se vuelve
        polisemico a proposito. Si al oyente le cuadra, la extension
        cuaja y se propaga; si no, la inhibicion la borra.

        Registramos el par como nacido por extension para poder medir
        despues que fraccion del lexico es metaforica. La marca es
        instrumentacion nuestra: el agente no la consulta jamas.
        """
        self._set(form, cat, self.cfg.lex_init_w)
        if (form, cat) in self.w:
            self.born_extended.add((form, cat))
        return form

    def named_categories(self, thr=None):
        """Categorias de las que este agente ya sabe hablar."""
        thr = self.cfg.lex_init_w if thr is None else thr
        return [c for c, forms in self.by_cat.items()
                if any(self.w[(f, c)] >= thr for f in forms)]

    # -- aprendizaje ----------------------------------------------------
    def reward(self, form, cat, speaker=None):
        """Co-observacion: he oido `form` y he visto que era un `cat` mio."""
        if speaker is not None:
            self.heard_from[form].add(speaker)
        cur = self.w.get((form, cat))
        if cur is None:
            self._set(form, cat, self.cfg.lex_init_w)
            cur = self.cfg.lex_init_w
        self._set(form, cat, min(1.0, cur + self.cfg.lex_lr))

        # inhibicion lateral en los dos ejes, con fuerzas distintas.
        # El `tuple(...)` hace falta porque _scale puede borrar entradas y
        # mutar el conjunto que estamos recorriendo; pero si no hay rival
        # no copiamos nada, que es el caso mayoritario.
        rivales = self.by_cat.get(cat)
        if rivales and len(rivales) > 1:
            factor = 1.0 - self.cfg.lex_inhib_form
            for f in tuple(rivales):
                if f != form:
                    self._scale(f, cat, factor)
        otros = self.by_form.get(form)
        if otros and len(otros) > 1:
            factor = 1.0 - self.cfg.lex_inhib_meaning
            for c in tuple(otros):
                if c != cat:
                    self._scale(form, c, factor)

    def penalize(self, form, cat, factor=0.7):
        if (form, cat) in self.w:
            self._scale(form, cat, factor)

    def note_use(self, form):
        self.use[form] += 1

    # -- internos -------------------------------------------------------
    def _set(self, form, cat, value):
        if value < self.cfg.lex_prune:
            self._drop(form, cat)
            return
        key = (form, cat)
        if key not in self.w:            # los indices solo cambian al crear
            self.by_cat[cat].add(form)
            self.by_form[form].add(cat)
            if len(form) > self.max_len:
                self.max_len = len(form)
        self.w[key] = value

    def _scale(self, form, cat, factor):
        v = self.w.get((form, cat))
        if v is None:
            return
        self._set(form, cat, v * factor)

    def _drop(self, form, cat):
        self.w.pop((form, cat), None)
        self.born_extended.discard((form, cat))
        self.born_invented.discard((form, cat))
        self.by_cat[cat].discard(form)
        self.by_form[form].discard(cat)
        if not self.by_cat[cat]:
            self.by_cat.pop(cat, None)
        if not self.by_form[form]:
            self.by_form.pop(form, None)

    def trim(self, capacity):
        """Olvida lo mas debil hasta caber. Devuelve cuantos pares cayeron.

        Nadie tiene memoria infinita. Este limite es lo que convierte
        "memorizar cada señal entera" en una estrategia inviable, y por
        tanto lo que puede empujar hacia una gramatica.
        """
        extra = len(self.w) - capacity
        if extra <= 0:
            return 0
        peores = sorted(self.w.items(), key=lambda kv: kv[1])[:extra]
        for (f, c), _ in peores:
            self._drop(f, c)
        return extra

    def forget_category(self, cat):
        for f in list(self.by_cat.get(cat, ())):
            self._drop(f, cat)

    # -- introspeccion ---------------------------------------------------
    def size(self):
        return len(self.w)

    def strong_pairs(self, thr=None):
        thr = self.cfg.lex_confidence if thr is None else thr
        return [(f, c, v) for (f, c), v in self.w.items() if v >= thr]

    def synonymy(self, thr=None):
        """Media de formas fuertes por categoria (1.0 = sin sinonimos)."""
        thr = self.cfg.lex_confidence if thr is None else thr
        counts = defaultdict(int)
        for (f, c), v in self.w.items():
            if v >= thr:
                counts[c] += 1
        return sum(counts.values()) / len(counts) if counts else 0.0

    def metaphor_share(self, thr=None):
        """Fraccion del lexico fuerte que nacio estirando otra palabra."""
        strong = self.strong_pairs(thr)
        if not strong:
            return 0.0
        n = sum(1 for f, c, _ in strong if (f, c) in self.born_extended)
        return n / len(strong)

    def polysemy(self, thr=None):
        """Media de significados fuertes por forma (1.0 = sin polisemia)."""
        thr = self.cfg.lex_confidence if thr is None else thr
        counts = defaultdict(int)
        for (f, c), v in self.w.items():
            if v >= thr:
                counts[f] += 1
        return sum(counts.values()) / len(counts) if counts else 0.0
