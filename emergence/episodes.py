#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fase 2 + Fase 6 — el lenguaje aparece porque hace falta, y acaba hablando
de lo que ya no esta delante.

Aqui no hay ningun "naming game". Nadie ejecuta un protocolo. Hay agentes
con hambre y depredadores. La asimetria que lo hace todo posible:

    el HABLANTE percibe la situacion.
    el OYENTE no.

DOS REGLAS DE APRENDIZAJE, DISJUNTAS
------------------------------------
  * la LENGUA solo se refuerza por CO-OBSERVACION: oi algo y despues vi
    de que se hablaba.
  * el VALOR de una categoria solo se aprende EXPERIMENTANDO: comi, o no
    hui y me alcanzo.

Por eso el lenguaje no puede colarse en la funcion de recompensa. Su
unico canal causal hacia la supervivencia es permitir decidir sin
percibir. Si aun asi la ablacion detecta ventaja, la ventaja es real.

EL PASADO NO SE PUEDE CO-OBSERVAR
---------------------------------
En cuanto un hablante cuenta algo que ya paso, la regla de arriba se
queda sin suelo: el oyente no puede volverse a mirar. Eso aqui no se
parchea, se respeta, y de ahi salen las dos consecuencias que son el
nucleo de la Fase 6.

  1. Un relato del pasado solo enseña PALABRAS si el oyente tambien
     estuvo alli y lo recuerda. La memoria compartida es el unico anclaje
     firme del tiempo verbal: el morfo de «antes» se aprende de lo vivido
     en comun, y solo despues sirve para contar lo que el otro no vio.

  2. Un relato sobre algo que el oyente no presencio no enseña palabras,
     pero puede enseñar el MUNDO — si ya entiende las palabras. Eso es
     `learn_from_testimony`, y es la unica via por la que un saber puede
     sobrevivir a quien lo adquirio.

Tres modos de canal, como siempre:

  language   el hablante emite su señal
  mute       no hay canal (ablacion)
  noise      señal aleatoria de un repertorio fijo (aisla SEÑALAR de INFORMAR)
"""

from .events import BEFORE, COMIO, DAÑO, DIJO, HAY, MATO, NOW
from .phonology import coin

MODE_LANGUAGE = "language"
MODE_MUTE = "mute"
MODE_NOISE = "noise"
MODES = (MODE_LANGUAGE, MODE_MUTE, MODE_NOISE)


class Channel:
    """El medio. Decide que llega del hablante al oyente."""

    def __init__(self, mode, cfg, rng, n_noise=14):
        assert mode in MODES, mode
        self.mode = mode
        self.cfg = cfg
        self.rng = rng
        self.noise_forms = [coin(rng) for _ in range(n_noise)]
        self.sent = 0

    def transmit(self, speaker, m):
        """(cadena, modo_de_construccion). (None, None) = silencio."""
        if self.mode == MODE_MUTE or m is None:
            return None, None
        if self.mode == MODE_NOISE:
            speaker.energy -= self.cfg.speak_cost
            self.sent += 1
            return self.rng.choice(self.noise_forms), None
        s, how = speaker.utter(m)
        if s is not None:
            self.sent += 1
        return s, how


def _kin_payback(speaker, listener_delta, listener_died, cfg):
    d = cfg.kin_share * listener_delta
    if listener_died:
        d -= cfg.kin_death_penalty
    speaker.gain(d)


# ---------------------------------------------------------------------
# Que decide contar el hablante
# ---------------------------------------------------------------------

def _choose_message(speaker, cat_now, place, gen, rng, cfg):
    """(significado, es_pasado, recuerdo). None = no tiene nada que decir.

    Contar el pasado tiene un coste real e inmediato: mientras hablas de
    ayer no estas avisando de lo que hay delante, y el oyente decide peor.
    Que aun asi compense es lo que la simulacion tiene que resolver, no
    algo que le impongamos.
    """
    if rng.random() < cfg.p_report_past and len(speaker.memory):
        rec = speaker.memory.recall(rng, gen)
        if rec is not None and rec[1] is not None:
            act, c1, c2, pl, _, oido = rec
            m = (act, c1, c2, pl, BEFORE)
            if oido and rng.random() < cfg.p_quote:
                # no lo vio: lo marca como contado (Fase 7)
                m = (DIJO, m, None, None, None)
            return m, True, rec
    if cat_now is None or not speaker.wants_to_speak(cat_now):
        return None, False, None
    return (HAY, cat_now, None, place, NOW), False, None


def _teach_past(listener, speaker, form, msg, memrec, acc, quoted=False):
    """Que se aprende de un relato del pasado.

    Si el oyente tambien estuvo alli, hay co-observacion diferida y la
    lengua se aprende. Si no, no se aprende ni una palabra: lo unico que
    puede cruzar es informacion sobre el mundo, y solo si ya entendia.
    """
    act, _, _, pl, g = memrec[:5]
    mine = next((e for e in listener.memory.items
                 if e[0] == act and e[3] == pl and e[4] == g), None)
    if mine is not None and mine[1] is not None:
        propio = (mine[0], mine[1], mine[2], mine[3], BEFORE)
        if quoted:
            # se lo estan CONTANDO, no afirmando. El oyente reconstruye el
            # suceso con sus propias categorias y lo envuelve igual que lo
            # oyo: asi es como se aprende el complementante. Sin esto solo
            # lo sabia quien lo decia, y nadie lo entendia al oirlo.
            propio = listener.gram.quote(propio)
        listener.gram.observe(form, propio)
        speaker.gram.observe(form, msg)
        acc.ground("recuerdo compartido")
    else:
        acc.ground("relato ajeno")


# ---------------------------------------------------------------------
# FORRAJEO: A esta junto a algo. B esta lejos y tiene que decidir.
# ---------------------------------------------------------------------

def forage_episode(world, speaker, listener, channel, cfg, rng, gen, acc):
    thing = world.sample_thing()
    rec = {"type": "forage", "kind": thing.kind.name, "place": thing.place,
           "afford": thing.affordance, "signal": None, "said": None,
           "acted": False, "optimal": None, "chose_well": None,
           "understood": False, "parsed": None, "novel": None,
           "past": False, "testimony": False, "quoted": False,
           "quote_ok": False, "descrito": False, "desc_ok": False,
           "concepto_nuevo": False}

    px = speaker.perceive(thing)
    cat_s = speaker.concepts.categorize(px)
    msg, is_past, memrec = _choose_message(speaker, cat_s, thing.place, gen,
                                           rng, cfg)
    rec["past"] = is_past
    rec["quoted"] = msg is not None and msg[0] == DIJO
    if msg is not None:
        rec["novel"] = not speaker.gram.knows_whole(msg)
    form, how = channel.transmit(speaker, msg) if msg else (None, None)

    # Si no se fia de su palabra, DESCRIBE en vez de nombrar. Es lo que
    # cierra el bucle: sin emitirlas en episodios reales, las piezas
    # atributivas nunca pasan por la co-observacion que las alinea, y cada
    # agente se queda con las suyas (solapamiento medido: 0.016).
    descripcion = None
    if (channel.mode == MODE_LANGUAGE and not is_past and msg is not None
            and speaker.wants_to_speak(cat_s)):
        descripcion = speaker.describe(cat_s, world.spread(rng))
        if descripcion is not None:
            form, how = descripcion, "desc"
            speaker.energy -= cfg.speak_cost
            rec["descrito"] = True
    rec["signal"], rec["said"] = form, how

    # el hablante esta alli: decide CON percepcion, no necesita lenguaje
    if speaker.decide_approach(cat_s, thing.place):
        speaker.gain(thing.payoff)
        cat_s = speaker.learn_value(cat_s, thing.payoff, px)

    # --- oyente: a ciegas, salvo por lo que oiga ---
    heard = parsed = None
    if form and not rec["descrito"]:
        heard, parsed = listener.gram.parse(form)
    rec["parsed"] = parsed

    cat_heard = place_heard = None
    if rec["descrito"]:
        c, nuevo = listener.understand_description(
            form, world.spread(rng), world.medio(rng))
        rec["desc_ok"] = c is not None
        rec["concepto_nuevo"] = nuevo
        cat_heard = c
    if heard is not None:
        if rec["quoted"] and heard[0] == DIJO:
            rec["quote_ok"] = True
        if heard[4] == BEFORE or heard[0] != HAY:
            # le hablan de otra cosa: no sirve para decidir ahora, pero
            # puede enseñarle algo del mundo
            rec["testimony"] = listener.learn_from_testimony(heard)
        else:
            cat_heard, place_heard = heard[1], heard[3]
            rec["heard_now"] = True
    rec["understood"] = cat_heard is not None

    approach = listener.decide_approach(cat_heard, place_heard)

    # REPARACION. Si el nombre no cuajo — el otro no reacciono y el
    # hablante creia que importaba — se intenta describir. Es lo que hace
    # cualquiera cuando le ponen cara de nada: enumerar como es la cosa.
    #
    # Este es el disparador que faltaba. El anterior («no me fio de mi
    # palabra») se apagaba justo cuando el idioma funcionaba, y ademas no
    # se activaba nunca al hablar con un extraño: el hablante SI se fia de
    # su palabra, lo que pasa es que el otro no la conoce. Solo el fracaso
    # observado distingue esos dos casos.
    if (channel.mode == MODE_LANGUAGE and not approach and not is_past
            and not rec["descrito"] and cat_heard is None
            and speaker.wants_to_speak(cat_s)):
        reparacion = speaker.describe(cat_s, world.spread(rng), forzar=True)
        if reparacion is not None:
            form, rec["descrito"], rec["said"] = reparacion, True, "desc"
            rec["signal"] = reparacion
            speaker.energy -= cfg.speak_cost
            c, nuevo = listener.understand_description(
                reparacion, world.spread(rng), world.medio(rng))
            rec["desc_ok"] = c is not None
            rec["concepto_nuevo"] = nuevo
            if c is not None:
                cat_heard = c
                approach = listener.decide_approach(cat_heard, place_heard)

    rec["acted"] = approach
    optimal = (thing.payoff - thing.travel) > 0
    rec["optimal"] = optimal
    rec["chose_well"] = (approach == optimal)

    py = listener.perceive(thing)
    cat_l = listener.concepts.categorize(py)

    if approach:
        listener.gain(-thing.travel)
        listener.learn_place(thing.place, thing.travel)
        listener.gain(thing.payoff)
        listener.learn_value(cat_l, thing.payoff, py)
        _kin_payback(speaker, thing.payoff - thing.travel,
                     not listener.alive, cfg)
        # sucede algo con consecuencias visibles, y los dos lo presencian:
        # o el otro se alimenta, o el otro se intoxica. Son sucesos
        # distintos porque se ven distintos.
        act = COMIO if thing.payoff >= 0 else DAÑO
        for w, own in ((speaker, cat_s), (listener, cat_l)):
            w.remember(act, own, None, thing.place, gen, abs(thing.payoff))
            w.learn_role(act, 0, thing.payoff)
    else:
        _uptake_feedback(speaker, form, msg, cfg)

    # co-observacion
    if rec["descrito"]:
        # co-observacion de una descripcion: ahora se de que hablaba, asi
        # que puedo quedarme con sus piezas
        listener.learn_description(form, cat_l, py)
        speaker.learn_description(form, cat_s, px)
        if cat_heard is not None and cat_heard in listener.concepts.provisional:
            listener.concepts.confirm(cat_heard)
        acc.ground("descripcion")
    elif form:
        if is_past:
            _teach_past(listener, speaker, form, msg, memrec, acc,
                        quoted=rec["quoted"])
        else:
            listener.gram.observe(form, (HAY, cat_l, None, thing.place, NOW),
                                  py, speaker.id)
            speaker.gram.observe(form, (HAY, cat_s, None, thing.place, NOW),
                                 px, speaker.id)
            acc.ground("presente")

    return rec


def _uptake_feedback(speaker, form, msg, cfg):
    """El hablante ve si el otro reacciono. Eso si es observable."""
    if not form or msg is None or msg[4] == BEFORE or msg[1] is None:
        return
    v = speaker.value.get(msg[1])
    if v is None or abs(v) * cfg.kin_share <= cfg.speak_threshold:
        return
    speaker.gram.penalize(form, msg, cfg.uptake_penalty)


# ---------------------------------------------------------------------
# ALARMA: hay un depredador. La decision se toma ANTES de verlo.
# ---------------------------------------------------------------------

def alarm_episode(world, speaker, listener, channel, cfg, rng, gen, acc):
    thing = world.sample_predator()
    rec = {"type": "alarm", "kind": thing.kind.name, "place": thing.place,
           "afford": thing.affordance, "signal": None, "said": None,
           "acted": False, "optimal": True, "chose_well": None,
           "understood": False, "parsed": None, "novel": None,
           "past": False, "testimony": False, "death": False}

    # centinela: lo ve de lejos y no corre riesgo. Por eso puede avisar.
    px = speaker.perceive(thing)
    cat_s = speaker.concepts.categorize(px)
    msg = (MATO, cat_s, None, thing.place, NOW)
    if speaker.wants_to_speak(cat_s):
        rec["novel"] = not speaker.gram.knows_whole(msg)
        form, how = channel.transmit(speaker, msg)
    else:
        form, how = None, None
    rec["signal"], rec["said"] = form, how

    heard = parsed = None
    if form:
        heard, parsed = listener.gram.parse(form)
    rec["parsed"] = parsed
    cat_heard = None
    if heard is not None:
        if heard[0] == MATO and heard[4] == NOW:
            cat_heard = heard[1]
        else:
            rec["testimony"] = listener.learn_from_testimony(heard)
    rec["understood"] = cat_heard is not None

    fled = listener.decide_flee(cat_heard)
    rec["acted"] = fled
    rec["chose_well"] = fled

    py = listener.perceive(thing)
    cat_l = listener.concepts.categorize(py)

    if fled:
        listener.gain(-cfg.flee_cost)
        l_delta = -cfg.flee_cost
        if rng.random() < cfg.predator_death_p_fled:
            listener.kill("depredador")
    else:
        l_delta = _maul(listener, cfg, rng)
        listener.learn_value(cat_l, l_delta, py)

    # el suceso: un MATO con el depredador en el primer papel. El daño que
    # se aprende es el del encuentro, no el de haber huido: huir no enseña
    # lo que cuesta el bicho, solo lo que cuesta correr.
    for w, own in ((speaker, cat_s), (listener, cat_l)):
        # un depredador siempre merece recordarse
        w.remember(MATO, own, None, thing.place, gen, cfg.predator_damage)
        w.learn_role(MATO, 0, -cfg.predator_damage)

    if form:
        listener.gram.observe(form, (MATO, cat_l, None, thing.place, NOW),
                              py, speaker.id)
        speaker.gram.observe(form, msg, px, speaker.id)
        acc.ground("presente")
    if not fled:
        _uptake_feedback(speaker, form, msg, cfg)

    rec["death"] = not listener.alive
    _kin_payback(speaker, l_delta, not listener.alive, cfg)
    return rec


def _maul(agent, cfg, rng):
    """Consecuencia de no huir. Devuelve el delta experimentado."""
    if rng.random() < cfg.predator_death_p:
        agent.kill("depredador")
    agent.gain(-cfg.predator_damage)
    return -cfg.predator_damage
