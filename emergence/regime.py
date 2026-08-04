#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regimen dinamico del premio — el lazo cerrado que ajusta la presion.

El regimen cooperativo (premio en energia por entenderse, comprimir y
enseñar) con premios FIJOS resulto casi inerte: con la banda clavada en
`max_pop` el premio de energia apenas se traduce en reproduccion
diferencial. Este modulo lo hace DINAMICO — «que se ajuste solo a premiar
la comprension y la emergencia del lenguaje» — sin tocar ni un peso lexico.
Todo sigue siendo canal de ENERGIA (fitness): la Regla 2 no se roza.

Tres fuentes de dinamismo, cada una ablacionable desde `config.py`:

  1. INFORMACION (por episodio, en `episodes.py`): el premio de comprension
     escala con lo DECISIVO que fue el mensaje. Un aviso que resuelve una
     decision de alto riesgo paga; confirmar lo obvio, casi nada. Se agota
     solo para lo rutinario segun la lengua mejora.

  2. CONTROLADOR de kappa (aqui): una ganancia global multiplica todos los
     premios. Cada generacion persigue un setpoint ASPIRACIONAL — el mejor
     valor de comprension visto, por un factor — asi que la presion sube
     cuando la lengua se estanca y baja cuando alcanza su frontera. Es una
     diana movil: de ahi el dinamismo.

  3. MADUREZ (aqui, escalar `mu`): con lengua inmadura pesa entenderse a
     secas; con lengua madura suben compresion y enseñanza, que solo tienen
     sentido cuando ya hay piezas que reutilizar.

La seleccion competitiva (Capa 3) vive en `tribe.reproduce`; usa el
`comm_score` que los enganches de `episodes.py` acumulan.
"""


class Regime:
    """Estado dinamico del premio para una corrida. Mutable, barato.

    Se crea una vez por simulacion y se cuelga de `channel.regime` para que
    cada episodio lea los premios EFECTIVOS sin cambiar ninguna firma. El
    controlador lo actualiza una vez por generacion desde las tasas del
    acumulador.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.kappa = 1.0            # ganancia global sobre los premios
        self.best = 0.0            # mejor INDICE de emergencia visto (rolling max)
        self.setpoint = 0.0        # diana actual del controlador
        self.mu = 0.0              # madurez de la lengua (EWMA del indice)
        self.index = 0.0           # ultimo indice compuesto de emergencia

    # -- lectura desde los episodios -----------------------------------
    def _mature(self, base_comp, base_teach):
        """Reparte peso hacia compresion/enseñanza segun madurez (Capa 4).

        Con `dyn_curriculum=0` no reordena nada: devuelve los pesos planos.
        Con curriculum, la compresion y la enseñanza valen `mu` (0..1): no
        se premia comprimir una lengua que aun no tiene piezas.
        """
        c = self.cfg.dyn_curriculum
        if not c:
            return base_comp, base_teach
        w = (1.0 - c) + c * self.mu
        return base_comp * w, base_teach * w

    # INTERRUPTOR MAESTRO. `cooperative=True` por defecto: el regimen es la
    # mitad de la combinacion ganadora (sinergico con `lex_collapse`, ver la
    # nota en config.py). Con `cooperative=False` todos los premios quedan a 0
    # y el regimen entero se ablaciona limpio — lo que hacen `run._pure` y la
    # ablacion falsable.
    def comm(self, info=1.0):
        """Premio efectivo de comprension mutua, ponderado por informacion."""
        if not self.cfg.cooperative:
            return 0.0
        w = 1.0
        if self.cfg.info_reward:
            # info in [0,1]: cuanto decidio el mensaje. Mezcla con un piso
            # para que un mensaje correcto siempre pague algo.
            w = (1.0 - self.cfg.info_reward) + self.cfg.info_reward * info
        return self.cfg.comm_reward * self.kappa * w

    def penalty(self):
        if not self.cfg.cooperative:
            return 0.0
        return self.cfg.comm_penalty * self.kappa

    def compression(self):
        if not self.cfg.cooperative:
            return 0.0
        comp, _ = self._mature(self.cfg.compression_reward, self.cfg.teach_reward)
        return comp * self.kappa

    def teach(self):
        if not self.cfg.cooperative:
            return 0.0
        _, teach = self._mature(self.cfg.compression_reward, self.cfg.teach_reward)
        return teach * self.kappa

    def testimony(self):
        if not self.cfg.cooperative:
            return 0.0
        return self.cfg.testimony_reward * self.kappa

    # -- actualizacion por el controlador ------------------------------
    def update(self, index):
        """Cierra el lazo: ajusta kappa hacia el setpoint aspiracional.

        `index` es el INDICE COMPUESTO DE EMERGENCIA — comprension +
        coherencia + composicionalidad, promediado — que la poblacion
        alcanzo esta generacion. El controlador no persigue una sola
        metrica sino el conjunto de las tres cosas que definen que hay
        lengua: que se entiendan, que compartan convenciones y que compongan.

        El setpoint persigue el MEJOR indice visto por `dyn_aspiration`, asi
        que:

          - si el indice esta por debajo de su frontera -> kappa sube
          - si la alcanza o la supera                    -> kappa baja

        kappa queda clampado para que el lazo no se dispare. Con
        `dyn_control=0` el controlador se apaga y kappa se queda en 1.0.
        """
        cfg = self.cfg
        self.index = index
        # madurez: EWMA del indice, para el curriculum (Capa 4)
        self.mu = 0.8 * self.mu + 0.2 * index
        if not cfg.dyn_control:
            self.setpoint = index
            return self.kappa
        self.best = max(self.best, index)
        self.setpoint = self.best * cfg.dyn_aspiration
        err = self.setpoint - index
        # Empuje proporcional al deficit MENOS una FUGA hacia 1.0. Sin la
        # fuga el lazo satura: como la diana aspiracional va siempre por
        # encima del mejor valor, el error nunca se anula y kappa treparia
        # hasta el techo y se quedaria pegado — que no es dinamico, es
        # maximo constante. Con la fuga hay equilibrio: kappa se asienta
        # donde `η·err = leak·(kappa−1)`, alto cuando el indice flojea,
        # de vuelta a 1 cuando remonta.
        leak = 0.5 * cfg.dyn_control
        self.kappa += cfg.dyn_control * err - leak * (self.kappa - 1.0)
        self.kappa = min(cfg.dyn_kappa_max, max(cfg.dyn_kappa_min, self.kappa))
        return self.kappa
