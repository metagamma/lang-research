<script setup>
// La crónica: lo que le pasa a la gente, contado.
//
// Las curvas dicen que el 62% acierta. Esto dice que el agente 14 se
// intoxicó con una seta que su vecino le había nombrado bien. Son los
// mismos datos y no cuentan lo mismo: uno se mide, el otro se sigue.
//
// El nombre de la especie que aparece aquí es conocimiento NUESTRO, no
// del agente. Va porque si no, no hay nada que leer — pero conviene no
// olvidar que el agente solo sabe que su palabra acompaña a ciertas
// cosas.
import { computed, ref } from 'vue'

const props = defineProps({ sucesos: { type: Array, default: () => [] } })

const filtro = ref('todo')

const TIPO = {
  comio: { icono: '●', color: '#2e9e5b', etiqueta: 'comió' },
  veneno: { icono: '✕', color: '#c0392b', etiqueta: 'se intoxicó' },
  huyo: { icono: '↯', color: '#8e44ad', etiqueta: 'huyó' },
  muerte: { icono: '✕', color: '#8e44ad', etiqueta: 'murió' },
  enseno: { icono: '✎', color: '#2980b9', etiqueta: 'enseñó' },
  describio: { icono: '≈', color: '#d98324', etiqueta: 'describió' },
  perdida: { icono: '·', color: '#8a8f98', etiqueta: 'no se entendió' },
  nacen: { icono: '+', color: '#2e9e5b', etiqueta: 'nacimientos' },
  mueren: { icono: '−', color: '#c0392b', etiqueta: 'muertes' },
}

const GRUPOS = {
  todo: null,
  vida: ['comio', 'veneno', 'huyo', 'muerte', 'nacen', 'mueren'],
  lengua: ['enseno', 'describio', 'perdida'],
}

const filas = computed(() => {
  const g = GRUPOS[filtro.value]
  return g ? props.sucesos.filter(s => g.includes(s.tipo)) : props.sucesos
})

// Cuánto de lo que pasa es lengua y cuánto es supervivencia. Sale de la
// misma lista, así que es honesto: no es una métrica aparte.
const reparto = computed(() => {
  const n = props.sucesos.length
  if (!n) return null
  const leng = props.sucesos.filter(s => GRUPOS.lengua.includes(s.tipo)).length
  const mal = props.sucesos.filter(s => s.tipo === 'veneno').length
  return { n, leng, mal }
})
</script>

<template>
  <div class="cronica">
    <div class="mandos">
      <button v-for="k in Object.keys(GRUPOS)" :key="k"
              :class="{ on: filtro === k }" @click="filtro = k">{{ k }}</button>
      <small v-if="reparto">
        {{ reparto.leng }} de {{ reparto.n }} sobre la lengua ·
        {{ reparto.mal }} intoxicaciones
      </small>
    </div>

    <p v-if="!filas.length" class="vacio">Esperando que pase algo…</p>

    <ol class="lista">
      <li v-for="(s, i) in filas" :key="i"
          :style="{ opacity: 1 - Math.min(0.65, i * 0.02) }">
        <span class="icono" :style="{ color: (TIPO[s.tipo] || {}).color }">
          {{ (TIPO[s.tipo] || {}).icono || '·' }}
        </span>
        <span class="texto">{{ s.texto }}</span>
        <small v-if="s.t >= 0">t{{ s.t + 1 }}</small>
        <small class="gen">g{{ s.g }}</small>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.cronica { display: flex; flex-direction: column; gap: .4rem; min-height: 0; }
.mandos { display: flex; gap: .3rem; align-items: center; flex-wrap: wrap; }
.mandos button { background: transparent; color: inherit; cursor: pointer;
                 border: 1px solid rgba(128,128,128,.3); border-radius: 3px;
                 padding: .12rem .5rem; font-size: .74rem; }
.mandos button.on { border-color: currentColor; font-weight: 600; }
.mandos small { margin-left: auto; opacity: .55; font-size: .7rem; }
.lista { list-style: none; margin: 0; padding: 0; overflow-y: auto;
         display: flex; flex-direction: column; gap: .12rem; }
.lista li { display: flex; gap: .4rem; align-items: baseline;
            font-size: .78rem; line-height: 1.35; }
.icono { width: .8rem; flex: none; text-align: center; }
.texto { flex: 1; }
.lista small { opacity: .42; font-size: .66rem; font-family: ui-monospace, monospace; }
.gen { min-width: 2.4rem; text-align: right; }
.vacio { opacity: .6; font-size: .78rem; }
</style>
