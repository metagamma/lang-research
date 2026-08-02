#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 6 — gramatica con papeles y orden de palabras emergente.

Generaliza la gramatica de dos piezas de la Fase 5. Un significado ya no
es (cosa, lugar) sino un suceso completo:

    (accion, participante1, participante2, lugar, tiempo)

Tres cosas nuevas, y las tres importan.

1. VOCABULARIOS POR TIPO, NO POR RANURA
   Los dos participantes comparten el MISMO inventario de morfos. La
   palabra para «acechante» es la misma tanto si mata como si lo matan.
   Es lo que obliga a que el papel lo cargue otra cosa: la posicion.

2. ORDEN APRENDIDO, NO DADO
   Cada agente tiene pesos sobre los seis ordenes posibles del nucleo
   (SVO, SOV, VSO, VOS, OVS, OSV) y usa el que mas peso tiene. El orden
   se aprende por co-observacion: si viste quien se comio a quien, sabes
   que orden habria interpretado bien lo que oiste, y refuerzas ese.

   En la Fase 5 el orden estaba fijado por nosotros y lo dijimos como
   limitacion. Aqui deja de estarlo. Que una tribu converja a SOV y otra
   a SVO no es algo que hayamos puesto: es a lo que llegan.

3. ARIDAD VARIABLE
   `hay` tiene un participante y `comio` dos. El oyente no sabe cual es
   hasta haber interpretado la accion, que es una de las piezas — o sea,
   circular. Se resuelve probando las secuencias candidatas y quedandose
   con la que mejor puntua. Es exactamente el problema de un oyente real.

Lo que seguimos dando hecho, y conviene decirlo: lugar y tiempo van
siempre al final, detras del nucleo. Emerge el orden de los ARGUMENTOS,
no la posicion de los circunstanciales.
"""

from .events import ACTIONS, ARITY, BEFORE, DIJO, HAY, NOW, SEDICE
from .lexicon import Lexicon
from .phonology import coin

# --- vocabularios: inventarios de morfos por tipo de valor -------------
V_ACT, V_CAT, V_PLACE, V_TENSE = range(4)
N_VOC = 4

# --- ranuras del significado ------------------------------------------
S_ACT, S_ARG1, S_ARG2, S_PLACE, S_TENSE = range(5)
SLOT_VOC = {S_ACT: V_ACT, S_ARG1: V_CAT, S_ARG2: V_CAT,
            S_PLACE: V_PLACE, S_TENSE: V_TENSE}

# los seis ordenes tipologicos del nucleo
CORE_ORDERS = (
    (S_ARG1, S_ACT, S_ARG2),   # SVO
    (S_ARG1, S_ARG2, S_ACT),   # SOV
    (S_ACT, S_ARG1, S_ARG2),   # VSO
    (S_ACT, S_ARG2, S_ARG1),   # VOS
    (S_ARG2, S_ACT, S_ARG1),   # OVS
    (S_ARG2, S_ARG1, S_ACT),   # OSV
)
ORDER_NAME = ("SVO", "SOV", "VSO", "VOS", "OVS", "OSV")
TAIL = (S_PLACE, S_TENSE)

HOLISTIC, COMPOSED, PARTIAL = "hol", "comp", "part"


def slot_value(m, slot):
    """El valor que le toca a una ranura dentro de un significado."""
    return m[slot] if slot < 3 else m[slot]


class Syntax:
    def __init__(self, cfg, rng):
        self.cfg = cfg
        self.rng = rng
        self.voc = [Lexicon(cfg, rng) for _ in range(N_VOC)]
        self.hol = Lexicon(cfg, rng)          # señales enteras, opacas
        self.order_w = [1.0] * len(CORE_ORDERS)
        self.heard = []
        self.produced = {HOLISTIC: 0, COMPOSED: 0}
        self.clouds = {}   # morfo -> nube sensorial (solo sonda)
        self.speaker_actual = None   # de quien es lo que estoy oyendo
        self._ctx = None             # plausibilidad por situacion (Fase 10)
        self.parsed = {HOLISTIC: 0, COMPOSED: 0, PARTIAL: 0}

    def record_cloud(self, pieza, percept):
        """Anota un percepto en la nube de una pieza concreta."""
        from .attributes import Cloud
        c = self.clouds.get(pieza)
        if c is None:
            c = self.clouds[pieza] = Cloud(len(percept))
        c.add(percept)

    # -- atajos ---------------------------------------------------------
    @property
    def cat(self):
        """El inventario de morfos de categoria (lo usa la metafora)."""
        return self.voc[V_CAT]

    def best_order(self):
        best, bw = 0, -1.0
        for i, w in enumerate(self.order_w):
            if w > bw:
                best, bw = i, w
        return best

    def order_confidence(self):
        tot = sum(self.order_w)
        return max(self.order_w) / tot if tot else 0.0

    # -- secuencias de ranuras -----------------------------------------
    def _sequence(self, order_i, arity, mark_act=True, mark_tense=True):
        """Que ranuras llevan morfo, y en que orden.

        LO NO MARCADO NO SE DICE. El presente y el existencial son los
        valores por defecto y no llevan pieza: «hay un fruto en el valle»
        se dice igual que en la Fase 5, con dos morfos. Solo lo que se
        aparta del caso normal — un pasado, un suceso que no es un simple
        haber — añade material.

        Sin esto, cada enunciado exigia cuatro morfos y el oyente tenia que
        conocerlos los cuatro para entender algo. La comprension compuesta
        se quedaba en cero: se producia estructura que nadie sabia leer.
        Es tambien lo que hacen las lenguas reales con el morfema cero.
        """
        core = []
        for sl in CORE_ORDERS[order_i]:
            if sl == S_ARG2 and arity < 2:
                continue
            if sl == S_ACT and not mark_act:
                continue
            core.append(sl)
        tail = [S_PLACE]
        if mark_tense:
            tail.append(S_TENSE)
        return core + tail

    # -- recursividad (Fase 7) -----------------------------------------
    def _is_quote(self, m):
        return m[S_ACT] == DIJO and isinstance(m[S_ARG1], tuple)

    def quote(self, inner):
        """Envuelve un suceso en «alguien dijo que ...»."""
        return (DIJO, inner, None, None, None)

    def depth(self, m, d=1):
        return self.depth(m[S_ARG1], d + 1) if self._is_quote(m) else d

    # -- produccion -----------------------------------------------------
    def express(self, m, order_i=None, _d=0):
        """(cadena, modo). NO contabiliza: sirve tambien para medir."""
        whole = self.hol.produce(m)
        if whole is not None and self.hol.w[(whole, m)] >= self.cfg.lex_confidence:
            return whole, HOLISTIC
        if self._is_quote(m):
            # complementante delante + la oracion encajada detras.
            # Que el marcador vaya siempre en cabeza es cosa nuestra, no
            # emerge; lo que si emerge es que exista el encaje y se use.
            if _d >= self.cfg.max_depth:
                return (whole, HOLISTIC) if whole is not None else (None, None)
            marca = self.voc[V_ACT].produce(DIJO)
            dentro, _ = self.express(m[S_ARG1], order_i, _d + 1)
            if marca is None or dentro is None:
                return (whole, HOLISTIC) if whole is not None else (None, None)
            return marca + dentro, COMPOSED
        oi = self.best_order() if order_i is None else order_i
        parts = []
        seq = self._sequence(oi, ARITY[m[S_ACT]],
                             mark_act=m[S_ACT] != HAY,
                             mark_tense=m[S_TENSE] != NOW)
        for slot in seq:
            v = m[slot]
            if not isinstance(v, int):
                continue
            morph = self.voc[SLOT_VOC[slot]].produce(v)
            if morph is None:
                return (whole, HOLISTIC) if whole is not None else (None, None)
            parts.append(morph)
        return ("".join(parts), COMPOSED) if parts else (None, None)

    def produce(self, m):
        s, mode = self.express(m)
        if mode:
            self.produced[mode] += 1
        return s, mode

    def invent(self, m):
        """Crear lo que falte. Reutiliza cada pieza que ya exista."""
        if self._is_quote(m):
            if self.voc[V_ACT].produce(DIJO) is None:
                self.voc[V_ACT].invent(DIJO)
            self.invent(m[S_ARG1])
            s, mode = self.express(m)
            if mode:
                self.produced[mode] += 1
            return s, mode
        if self.rng.random() >= self.cfg.p_compose and not self._any_morph(m):
            form = coin(self.rng)
            self.hol._set(form, m, self.cfg.lex_init_w)
            self.produced[HOLISTIC] += 1
            return form, HOLISTIC
        for slot in self._sequence(self.best_order(), ARITY[m[S_ACT]]):
            v = m[slot]
            if v is not None and self.voc[SLOT_VOC[slot]].produce(v) is None:
                self.voc[SLOT_VOC[slot]].invent(v)
        s, mode = self.express(m)
        if mode:
            self.produced[mode] += 1
        return s, mode

    def _any_morph(self, m):
        for slot in (S_ACT, S_ARG1, S_ARG2, S_PLACE, S_TENSE):
            v = m[slot]
            if not isinstance(v, int):
                continue
            if self.voc[SLOT_VOC[slot]].produce(v) is not None:
                return True
        return False

    # -- comprension ----------------------------------------------------
    def parse(self, s, _d=0, count=True, contexto=None):
        """(significado, modo). El significado puede tener huecos a None."""
        self._ctx = contexto            # lo consulta _scan al desambiguar
        m = self.hol.interpret(s)
        if m is not None:
            if count:
                self.parsed[HOLISTIC] += 1
            return m, HOLISTIC

        hits = self._scan(s)
        # ¿empieza por el complementante? Entonces lo que sigue es una
        # oracion entera y hay que analizarla igual que cualquier otra:
        # la misma funcion llamandose a si misma. Eso es la recursividad.
        if _d < self.cfg.max_depth:
            for (j, v, _w) in hits[V_ACT].get(0, ()):
                if v != DIJO or j >= len(s):
                    continue
                dentro, modo = self.parse(s[j:], _d + 1, count)
                if dentro is not None:
                    if count:
                        self.parsed[COMPOSED] += 1
                    return (DIJO, dentro, None, None, None), COMPOSED
        best, bw = None, 0.0
        # Los ordenes se prueban de mas creido a menos, y se para pronto.
        # Un oyente no explora las seis gramaticas posibles cada vez que
        # oye algo: intenta la que tiene interiorizada y, si no cuadra,
        # una alternativa. Probar las seis siempre era lo que hacia la
        # comprension mas cara que toda la simulacion junta.
        orden = sorted(range(len(CORE_ORDERS)),
                       key=lambda i: -self.order_w[i])[:self.cfg.parse_orders]
        total = max(1e-9, sum(self.order_w))
        for oi in orden:
            # el oyente tampoco sabe de antemano si le hablan en pasado ni
            # cuantos participantes hay: prueba las lecturas posibles y se
            # queda con la que mas peso acumula. Las variantes sin marca
            # van primero porque son las mas frecuentes.
            for mark_a in (False, True):
                for mark_t in (False, True):
                    for arity in (1, 2):
                        seq = self._sequence(oi, arity, mark_a, mark_t)
                        got = self._segment(s, seq, hits)
                        if got is None:
                            continue
                        score = got[1] * self.order_w[oi] / total
                        if score > bw:
                            best, bw = (seq, got[0]), score
            if best is not None:
                break
        if best is None:
            got = self._prefix_guess(s, hits)
            if got is None:
                return None, None
            if count:
                self.parsed[PARTIAL] += 1
            return got, PARTIAL
        if count:
            self.parsed[COMPOSED] += 1
        return self._assemble(*best), COMPOSED

    def _scan(self, s):
        """Todos los morfos conocidos que aparecen en `s`, por posicion.

        Se hace UNA vez por señal en vez de una por cada orden y aridad
        que se prueba. Es la diferencia entre O(len^2) consultas y doce
        veces esa cifra, y era el verdadero cuello de la Fase 6.
        """
        lo, n = self.cfg.morph_min, len(s)
        hits = [dict() for _ in range(N_VOC)]
        for vi, voc in enumerate(self.voc):
            top = voc.max_len
            if top < lo:
                continue
            forms, w = voc.by_form, voc.w
            h = hits[vi]
            for i in range(n - lo + 1):
                # no tiene sentido mirar trozos mas largos que el morfo mas
                # largo que este agente conoce: no pueden ser ninguno suyo
                for j in range(i + lo, min(i + top, n) + 1):
                    piece = s[i:j]
                    if piece not in forms:
                        continue
                    v, weight = voc.best_for(piece, self._ctx if vi == V_CAT else None)
                    if v is not None:
                        h.setdefault(i, []).append((j, v, weight))
        return hits

    def _segment(self, s, seq, hits):
        """Reparte `s` entre las ranuras de `seq`. (valores, peso) o None.

        Con memoizacion, y no es un detalle de eficiencia: sin ella esto
        es exponencial. Cuando los morfos son cortos, en cada posicion de
        la cadena empiezan varios morfos conocidos, y explorar todas las
        combinaciones de cinco ranuras multiplica esas ramas entre si. La
        simulacion no iba lenta: se colgaba.

        Memoizando por (posicion, ranura) el mismo recorrido pasa a ser
        programacion dinamica sobre un enrejado, lineal en la longitud.
        """
        n = len(s)
        seen = {}

        def rec(i, k):
            key = (i, k)
            if key in seen:
                return seen[key]
            if k == len(seq):
                out = ([], 0.0) if i == n else None
            else:
                out = None
                for (j, v, w) in hits[SLOT_VOC[seq[k]]].get(i, ()):
                    rest = rec(j, k + 1)
                    if rest is None:
                        continue
                    score = w + rest[1]
                    if out is None or score > out[1]:
                        out = ([v] + rest[0], score)
            seen[key] = out
            return out

        return rec(0, 0)

    def _prefix_guess(self, s, hits):
        """Entender a medias: reconocer solo la primera pieza.

        Media señal sigue siendo mejor que nada — con la categoria pero
        sin el resto, el oyente ya puede decidir mejor que a ciegas. Que
        exista esta opcion es lo que hace util tener piezas.
        """
        for voc_i in (V_CAT, V_ACT):
            for (_, v, _) in hits[voc_i].get(0, ()):
                if v is None:
                    continue
                if voc_i == V_CAT:
                    return (HAY, v, None, None, None)
                return (v, None, None, None, None)
        return None

    def _assemble(self, seq, vals):
        # los valores por defecto rellenan lo que no vino marcado
        m = [HAY, None, None, None, NOW]
        for slot, v in zip(seq, vals):
            m[slot] = v
        if m[S_ACT] is None:
            m[S_ACT] = HAY
        return tuple(m)

    SLOT_NOMBRE = {S_ACT: "accion", S_ARG1: "cosa", S_ARG2: "cosa2",
                   S_PLACE: "lugar", S_TENSE: "tiempo"}

    def glosar(self, m):
        """Descompone lo que este agente diria, pieza a pieza.

        Devuelve [(morfo, ranura, valor)] o None si no lo construye por
        composicion. Es la misma logica de `express`, expuesta para poder
        ENSEÑAR la oracion segmentada en vez de una cadena opaca.

        No calcula nada nuevo ni altera nada: es una ventana a lo que el
        agente ya hace.
        """
        if self._is_quote(m):
            marca = self.voc[V_ACT].produce(DIJO)
            dentro = self.glosar(m[S_ARG1])
            if marca is None or dentro is None:
                return None
            return [(marca, "cita", "dijo que")] + dentro
        # NO se abandona si existe una forma holistica fuerte. Se llama a
        # esto sabiendo que el enunciado SE CONSTRUYO por composicion; y
        # para cuando llega la llamada, la co-observacion del propio
        # episodio ya ha reforzado el bloque entero. Mirar el estado de
        # ahora para explicar lo que se dijo antes daba None casi siempre.
        seq = self._sequence(self.best_order(), ARITY[m[S_ACT]],
                             mark_act=m[S_ACT] != HAY,
                             mark_tense=m[S_TENSE] != NOW)
        piezas = []
        for slot in seq:
            v = m[slot]
            if not isinstance(v, int):
                continue
            morfo = self.voc[SLOT_VOC[slot]].produce(v)
            if morfo is None:
                return None
            piezas.append((morfo, self.SLOT_NOMBRE.get(slot, "?"), v))
        return piezas or None

    # -- metalenguaje (Fase 11) -----------------------------------------
    def ensenar(self, forma, descripcion):
        """«[forma] se-dice [descripcion]». La lengua hablando de si misma.

        El orden es forma-marca-descripcion, no al reves, porque asi el
        oyente puede separar las partes en cuanto conoce la marca: lo de
        antes es la palabra, lo de despues es lo que significa. Sin un
        separador reconocible, dos cadenas pegadas no se pueden partir.
        """
        marca = self.voc[V_ACT].produce(SEDICE)
        if marca is None:
            marca = self.voc[V_ACT].invent(SEDICE)
        return forma + marca + descripcion

    def leer_ensenanza(self, s):
        """(forma, descripcion) si esto es una enseñanza. None si no.

        Se busca la marca de SEDICE dentro de la cadena; lo de antes es la
        palabra de la que se habla y lo de despues, su glosa.
        """
        marca = self.voc[V_ACT].produce(SEDICE)
        if not marca:
            return None
        i = s.find(marca, self.cfg.morph_min)
        if i < self.cfg.morph_min:
            return None
        forma, desc = s[:i], s[i + len(marca):]
        if len(forma) < self.cfg.morph_min or len(desc) < 2 * self.cfg.morph_min:
            return None
        return forma, desc

    # -- aprendizaje ----------------------------------------------------
    def observe(self, s, m, percept=None, speaker=None):
        """Co-observacion: oi `s` y luego vi que el suceso era `m`.

        `percept` es instrumentacion: alimenta las nubes sensoriales por
        morfo de `attributes.py`. No interviene en nada de lo que el
        agente aprende ni decide.
        """
        if percept is not None:
            from .attributes import record
            record(self, s, percept)
        if self._is_quote(m):
            self._learn_quote(s, m)
            return
        self.hol.reward(s, m, speaker)
        self.speaker_actual = speaker
        self._learn_order(s, m)
        if self.rng.random() < self.cfg.p_align:
            self._align(s, m)
        self.heard.append((s, m))
        if len(self.heard) > self.cfg.grammar_memory:
            self.heard.pop(0)
        self._chunk(s, m)
        if self.cfg.hol_capacity > 0:
            self.hol.trim(self.cfg.hol_capacity)

    def _learn_order(self, s, m):
        """¿Que orden habria leido bien lo que acabo de ver?

        No hace falta que nadie explique la regla: basta con haber visto
        el suceso y comprobar con que orden lo habria dicho uno mismo. Es
        generar-y-comparar, no buscar: seis construcciones baratas en vez
        de seis analisis completos. El que cuadra sube, los
        demas bajan un poco. Asi es como una tribu acaba compartiendo un
        orden sin que nadie lo decrete.
        """
        acierto = None
        for oi in range(len(CORE_ORDERS)):
            cand, _ = self.express(m, oi)
            if cand is None:
                continue
            if cand == s:
                acierto = oi
                break
        if acierto is None:
            return
        for i in range(len(self.order_w)):
            if i == acierto:
                self.order_w[i] = min(50.0, self.order_w[i] + 1.0)
            else:
                self.order_w[i] *= (1.0 - self.cfg.order_decay)

    def _learn_quote(self, s, m):
        """Aprender el complementante VERIFICANDO POR ANALISIS.

        La version anterior exigia que el oyente supiera decir la oracion
        de dentro con exactamente la misma cadena que el hablante, y solo
        entonces se quedaba con el sobrante como marca. Fallaba el 55% de
        las veces por una razon obvia en retrospectiva: dos hablantes de
        una lengua que aun no ha convergido dicen lo mismo de formas algo
        distintas. Estabamos pidiendo identidad de produccion cuando lo
        que importa es identidad de significado.

        Ahora se prueba cada corte posible y se comprueba si el resto SE
        ENTIENDE como el suceso de dentro. Entender no es reproducir: un
        oyente reconoce frases que el no habria construido igual. Eso es
        justamente lo que separa comprender de repetir.

        El analisis se hace sin contabilizar (`count=False`): medir la
        comprension no puede inflarse con los analisis que hace el propio
        aprendizaje, o el numero dejaria de significar nada.
        """
        dentro = m[S_ARG1]
        lo, hi = self.cfg.morph_min, self.cfg.morph_max
        tope = min(hi, len(s) - lo)
        for cut in range(lo, tope + 1):
            leido, _ = self.parse(s[cut:], _d=1, count=False)
            if leido is None:
                continue
            # basta con que coincida el nucleo: que pasa y a quien
            if (leido[S_ACT] == dentro[S_ACT]
                    and leido[S_ARG1] == dentro[S_ARG1]):
                self.voc[V_ACT].reward(s[:cut], DIJO)
                break
        self.hol.reward(s, m)

    def _align(self, s, m):
        """Alineamiento SUPERVISADO: sabiendo el significado, refuerza las piezas.

        Esta es la diferencia entre aprender a ciegas y aprender mirando.
        `_chunk` compara dos señales oidas y trata de adivinar donde esta
        la costura sin saber que significan; es debil y solo funciona
        cuando el mismo significado se repite mucho. Aqui el agente YA
        sabe lo que la frase significaba — acaba de verlo — asi que solo
        le falta repartir la cadena entre las ranuras.

        Regla de la pieza que sobra: se admite como maximo UN trozo
        desconocido. Si reconozco todas las palabras menos una, lo que
        queda tiene que ser la que falta. Es como aprende cualquiera una
        palabra nueva dentro de una frase que entiende, y es lo que
        permite que el vocabulario crezca de uno en uno en vez de tener
        que adivinarlo entero de golpe.

        Sin esto, nada reforzaba jamas un morfo por haber funcionado: solo
        lo hacia la induccion a ciegas. Con un espacio de significados
        grande esa via se queda sin repeticiones y el lexico no converge.
        """
        hits = self._scan(s)
        seq = self._sequence(self.best_order(), ARITY[m[S_ACT]],
                             mark_act=m[S_ACT] != HAY,
                             mark_tense=m[S_TENSE] != NOW)
        vals = [m[sl] for sl in seq]
        if any(not isinstance(v, int) for v in vals):
            return False
        got = self._supervised_split(s, seq, vals, hits)
        if got is None:
            return False
        for (piece, slot, val) in got:
            self.voc[SLOT_VOC[slot]].reward(piece, val,
                                            getattr(self, 'speaker_actual', None))
        return True

    def _supervised_split(self, s, seq, vals, hits, max_unknown=1):
        """Reparte `s` entre ranuras cuyos valores ya conocemos.

        Devuelve [(trozo, ranura, valor)] o None. Prefiere el reparto con
        menos piezas desconocidas: si hay una lectura que encaja del todo
        con lo que ya se sabe, esa gana.
        """
        lo, hi, n = self.cfg.morph_min, self.cfg.morph_max, len(s)
        seen = {}

        def rec(i, k, unk):
            if k == len(seq):
                return ([], unk) if i == n else None
            key = (i, k, unk)
            if key in seen:
                return seen[key]
            voc_i = SLOT_VOC[seq[k]]
            best = None
            conocidos = {j for (j, v, _) in hits[voc_i].get(i, ()) if v == vals[k]}
            # primero las piezas que ya se saben, luego la que sobra
            for j in range(i + lo, min(i + hi, n) + 1):
                nueva = 0 if j in conocidos else 1
                if unk + nueva > max_unknown:
                    continue
                rest = rec(j, k + 1, unk + nueva)
                if rest is None:
                    continue
                cand = ([(s[i:j], seq[k], vals[k])] + rest[0], rest[1])
                if best is None or cand[1] < best[1]:
                    best = cand
            seen[key] = best
            return best

        got = rec(0, 0, 0)
        return got[0] if got else None

    def _chunk(self, s, m):
        """Induccion de morfos: alinear señales que difieren en UNA ranura.

        Si dos frases hablan del mismo suceso cambiando solo el lugar, lo
        que comparten nombra el suceso y lo que las separa nombra el
        lugar. Generaliza el alineamiento de prefijos y sufijos de la Fase
        5 a cualquier numero de ranuras: se busca el trozo que varia.
        """
        lo, hi = self.cfg.morph_min, self.cfg.morph_max
        n = hits = 0
        for (s2, m2) in reversed(self.heard):
            n += 1
            if n > self.cfg.chunk_window:
                break
            if s2 == s or m2 == m:
                continue
            difs = [i for i in range(5) if m[i] != m2[i]]
            if len(difs) != 1:
                continue
            slot = difs[0]
            if m[slot] is None or m2[slot] is None:
                continue
            pre = _common_prefix(s, s2)
            suf = _common_suffix(s[len(pre):], s2[len(pre):])
            mid1 = s[len(pre):len(s) - len(suf)]
            mid2 = s2[len(pre):len(s2) - len(suf)]
            if not (lo <= len(mid1) <= hi and lo <= len(mid2) <= hi):
                continue
            voc = self.voc[SLOT_VOC[slot]] if slot < 5 else None
            if voc is None:
                continue
            voc.reward(mid1, m[slot])
            voc.reward(mid2, m2[slot])
            hits += 1
            if hits >= self.cfg.chunk_max_hits:
                break

    def penalize(self, s, m, factor):
        self.hol.penalize(s, m, factor)

    # -- introspeccion --------------------------------------------------
    def size(self):
        return self.hol.size() + sum(v.size() for v in self.voc)

    def compositional_share(self):
        t = self.produced[HOLISTIC] + self.produced[COMPOSED]
        return self.produced[COMPOSED] / t if t else 0.0

    def has_rules(self):
        return bool(self.voc[V_CAT].by_form) and bool(self.voc[V_ACT].by_form)

    def knows_whole(self, m):
        w = self.hol.produce(m)
        return w is not None and self.hol.w[(w, m)] >= self.cfg.lex_confidence


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
