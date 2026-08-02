#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emision en vivo — la simulacion corriendo indefinidamente, observable.

Un hilo corre generaciones sin parar; otro sirve lo que ocurre. Entre los
dos, colas acotadas.

EL OBSERVADOR NO ALTERA LA CORRIDA
----------------------------------
Regla que no se negocia. El hilo de simulacion **nunca se bloquea** por el
transporte: si la cola esta llena se descarta y se sigue. Que haya cero
navegadores mirando, o uno lento, no puede cambiar ni un episodio.

Es la misma disciplina que `CLAUDE.md` impone a las metricas — medir no
altera — aplicada al transporte. Si un cliente lento pudiera frenar la
simulacion, tendriamos un problema de Heisenberg en el modelo mismo.

Los descartes se CUENTAN y se emiten. Un visor que pierde datos en
silencio miente sobre lo que enseña.

TRES CANALES A RITMOS DISTINTOS
-------------------------------
Son ~800 episodios por segundo. Ni el navegador puede dibujarlos ni el
ojo verlos. El servidor decide que emite:

    episodio     muestreado a ~30/s   -> vista de mundo
    generacion   ~1 por generacion    -> curvas
    instantanea  cada N generaciones  -> tablas y estado completo

ESTO NO ES UN EXPERIMENTO
-------------------------
Una corrida indefinida y sin semilla no tiene replicacion, ni intervalos,
ni brazos de control. Sirve para MIRAR. Para MEDIR estan `ablation`,
`social`, `bottleneck` y `audit`, que corren por lotes con semillas.
"""

import json
import threading
import time
from collections import deque

from .config import Config
from .episodes import Channel, MODE_LANGUAGE
from .events import ACTION_NAME, TENSE_NAME
from .export import snapshot
from .syntax import ORDER_NAME
from .fastrand import FastRandom
from .metrics import (concept_alignment, lexical_coherence, lexicon_stats,
                      mean, prediction_score, topographic_similarity)
from .tribe import Population
from .world import World, load_spec

PROBE_SEED = 20260801


class Bus:
    """Colas acotadas, una por canal. Publicar nunca bloquea."""

    def __init__(self, tope=256):
        self.tope = tope
        self._colas = {}
        self._lock = threading.Lock()
        self.descartes = 0
        self.seq = 0

    def suscribir(self):
        """Una cola nueva para un cliente. Devuelve su identificador."""
        with self._lock:
            cid = self.seq = self.seq + 1
            self._colas[cid] = deque(maxlen=self.tope)
            return cid

    def cancelar(self, cid):
        with self._lock:
            self._colas.pop(cid, None)

    def publicar(self, canal, dato):
        """Encolar para todos. Si alguna cola esta llena, se pierde lo viejo.

        `deque(maxlen=)` descarta por la izquierda sin bloquear, que es
        justo lo que queremos: preferimos perder lo antiguo a frenar la
        simulacion.
        """
        msg = (canal, dato)
        with self._lock:
            for q in self._colas.values():
                if len(q) == q.maxlen:
                    self.descartes += 1
                q.append(msg)

    def recoger(self, cid, maximo=64):
        with self._lock:
            q = self._colas.get(cid)
            if not q:
                return []
            out = []
            while q and len(out) < maximo:
                out.append(q.popleft())
            return out

    def hay_clientes(self):
        with self._lock:
            return bool(self._colas)


class Vivo:
    """La simulacion corriendo indefinidamente.

    No duplica `simulate()`: reutiliza `Population.step`, el acumulador y
    las metricas de siempre. Lo unico que añade es que no termina, que
    publica, y que sabe que hacer cuando una tribu se extingue.
    """

    def __init__(self, cfg, n_tribes, seed, bus,
                 episodios_por_seg=30, snap_cada=10):
        self.cfg = cfg
        self.bus = bus
        self.n_tribes = n_tribes
        self.snap_cada = snap_cada
        self.episodios_por_seg = episodios_por_seg

        self.spec = load_spec(cfg.world)
        cfg.dim, cfg.n_places = self.spec.dim, self.spec.n_places
        self.world = World(FastRandom(seed * 7919 + 11), self.spec)
        self.rng = FastRandom(seed)
        self.rng_metric = FastRandom(PROBE_SEED + 1)
        self.probes = self.world.probe_set(FastRandom(PROBE_SEED), per_kind=10)
        self.channel = Channel(MODE_LANGUAGE, cfg, FastRandom(seed * 104729 + 7))
        self.pop = Population(n_tribes, cfg, self.rng)

        self.gen = 0
        self.pausa = False
        self.parar = False
        self.estado = {}          # ultima instantanea, para /state
        self.cortes = []          # generaciones donde se toco un parametro
        self.tribus_perdidas = []
        self._ultimo_envio = 0.0
        self._ultima_frase = 0.0

    # -- grabador de episodios (interfaz de Recorder) -------------------
    def frame(self, gen, tribe, sp, li, rec):
        """Lo llama la simulacion en cada episodio. Debe ser BARATO.

        Se muestrea por reloj, no por contador: asi el ritmo que ve el
        navegador es estable aunque la simulacion acelere o frene.
        """
        ahora = time.monotonic()
        if ahora - self._ultimo_envio < 1.0 / max(1, self.episodios_por_seg):
            return
        self._ultimo_envio = ahora
        d = {"g": gen, "t": tribe, "sp": sp, "li": li,
             "k": rec.get("kind"), "pl": rec.get("place")}
        for clave, campo in (("sig", "signal"), ("mode", "said")):
            if rec.get(campo):
                d[clave] = rec[campo]
        for clave, campo in (("und", "understood"), ("act", "acted"),
                             ("ok", "chose_well"), ("past", "past"),
                             ("desc", "descrito")):
            if rec.get(campo):
                d[clave] = 1
        if rec.get("type") == "alarm":
            d["alarm"] = 1
        # posiciones: la Fase 9 les dio coordenadas de verdad
        d["p"] = self._posiciones(tribe, sp, li)
        self.bus.publicar("episodio", d)
        self._quiza_frase(ahora, gen, tribe, sp, rec, d)

    def _quiza_frase(self, ahora, gen, tribe, sp, rec, d):
        """Rescatar una oracion compuesta, segmentada y glosada.

        Una cadena como `fikrodema` no dice nada a quien la ve. Partida en
        `fi + kro + dema` y glosada como (fruto, loma, antes) se ve que es
        una lengua y no ruido. Solo se emite una por segundo: son para
        leerlas, no para contarlas.
        """
        if rec.get("said") != "comp" or ahora - self._ultima_frase < 1.0:
            return
        hablante = next((a for a in self.pop.tribes[tribe].living()
                         if a.id == sp), None)
        if hablante is None or not hasattr(hablante.gram, "glosar"):
            return
        m = rec.get("_meaning")
        if m is None:
            return
        piezas = hablante.gram.glosar(m)
        if not piezas or len(piezas) < 2:
            return
        self._ultima_frase = ahora
        self.bus.publicar("oracion", {
            "g": gen, "t": tribe, "sp": sp,
            "sig": rec.get("signal"),
            "piezas": [[mo, ra] for mo, ra, _ in piezas],
            "orden": ORDER_NAME[hablante.gram.best_order()],
            "cosa": rec.get("kind"),
            "lugar": self.world.place_names[rec.get("place", 0)],
            "accion": ACTION_NAME.get(m[0], "?"),
            "tiempo": TENSE_NAME.get(m[4], "?"),
            "und": bool(rec.get("understood")),
        })

    def _posiciones(self, tribe, sp, li):
        out = {}
        for a in self.pop.tribes[tribe].living():
            if a.id in (sp, li):
                out[a.id] = [round(float(a.pos[0]), 3),
                             round(float(a.pos[1]), 3)]
        return out

    # -- control --------------------------------------------------------
    def aplicar(self, orden):
        """Cambios en vivo. Cada uno deja una marca en la serie."""
        cambios = {}
        if "pausa" in orden:
            self.pausa = bool(orden["pausa"])
        if "episodios_por_seg" in orden:
            self.episodios_por_seg = max(1, int(orden["episodios_por_seg"]))
        for k, v in (orden.get("parametros") or {}).items():
            if hasattr(self.cfg, k):
                setattr(self.cfg, k, type(getattr(self.cfg, k))(v))
                cambios[k] = v
        if cambios:
            # Un corte invalida la comparacion a ambos lados: la serie deja
            # de ser una sola corrida. El cliente lo pinta y lo advierte.
            self.cortes.append({"g": self.gen, "cambios": cambios})
            self.bus.publicar("corte", {"g": self.gen, "cambios": cambios})
        return {"pausa": self.pausa, "gen": self.gen, "cambios": cambios}

    # -- bucle ----------------------------------------------------------
    def correr(self):
        while not self.parar:
            if self.pausa:
                time.sleep(0.1)
                continue
            self.gen += 1
            acc, _ = self.pop.step(self.world, self.channel, self.rng,
                                   self.gen, self)
            self._revisar_tribus()
            if self.pop.extinct():
                self.bus.publicar("fin", {"g": self.gen,
                                          "razon": "todas las tribus muertas"})
                return
            self._publicar_generacion(acc)
            if self.gen % self.snap_cada == 0:
                self._publicar_instantanea()

    def _revisar_tribus(self):
        """Una tribu vacia se retira; el mundo sigue con las que quedan."""
        for t in self.pop.tribes:
            if not t.living() and t.index not in self.tribus_perdidas:
                self.tribus_perdidas.append(t.index)
                self.bus.publicar("tribu_perdida",
                                  {"g": self.gen, "tribu": t.index})

    def _publicar_generacion(self, acc):
        fila = {"g": self.gen}
        fila.update(self.pop.summary())
        fila.update(acc.rates())
        fila["descartes"] = self.bus.descartes
        self.bus.publicar("generacion", fila)

    def _publicar_instantanea(self):
        vivos = self.pop.living()
        if not vivos:
            return
        fila = {"g": self.gen}
        fila.update(self.pop.summary())
        por_tribu = [lexical_coherence(t.living(), self.world,
                                       self.rng_metric, 6)
                     for t in self.pop.tribes if t.living()]
        fila["coherence"] = mean(por_tribu)
        fila["topsim"] = topographic_similarity(vivos, self.world,
                                                self.rng_metric)
        fila["prediction"] = prediction_score(vivos[:24], self.probes)
        fila["alignment"] = concept_alignment(vivos, self.probes,
                                              self.rng_metric)
        fila.update({("lex_" + k): v
                     for k, v in lexicon_stats(vivos).items()})
        snap = snapshot(self.gen, self.pop, self.world, self.rng_metric, fila)
        snap["cortes"] = self.cortes[-20:]
        snap["tribus_perdidas"] = self.tribus_perdidas
        self.estado = snap
        self.bus.publicar("instantanea", snap)

    def instantanea_actual(self):
        """Para que un cliente que llega tarde no necesite la historia."""
        if not self.estado:
            self._publicar_instantanea()
        return self.estado or {"g": self.gen, "pop": 0}
