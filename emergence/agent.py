#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
El agente.

Tiene tres sistemas de aprendizaje separados, y la separacion importa:

  1. PARTICION   (percept.ConceptSpace) — que cosas son la misma cosa.
                 Se refina por sorpresa: cuando el resultado de consumir
                 contradice lo esperado, la categoria estaba mezclando
                 dos realidades y se parte.

  2. VALOR       (self.value) — cuanta energia da cada categoria SUYA.
                 Se aprende sufriendola en carne propia (EWMA).

  3. LEXICO      (lexicon.Lexicon) — que forma va con que categoria.
                 Se aprende por CO-OBSERVACION: oigo una forma y despues
                 veo el objeto del que se hablaba.

La separacion 2/3 es deliberada. El lexico nunca se refuerza con el pago
recibido, solo con la co-observacion; y el valor nunca se aprende de
oidas, solo por experiencia. Asi el lenguaje no puede "colarse" en la
funcion de recompensa: su unica via de influir en la supervivencia es
permitir decidir SIN percibir. Si aun asi ayuda, la ayuda es real.

REGIMEN COOPERATIVO (Regla 2 relajada, y con cuidado)
-----------------------------------------------------
El modelo por defecto premia en ENERGIA entenderse, comprimir y enseñar
(ver `config.py`, bloque «regimen cooperativo»). Eso NO toca ningun peso
de `lexicon.py`: la separacion 2/3 de arriba sigue intacta. Lo que cambia
es que el lenguaje pasa a comprar fitness tambien por comunicar bien, no
solo por permitir decidir sin percibir. Es una presion SELECTIVA
(energia -> reproduccion -> vigilancia), no telepatia lexica. La ablacion
falsable se corre aparte, en modo puro (`run._pure`), con estos premios a
cero.
"""

import numpy as np

from .events import ARITY, DIJO, Memory
from .percept import ConceptSpace
from .syntax import S_ACT, Syntax

_next_id = [0]


def _new_id():
    _next_id[0] += 1
    return _next_id[0]


class Agent:
    def __init__(self, cfg, rng, vigilance=None, tribe=0):
        self.cfg = cfg
        self.rng = rng
        self.id = _new_id()
        self.tribe = tribe
        self.age = 0
        self.energy = cfg.energy_start
        self.alive = True
        self.cause = None

        # gen heredable: resolucion perceptiva
        self.vigilance = cfg.vigilance if vigilance is None else vigilance
        self.concepts = ConceptSpace(self.vigilance, cfg.proto_lr, rng,
                                     cfg.max_categories, cfg.radius_min,
                                     cfg.dim)
        self.gram = Syntax(cfg, rng)
        # `lex` es el almacen de morfos de categoria: es sobre el que opera
        # la metafora de la Fase 4, que sigue funcionando igual.
        self.lex = self.gram.cat

        self.value = {}        # cat -> EWMA del delta de energia
        self.seen = {}         # cat -> veces experimentada de primera mano
        self.heard_of = set()  # cats cuyo valor viene SOLO de oidas
        self.origen = {}       # cat -> como se supo la PRIMERA vez
        self.en_region = {}    # (cat, region) -> veces vista alli
        self.por_region = {}   # region -> total visto alli
        #   ^ la procedencia se fija al aprender y no se reescribe. Si se
        #     mirara el estado actual, la experiencia directa borraria el
        #     rastro: casi todo acaba viviendose, y entonces parece que el
        #     testimonio nunca enseño nada aunque hubiera llegado antes.
        self.place_cost = {}   # lugar -> lo que cuesta llegar (se aprende andando)
        # Fase 9: posicion en el mundo. Deja de ser cierto que cualquier
        # par de la tribu se encuentre con la misma probabilidad, y eso
        # reparte el saber: cada uno ve lo que crece donde anda.
        self.pos = np.array([rng.random(), rng.random()])
        self.memory = Memory(cfg.memory_events)   # sucesos presenciados
        # Que papel de cada tipo de suceso carga con el pago. NO se lo
        # decimos: lo aprende viendo sucesos de primera mano. Es lo que
        # despues permite aprovechar un testimonio sobre algo que nunca
        # ha visto -- sabe que en un `mato` el peligro esta en la primera
        # posicion porque lo ha comprobado, no porque se lo hayan dicho.
        self.role_value = {}   # (accion, papel) -> EWMA del delta observado
        # competencia comunicativa acumulada: cuantas veces este agente
        # cobro premio por entenderse o enseñar. La seleccion competitiva
        # (Capa 3) reproduce antes a quien mas comunica. Nace en 0: no se
        # hereda, se gana viviendo — igual que la lengua.
        self.comm_score = 0.0

    # -- percepcion ------------------------------------------------------
    def perceive(self, thing):
        return np.clip(thing.features + self.rng.noise(self.cfg.dim,
                                                       self.cfg.perception_noise),
                       0.0, 1.0)

    def categorize(self, thing):
        return self.concepts.categorize(self.perceive(thing))

    def classify_batch(self, X):
        """Percibe y clasifica una matriz de estimulos, sin aprender nada.

        Solo la usa la instrumentacion. Mantiene el ruido perceptivo (dos
        agentes distintos siguen viendo lo mismo de forma distinta), pero
        lo genera de una vez para todo el lote.
        """
        if len(X) == 0:
            return []
        noise = self.rng.noise(X.size, self.cfg.perception_noise)
        return self.concepts.classify_many(np.clip(X + noise.reshape(X.shape),
                                                   0.0, 1.0))

    # -- valor -----------------------------------------------------------
    def expected(self, cat):
        return self.value.get(cat)

    def learn_value(self, cat, delta, percept=None):
        """Registra el resultado y, si sorprende, parte la categoria.

        Una sorpresa grande significa que esta categoria contiene cosas
        que se comportan distinto: la particion era demasiado gruesa.
        """
        prev = self.value.get(cat)
        self.origen.setdefault(cat, "vivido")
        self.seen[cat] = self.seen.get(cat, 0) + 1

        surprised = (prev is not None
                     and abs(delta - prev) > self.cfg.surprise_split
                     and percept is not None
                     and self.rng.random() < self.cfg.p_split)

        if surprised:
            new_cat = self.concepts.split(percept, blame=cat)
            if new_cat != cat:
                self.value[new_cat] = delta      # nace ya con lo aprendido
                self.seen[new_cat] = 1
                return new_cat

        a = self.cfg.value_lr
        self.value[cat] = delta if prev is None else (1 - a) * prev + a * delta
        return cat

    # -- decisiones ------------------------------------------------------
    def wander(self, rng):
        """Deriva lenta. Ni quieto ni teletransportado."""
        self.pos = np.clip(
            self.pos + rng.noise(2, self.cfg.wander), 0.02, 0.98)

    def anotar_region(self, cat, region):
        """Llevar la cuenta de que aparece en cada sitio.

        No es un mecanismo nuevo: es lo que cualquiera acumula andando por
        ahi. Sirve para desambiguar despues — si aqui nunca sale el fruto
        amargo, una palabra que cubre los dos frutos se lee «dulce».
        """
        if cat is None or region is None:
            return
        k = (cat, region)
        self.en_region[k] = self.en_region.get(k, 0) + 1
        self.por_region[region] = self.por_region.get(region, 0) + 1

    def contexto_de(self, region):
        """Plausibilidad de cada categoria en esta region, en [0, 1].

        Devuelve None si aun no ha andado bastante por aqui: sin datos, el
        contexto no debe opinar. Un prior inventado seria peor que ninguno.
        """
        total = self.por_region.get(region, 0)
        if total < self.cfg.contexto_min:
            return None
        return lambda c: self.en_region.get((c, region), 0) / total

    def learn_place(self, place, cost):
        a = self.cfg.value_lr
        prev = self.place_cost.get(place)
        self.place_cost[place] = cost if prev is None else (1 - a) * prev + a * cost

    def _typical_cost(self):
        """Cuanto suele costar llegar, cuando no se a donde hay que ir."""
        if not self.place_cost:
            return None
        return sum(self.place_cost.values()) / len(self.place_cost)

    def expected_gain(self, cat, place):
        """Lo que espera sacar. None = no tiene ni idea.

        Aqui se ve para que sirve entender media señal: con la categoria
        pero sin el lugar, el agente todavia puede decidir usando el
        coste tipico. Peor que saberlo todo, mucho mejor que nada.
        """
        v = None if cat is None else self.value.get(cat)
        if v is None:
            return None
        c = self.place_cost.get(place) if place is not None else self._typical_cost()
        return None if c is None else v - c

    def decide_approach(self, cat, place):
        """¿Merece la pena acercarse a algo que NO estoy percibiendo?"""
        g = self.expected_gain(cat, place)
        if g is None:
            return self.rng.random() < self.cfg.p_explore
        if g > 0:
            return True
        return self.rng.random() < self.cfg.p_explore_against

    def decide_flee(self, cat):
        """La decision hay que tomarla ANTES de tener el bicho encima."""
        v = None if cat is None else self.value.get(cat)
        if v is None:
            return False
        return v < -self.cfg.flee_cost

    def wants_to_speak(self, cat):
        n = self.seen.get(cat, 0)
        v = self.value.get(cat)
        if v is None or n <= self.cfg.novel_count:
            return self.rng.random() < self.cfg.p_babble   # balbuceo
        # hablar cuesta; solo compensa si lo que hay importa
        return abs(v) * self.cfg.kin_share > self.cfg.speak_threshold

    def utter(self, m):
        """Señal para un significado completo. (None, None) = callar."""
        s, mode = self.gram.produce(m)
        if s is None:
            if len(self.gram.heard) < self.cfg.listen_before_speak:
                return None, None      # aun escuchando: no acuña todavia
            if self.rng.random() >= self.cfg.p_invent:
                return None, None
            for slot in (1, 2):         # metafora sobre los participantes
                # una oracion encajada no es una categoria: no se le puede
                # prestar la palabra de un concepto vecino
                if isinstance(m[slot], int):
                    self._stretch(m[slot])
            s, mode = self.gram.invent(m)
        if s is None:
            return None, None
        self.gram.hol.note_use(s)
        self.energy -= self.cfg.speak_cost
        return s, mode

    # -- descripcion (Fase 8) ---------------------------------------------
    def describe(self, cat, ref, forzar=False):
        """Enumerar como es algo cuando no te fias de como se llama.

        Devuelve la cadena descriptiva, o None. La condicion es concreta y
        observable por el propio agente: que el peso de su mejor palabra
        para esa categoria no llegue al umbral de confianza. Es justo lo
        que hace cualquiera al no recordar un nombre — describirlo.
        """
        from .attributes import describir
        if not (0 <= cat < self.concepts.n):
            return None
        if not forzar:
            forma = self.gram.cat.produce(cat)
            peso = self.gram.cat.w.get((forma, cat), 0.0) if forma else 0.0
            if peso >= self.cfg.lex_confidence:
                return None
        if self.rng.random() >= self.cfg.p_describe:
            return None
        piezas, _ = describir(self.gram, self.concepts.protos[cat], ref,
                              min_n=self.cfg.describe_min_morphs,
                              refina=self.cfg.desc_refina)
        return "".join(piezas) if len(piezas) >= 2 else None

    def ensenar_palabra(self, cat, ref):
        """«mi palabra para esto es X, y esto es: verde, amargo».

        Se hace cuando el otro NO te ha entendido: en vez de repetir o de
        limitarte a describir, emparejas tu palabra con su descripcion.
        Asi el oyente no solo entiende esta vez, se lleva la palabra.
        """
        from .attributes import describir
        forma = self.gram.cat.produce(cat)
        if forma is None or not (0 <= cat < self.concepts.n):
            return None
        piezas, _ = describir(self.gram, self.concepts.protos[cat], ref,
                              min_n=self.cfg.describe_min_morphs,
                              refina=self.cfg.desc_refina)
        if len(piezas) < 2:
            return None
        return self.gram.ensenar(forma, "".join(piezas))

    def aprender_ensenanza(self, cadena, ref, medio):
        """Alguien me esta enseñando una palabra. ¿La entiendo y la adopto?

        REGLA DE LA PIEZA QUE SOBRA, aplicada a la construccion entera.
        Antes esto exigia conocer ya la marca de «se dice» para poder
        separar la cadena — y como cada hablante inventaba la suya, el
        100% se caia en ese primer eslabon sin llegar a intentar nada mas.

        Es el mismo callejon que tuvo el complementante y se sale igual:
        si reconozco lo de los extremos, lo de en medio TIENE que ser la
        marca. Se prueban los cortes; si el principio es una palabra
        plausible y el final se decodifica como descripcion, el trozo
        central se adopta como marca.

        Sigue sin entrar nada sin anclaje: hace falta decodificar la
        glosa. Lo que se relaja no es la exigencia de entender, es la de
        conocer de antemano el separador.
        """
        from .events import SEDICE
        lo, hi = self.cfg.morph_min, self.cfg.morph_max
        n = len(cadena)
        conocida = self.gram.leer_ensenanza(cadena)
        candidatos = [conocida] if conocida else []
        if not candidatos:
            # sin marca conocida: buscar el corte que deje una glosa legible
            for i in range(lo, n - 2 * lo):
                for j in range(i + lo, min(i + hi, n - 2 * lo) + 1):
                    candidatos.append((cadena[:i], cadena[j:], cadena[i:j]))
        for cand in candidatos:
            if len(cand) == 2:
                forma, desc, marca = cand[0], cand[1], None
            else:
                forma, desc, marca = cand
            cat, _nuevo = self.understand_description(desc, ref, medio)
            if cat is None:
                continue
            self.gram.cat.reward(forma, cat)
            if marca is not None:
                self.gram.voc[0].reward(marca, SEDICE)   # la pieza que sobraba
            return True
        return False

    def understand_description(self, cadena, ref, medio):
        """Leer una descripcion: hallar el concepto o INSTALARLO.

        Si ya tiene una categoria que cumple las restricciones, la usa. Si
        no, crea una provisional. Esa es la unica via del modelo por la que
        una palabra entrega un CONCEPTO y no solo un valor.
        """
        from .attributes import entender
        cons = entender(self.gram, cadena, ref,
                        min_n=self.cfg.describe_min_morphs)
        if cons is None:
            return None, False
        x = list(medio)
        for d, v in cons.items():
            x[d] = v
        i = self.concepts.classify(x)
        if i is not None:
            return i, False
        i = self.concepts.install_described(
            cons, medio, self.vigilance * self.cfg.described_radius)
        return i, i is not None

    def learn_description(self, cadena, cat_visto, percept):
        """Regla de la pieza que sobra, aplicada a una descripcion.

        Si reconozco alguna pieza, lo que queda tiene que ser otra pieza —
        y acabo de ver a que se referia todo. Cada trozo se engancha a la
        categoria observada, igual que cualquier palabra.

        Un adjetivo acaba siendo, en esta representacion, un morfo
        POLISEMICO cuyos significados comparten una dimension sensorial:
        aparece con muchas cosas distintas que tienen algo en comun. No
        hay que declararlo adjetivo; se vuelve uno al usarse asi.
        """
        lo, hi = self.cfg.morph_min, self.cfg.morph_max
        n = len(cadena)
        conocidas = self.gram.cat.by_form
        i = piezas = 0
        trozos, reconocidas = [], 0
        while i < n:
            corte = None
            for j in range(min(i + hi, n), i + lo - 1, -1):
                if cadena[i:j] in conocidas:
                    corte = j
                    break
            if corte is None:
                corte = min(i + hi, n)
            else:
                reconocidas += 1
            trozos.append(cadena[i:corte])
            i = corte
        if reconocidas == 0 or len(trozos) < 2:
            return False            # sin ancla, no se inventa nada
        for t in trozos:
            if lo <= len(t) <= hi:
                self.gram.cat.reward(t, cat_visto)
                self.gram.record_cloud(t, percept)
        return True

    # -- sucesos (Fase 6) -------------------------------------------------
    def remember(self, action, c1, c2, place, gen, salience=None,
                 hearsay=False):
        """Guardar un suceso, si merece la pena guardarlo.

        Nadie recuerda cada arbusto que vio. Se retiene lo que tuvo
        consecuencias, y eso ademas es lo unico que despues valdra la pena
        contar. La memoria selectiva no es una optimizacion: es lo que
        hace que un relato lleve informacion.
        """
        if salience is None:
            salience = abs(self.value.get(c1, 0.0)) if c1 is not None else 0.0
        if salience < self.cfg.memory_salience:
            return False
        self.memory.add(action, c1, c2, place, gen, hearsay)
        return True

    def witness(self, event, gen):
        """Presenciar un suceso: categorizar participantes y recordarlo."""
        c1 = self.concepts.classify(self.perceive(event.t1)) if event.t1 else None
        c2 = self.concepts.classify(self.perceive(event.t2)) if event.t2 else None
        self.memory.add(event.action, c1, c2, event.place, gen)
        return c1, c2

    def learn_role(self, action, role, delta):
        """De primera mano: en este tipo de suceso, este papel vale esto."""
        a = self.cfg.value_lr
        k = (action, role)
        prev = self.role_value.get(k)
        self.role_value[k] = delta if prev is None else (1 - a) * prev + a * delta

    def learn_from_testimony(self, m):
        """Aprender de lo que otro cuenta.

        La regla es estricta y es la que sostiene todo el modelo: el
        testimonio dice QUE categoria ocupaba un papel, nunca CUANTO duele.
        El cuanto sale de `role_value`, que este agente aprendio sufriendo
        o viendo sucesos con sus propios ojos.

        Asi, oir «un acechante mato a alguien» sirve incluso si nunca has
        visto un acechante: ya sabes lo que cuesta un `mato`. Lo que te
        faltaba era saber a que se parece el que lo hace. Eso es lenguaje
        haciendo su trabajo, no telepatia.
        """
        # «me dijeron que...»: se desenvuelve y se descuenta mas. Cada
        # capa de encaje aleja la informacion de quien la vivio, y el peso
        # baja con ella. Es lo que impide que un rumor repetido acabe
        # pesando tanto como haberlo visto.
        lr = self.cfg.testimony_lr
        depth = 0
        while m[S_ACT] == DIJO and isinstance(m[1], tuple):
            m = m[1]
            depth += 1
            lr = self.cfg.hearsay_lr
            if depth >= self.cfg.max_depth:
                break
        act = m[S_ACT]
        learned = False
        for role in range(ARITY[act]):
            cat = m[1 + role]
            rv = self.role_value.get((act, role))
            if cat is None or rv is None or abs(rv) < 0.5:
                continue
            prev = self.value.get(cat)
            self.origen.setdefault(cat, "oidas")
            self.value[cat] = rv if prev is None else (1 - lr) * prev + lr * rv
            self.heard_of.add(cat)
            learned = True
        # Se anota que a uno se lo CONTARON, haya aprendido algo o no.
        # Uno recuerda que le hablaron de un acechante en la loma aunque no
        # sepa aun cuanto muerde. Antes solo se guardaba cuando ademas
        # enseñaba, y el encaje era tan raro (0.6% de los enunciados) que
        # el complementante no llegaba a cuajar en la tribu.
        if m[1] is not None:
            self.memory.add(act, m[1], m[2], m[3], self.age, True)
        return learned

    def _stretch(self, cat):
        """Fase 4 — extension metaforica. None si no procede.

        Le falta palabra para `cat`. Antes de acuñar una de la nada, mira
        si algun concepto SUYO parecido ya la tiene, y se la presta.

        Es el mecanismo de mano -> mano de pintura: la palabra viaja por
        semejanza perceptiva. Solo hace falta una cosa que el agente ya
        tenga (la distancia entre sus propios prototipos); no consulta
        ninguna etiqueta del mundo ni sabe que esta haciendo una metafora.

        Por que no siempre: acuñar da una palabra univoca pero cuesta que
        la tribu la aprenda; estirar reutiliza algo que los demas YA
        entienden pero introduce ambiguedad. Cual de las dos gana es una
        pregunta empirica — por eso `p_metaphor` es un parametro y se
        puede poner a cero para ablacionarla.
        """
        if self.lex.produce(cat) is not None:
            return False                      # ya tiene morfo propio
        if self.rng.random() >= self.cfg.p_metaphor:
            return False
        src, _ = self.concepts.nearest_among(cat, self.lex.named_categories(),
                                             self.cfg.metaphor_radius)
        if src is None:
            return False
        form = self.lex.produce(src)
        if not form:
            return False
        self.lex.extend(form, cat)
        return True

    # -- energia / ciclo vital -------------------------------------------
    def gain(self, delta):
        self.energy = min(self.cfg.energy_max, self.energy + delta)
        if self.energy <= 0:
            self.alive = False
            self.cause = self.cause or "hambre"

    def kill(self, cause):
        self.alive = False
        self.cause = cause

    def child(self, rng):
        v = self.vigilance + rng.gauss(0.0, self.cfg.vigilance_mut)
        v = min(self.cfg.vigilance_max, max(self.cfg.vigilance_min, v))
        c = Agent(self.cfg, rng, vigilance=v, tribe=self.tribe)
        c.energy = self.cfg.child_energy
        c.pos = np.clip(self.pos + rng.noise(2, 0.05), 0.02, 0.98)  # nace cerca
        # el hijo NO hereda ni categorias ni palabras: las tiene que
        # aprender viviendo. El idioma no es un genoma.
        return c

    def __repr__(self):
        return (f"<Agent {self.id} t{self.tribe} e={self.energy:.1f} "
                f"cats={len(self.concepts)} gram={self.gram.size()}>")
