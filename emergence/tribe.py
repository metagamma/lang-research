#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tribus y demografia.

La transmision del idioma entre generaciones es HORIZONTAL, no genetica:
el hijo nace sin categorias y sin palabras, y aprende participando en
episodios con adultos que ya las tienen. Lo unico que se hereda es la
vigilancia perceptiva, con mutacion. Evoluciona la facultad; la lengua
se aprende.

Las tribus estan aisladas por defecto (`contact=0`). Con contacto > 0
hay encuentros esporadicos entre miembros de tribus distintas, que es la
via por la que aparecen los prestamos.
"""

from collections import Counter

import numpy as np

from .agent import Agent
from .episodes import forage_episode, alarm_episode


def _vecino(a, pool, rng, k, p_lejano=0.0):
    """Uno de los k mas cercanos — o, de vez en cuando, alguien de MEDIA
    distancia.

    Los encuentros de largo alcance son pocos pero decisivos: sin ellos la
    tribu es una reticula y la convergencia lexica se atasca en un estado
    metaestable con varias convenciones vivas a la vez. Con ellos, una
    convencion mayoritaria puede saltar de un vecindario a otro.

    PERO EL ATAJO NO ES ALEATORIO, y esto importa. La literatura del
    naming game sobre mundos pequeños con geografia mide que «una
    distancia geografica demasiado larga de los atajos inhibe la
    convergencia»: hay una distancia optima, intermedia. Un salto al otro
    extremo del mapa pone en contacto dos vecindarios que no comparten
    nada, y la palabra que llega no se ancla en ninguna parte; un salto de
    media distancia conecta zonas con solape parcial, por donde una
    convencion si puede propagarse.

    Asi que el atajo sale de la BANDA INTERMEDIA del ranking de
    distancias: ni los k vecinos de siempre, ni los del borde del mundo.
    """
    otros = [b for b in pool if b is not a]
    if not otros:
        return None
    if len(otros) <= k:
        return rng.choice(otros)
    P = np.stack([b.pos for b in otros])
    d = ((P - a.pos) ** 2).sum(1)

    if p_lejano and rng.random() < p_lejano:
        orden = np.argsort(d)
        lo = k                                  # mas alla del vecindario
        hi = max(lo + 1, int(len(orden) * 0.75))  # pero no el borde
        banda = orden[lo:hi]
        if len(banda):
            return otros[int(rng.choice(banda.tolist()))]

    idx = np.argpartition(d, k)[:k]
    return otros[int(rng.choice(idx.tolist()))]


class Tribe:
    def __init__(self, index, cfg, rng):
        self.index = index
        self.cfg = cfg
        self.rng = rng
        self.agents = [Agent(cfg, rng, tribe=index)
                       for _ in range(cfg.tribe_size)]
        self.born = cfg.tribe_size
        self.deaths = Counter()

    # ------------------------------------------------------------------
    def living(self):
        return [a for a in self.agents if a.alive]

    def run_episodes(self, world, channel, rng, acc, gen):
        """Dos presupuestos distintos, y la distincion importa.

        FORRAJEO: numero FIJO de oportunidades por generacion. El monte da
        lo que da; cuanta mas gente, menos toca a cada uno. De ahi sale la
        capacidad de carga.

        DEPREDACION: proporcional a la POBLACION. Un acechante viene a por
        alguien, no a por un parche. Atarla al presupuesto de forrajeo era
        un error: al subir la densidad de interaccion para que la lengua
        pudiera converger, subia con ella la mortalidad, y las bandas
        pequeñas —justo las que convergen— se aniquilaban. Dos cosas que
        no tienen por que ir juntas estaban atadas por el codigo.
        """
        cfg = self.cfg
        n_alarm = int(round(len(self.living()) * cfg.alarms_per_agent))
        agenda = [False] * cfg.episodes_per_gen + [True] * n_alarm
        rng.shuffle(agenda)
        for es_alarma in agenda:
            pool = self.living()
            if len(pool) < 2:
                break
            speaker = rng.choice(pool)
            listener = _vecino(speaker, pool, rng, cfg.near_k, cfg.p_lejano)
            if listener is None:
                continue
            if es_alarma:
                rec = alarm_episode(world, speaker, listener, channel,
                                    cfg, rng, gen, acc)
            else:
                rec = forage_episode(world, speaker, listener, channel,
                                     cfg, rng, gen, acc)
            acc.add(rec)
            if acc.recorder is not None:
                acc.recorder.frame(gen, self.index, speaker.id,
                                   listener.id, rec)

    def metabolism_and_death(self):
        cfg = self.cfg
        for a in self.agents:
            if not a.alive:
                continue
            a.wander(self.rng)
            a.age += 1
            a.gain(-cfg.metabolic_cost)
            if a.alive and a.age > cfg.max_age:
                a.kill("vejez")
        for a in self.agents:
            if not a.alive:
                self.deaths[a.cause or "hambre"] += 1
        self.agents = [a for a in self.agents if a.alive]

    def reproduce(self, rng):
        cfg = self.cfg
        newborns = []
        for a in self.agents:
            if len(self.agents) + len(newborns) >= cfg.max_pop:
                break
            if a.energy >= cfg.repro_threshold:
                a.gain(-cfg.repro_cost)
                newborns.append(a.child(rng))
        self.agents.extend(newborns)
        self.born += len(newborns)
        return len(newborns)

    def step(self, world, channel, rng, acc, gen):
        self.run_episodes(world, channel, rng, acc, gen)
        self.metabolism_and_death()
        births = self.reproduce(rng)
        if self.cfg.deriva_fonica:
            self.derivar(rng)
        return births

    def derivar(self, rng):
        """Cambio fonico sistematico. Fase 13.

        LA REGLA ES DE LA TRIBU, NO DEL HABLANTE, y ahi esta todo. Si cada
        agente deformara sus formas por su cuenta, la lengua se
        desintegraria: nadie entenderia a nadie y lo que mediriamos seria
        ruido. Las lenguas reales derivan porque TODA la comunidad aplica
        el mismo cambio a la vez —vita > vida en todo el latin vulgar—, y
        por eso siguen siendo mutuamente inteligibles mientras cambian.

        Asi que se sortea UNA forma de la tribu, se le aplica la lenicion,
        y el resultado se propaga a todos los que la tenian. La lengua se
        desplaza entera.
        """
        from .phonology import deriva
        from .syntax import V_CAT
        vivos = self.living()
        if len(vivos) < 2:
            return
        formas = set()
        for a in vivos:
            for (f, _c) in a.gram.voc[V_CAT].w:
                formas.add(f)
        if not formas:
            return
        vieja = rng.choice(sorted(formas))
        nueva = deriva(vieja, rng, self.cfg.deriva_fonica)
        if nueva == vieja:
            return
        for a in vivos:
            voc = a.gram.voc[V_CAT]
            for (f, c), w in list(voc.w.items()):
                if f == vieja:
                    voc._drop(f, c)
                    voc._set(nueva, c, w)


class Accumulator:
    """Contadores de un tramo de simulacion."""

    def __init__(self, recorder=None):
        self.recorder = recorder   # solo mira y apunta; no interviene
        self.episodes = 0
        self.signals = 0
        self.understood = 0
        self.good = 0
        self.forage = 0
        self.forage_good = 0
        self.alarm = 0
        self.alarm_fled = 0
        self.alarm_deaths = 0
        self.named = Counter()      # kind -> veces que se emitio una señal viendolo
        self.said = Counter()       # como se construyo la señal (Fase 5)
        self.parsed = Counter()     # como se entendio
        self.anchor = Counter()     # como se anclo cada señal (Fase 6)
        self.past = 0               # relatos del pasado
        self.ensenanzas = 0         # «esto se dice X» (metalenguaje)
        self.aprendidas = 0         # ...y el oyente se quedo la palabra
        self.descrito = 0           # enunciados que son descripciones
        self.desc_ok = 0            # ...entendidas por el oyente
        self.conceptos = 0          # ...que instalaron un concepto
        self.quoted = 0             # enunciados con oracion encajada
        self.quote_ok = 0           # ...y entendidos como tales
        self.testimony = 0          # veces que un relato enseño algo
        self.novel = 0              # combinaciones nunca dichas antes
        self.novel_good = 0
        self.known_good = 0
        # regimen cooperativo: episodios que dispararon cada premio/castigo
        self.coop_comm = 0          # comprension mutua + acierto (a ambos)
        self.coop_comp = 0          # compresion (señal compuesta)
        self.coop_penalty = 0       # comunicacion fallida (castigo al hablante)
        self.coop_teach = 0         # se instalo un concepto en el oyente
        self.coop_testimony = 0     # un relato enseño algo del mundo no vivido

    def ground(self, how):
        self.anchor[how] += 1

    def add(self, rec):
        self.episodes += 1
        if rec.get('past'):
            self.past += 1
        if rec.get('testimony'):
            self.testimony += 1
        if rec.get('ensenanza'):
            self.ensenanzas += 1
            if rec.get('aprendida'): self.aprendidas += 1
        if rec.get('descrito'):
            self.descrito += 1
            if rec.get('desc_ok'): self.desc_ok += 1
            if rec.get('concepto_nuevo'): self.conceptos += 1
        if rec.get('quoted'):
            self.quoted += 1
            if rec.get('quote_ok'):
                self.quote_ok += 1
        if rec["signal"]:
            self.signals += 1
            self.named[rec["kind"]] += 1
            if rec.get("said"):
                self.said[rec["said"]] += 1
            if rec.get("parsed"):
                self.parsed[rec["parsed"]] += 1
            # el caso critico de la Fase 5: el hablante nunca habia tenido
            # que nombrar esta combinacion. Componer generaliza; una lista
            # de bloques opacos, no.
            if rec.get("novel"):
                self.novel += 1
                self.novel_good += 1 if rec["chose_well"] else 0
            elif rec.get("novel") is False:
                self.known_good += 1 if rec["chose_well"] else 0
        if rec["understood"]:
            self.understood += 1
        if rec.get("comm_reward"):
            self.coop_comm += 1
        if rec.get("comp_reward"):
            self.coop_comp += 1
        if rec.get("comm_penalty"):
            self.coop_penalty += 1
        if rec.get("teach_reward"):
            self.coop_teach += 1
        if rec.get("testimony_reward"):
            self.coop_testimony += 1
        if rec["chose_well"]:
            self.good += 1
        if rec["type"] == "forage":
            self.forage += 1
            self.forage_good += 1 if rec["chose_well"] else 0
        else:
            self.alarm += 1
            self.alarm_fled += 1 if rec["acted"] else 0
            self.alarm_deaths += 1 if rec.get("death") else 0

    def rates(self):
        e = max(1, self.episodes)
        sig = max(1, self.signals)
        known = max(1, self.signals - self.novel)
        return {
            "episodes": self.episodes,
            "signal_rate": self.signals / e,
            "understood_rate": self.understood / sig,
            "success": self.good / e,
            "forage_success": self.forage_good / max(1, self.forage),
            "flee_rate": self.alarm_fled / max(1, self.alarm),
            "alarm_death_rate": self.alarm_deaths / max(1, self.alarm),
            # Fase 5
            "said_composed": self.said.get("comp", 0) / sig,
            "parsed_composed": self.parsed.get("comp", 0) / sig,
            "parsed_partial": self.parsed.get("part", 0) / sig,
            "novel_rate": self.novel / sig,
            "past_rate": self.past / e,
            "meta_rate": self.ensenanzas / e,
            "meta_learned": self.aprendidas / max(1, self.ensenanzas),
            "desc_rate": self.descrito / e,
            "desc_understood": self.desc_ok / max(1, self.descrito),
            "concepts_installed": self.conceptos / max(1, self.descrito),
            "quote_rate": self.quoted / e,
            "quote_understood": self.quote_ok / max(1, self.quoted),
            "testimony_rate": self.testimony / max(1, self.past),
            "anchor_shared": self.anchor.get("recuerdo compartido", 0) / max(1, self.past),
            "novel_success": self.novel_good / max(1, self.novel),
            "known_success": self.known_good / known,
            # regimen cooperativo (fraccion de episodios)
            "coop_comm_rate": self.coop_comm / e,
            "coop_comp_rate": self.coop_comp / e,
            "coop_penalty_rate": self.coop_penalty / e,
            "coop_teach_rate": self.coop_teach / e,
            "coop_testimony_rate": self.coop_testimony / e,
        }


class Population:
    def __init__(self, n_tribes, cfg, rng):
        self.cfg = cfg
        self.rng = rng
        self.tribes = [Tribe(i, cfg, rng) for i in range(n_tribes)]

    def living(self):
        return [a for t in self.tribes for a in t.living()]

    def extinct(self):
        return len(self.living()) == 0

    def contact_round(self, world, channel, rng, acc, gen):
        cfg = self.cfg
        if cfg.contact <= 0 or len(self.tribes) < 2:
            return
        for _ in range(cfg.contact):
            i, j = rng.sample(range(len(self.tribes)), 2)
            a = self.tribes[i].living()
            b = self.tribes[j].living()
            if not a or not b:
                continue
            rec = forage_episode(world, rng.choice(a), rng.choice(b),
                                 channel, cfg, rng, gen, acc)
            acc.add(rec)

    def step(self, world, channel, rng, gen, recorder=None):
        acc = Accumulator(recorder)
        births = 0
        for t in self.tribes:
            births += t.step(world, channel, rng, acc, gen)
        self.contact_round(world, channel, rng, acc, gen)
        return acc, births

    # -- resumenes -----------------------------------------------------
    def summary(self):
        alive = self.living()
        if not alive:
            return {"pop": 0, "energy": 0.0, "vigilance": 0.0,
                    "categories": 0.0, "lexicon": 0.0, "age": 0.0}
        n = len(alive)
        return {
            "pop": n,
            "energy": sum(a.energy for a in alive) / n,
            "vigilance": sum(a.vigilance for a in alive) / n,
            "categories": sum(len(a.concepts) for a in alive) / n,
            "lexicon": sum(len(a.lex.strong_pairs()) for a in alive) / n,
            "age": sum(a.age for a in alive) / n,
        }

    def deaths(self):
        c = Counter()
        for t in self.tribes:
            c.update(t.deaths)
        return c
