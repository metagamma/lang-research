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

from .agent import Agent
from .episodes import forage_episode, alarm_episode


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
            speaker, listener = rng.sample(pool, 2)
            if es_alarma:
                rec = alarm_episode(world, speaker, listener, channel,
                                    cfg, rng, gen, acc)
            else:
                rec = forage_episode(world, speaker, listener, channel,
                                     cfg, rng, gen, acc)
            acc.add(rec)

    def metabolism_and_death(self):
        cfg = self.cfg
        for a in self.agents:
            if not a.alive:
                continue
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
        return births


class Accumulator:
    """Contadores de un tramo de simulacion."""

    def __init__(self):
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
        self.descrito = 0           # enunciados que son descripciones
        self.desc_ok = 0            # ...entendidas por el oyente
        self.conceptos = 0          # ...que instalaron un concepto
        self.quoted = 0             # enunciados con oracion encajada
        self.quote_ok = 0           # ...y entendidos como tales
        self.testimony = 0          # veces que un relato enseño algo
        self.novel = 0              # combinaciones nunca dichas antes
        self.novel_good = 0
        self.known_good = 0

    def ground(self, how):
        self.anchor[how] += 1

    def add(self, rec):
        self.episodes += 1
        if rec.get('past'):
            self.past += 1
        if rec.get('testimony'):
            self.testimony += 1
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
            "desc_rate": self.descrito / e,
            "desc_understood": self.desc_ok / max(1, self.descrito),
            "concepts_installed": self.conceptos / max(1, self.descrito),
            "quote_rate": self.quoted / e,
            "quote_understood": self.quote_ok / max(1, self.quoted),
            "testimony_rate": self.testimony / max(1, self.past),
            "anchor_shared": self.anchor.get("recuerdo compartido", 0) / max(1, self.past),
            "novel_success": self.novel_good / max(1, self.novel),
            "known_success": self.known_good / known,
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

    def step(self, world, channel, rng, gen):
        acc = Accumulator()
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
