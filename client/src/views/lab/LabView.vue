<script setup>
// Vista cientifica. Sin animacion: numeros.
import { computed } from 'vue'
import { instantanea, serie, cortes, gen, tic } from '../../core/state.js'
import MetricCurve from '../../components/MetricCurve.vue'
import VariantBars from '../../components/VariantBars.vue'

const METRICAS = [
  ['success', 'decisiones acertadas'],
  ['pop', 'poblacion'],
  ['signal_rate', 'episodios con señal'],
  ['said_composed', 'señales compuestas'],
  ['past_rate', 'enunciados sobre el pasado'],
  ['desc_rate', 'descripciones'],
]

const tribus = computed(() => { tic.value; return instantanea.value?.tribus || [] })
const marcas = computed(() => cortes.value.map(c => c.g))
</script>

<template>
  <section class="lab">
    <p v-if="!instantanea" class="esperando">Esperando datos…</p>

    <template v-else>
      <div class="cifras">
        <div><b>{{ gen }}</b><span>generación</span></div>
        <div><b>{{ instantanea.pop }}</b><span>población</span></div>
        <div><b>{{ instantanea.coherencia?.toFixed(3) }}</b><span>coherencia</span></div>
        <div><b>{{ instantanea.topsim?.toFixed(3) }}</b><span>composicionalidad</span></div>
      </div>

      <p v-if="marcas.length" class="aviso">
        {{ marcas.length }} cambio(s) de parámetro en vivo. La serie
        <b>deja de ser comparable</b> a ambos lados de cada marca: no es
        una sola corrida.
      </p>

      <div class="curvas">
        <MetricCurve v-for="[k, t] in METRICAS" :key="k"
                     :serie="serie" :clave="k" :titulo="t" :marcas="marcas" />
      </div>

      <h2>Reparto de variantes por tipo</h2>
      <p class="nota">
        Donde se ve si la lengua convergió. Varias barras parejas para una
        misma cosa = convenciones rivales que no se deshacen.
      </p>
      <div class="tribus">
        <div v-for="(t, i) in tribus" :key="i" class="tribu">
          <h3>Tribu {{ i + 1 }}
            <small>{{ t?.n }} agentes · coherencia {{ t?.coherencia?.toFixed(3) }}</small>
          </h3>
          <VariantBars v-if="t" :nombres="t.nombres" />
          <p v-else class="perdida">extinguida</p>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.cifras { display: flex; gap: 2rem; margin-bottom: 1rem; }
.cifras div { display: flex; flex-direction: column; }
.cifras b { font-size: 1.6rem; }
.cifras span { opacity: .65; font-size: .8rem; }
.curvas { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
.tribus { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; }
.aviso { border-left: 3px solid var(--sig-fallo); padding-left: .7rem; }
.nota, .esperando { opacity: .7; }
.perdida { opacity: .5; font-style: italic; }
small { font-weight: 400; opacity: .6; }
</style>
