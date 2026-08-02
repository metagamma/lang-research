<script setup>
import { onMounted, ref } from 'vue'
import { crearFuente } from './core/source.js'
import { manejadores, conectado, terminado, tribusPerdidas } from './core/state.js'
import LabView from './views/lab/LabView.vue'
import WorldView from './views/world/WorldView.vue'
import Controles from './components/Controles.vue'

const vista = ref('lab')
const fuente = crearFuente(manejadores)
onMounted(() => fuente.arrancar().catch(e => console.warn('sin backend', e)))
</script>

<template>
  <header>
    <h1>Emergencia del lenguaje</h1>
    <nav>
      <button :class="{ on: vista === 'world' }" @click="vista = 'world'">Mundo</button>
      <button :class="{ on: vista === 'lab' }" @click="vista = 'lab'">Laboratorio</button>
    </nav>
  </header>

  <Controles :control="fuente.control" :conectado="conectado" />

  <p v-if="terminado" class="fin">Simulación terminada: {{ terminado.razon }}</p>
  <p v-if="tribusPerdidas.length" class="fin">
    Tribu(s) extinguida(s): {{ tribusPerdidas.join(', ') }} — el mundo sigue
    con las que quedan.
  </p>

  <main>
    <WorldView v-show="vista === 'world'" />
    <LabView v-show="vista === 'lab'" />
  </main>

  <footer>
    Esto es una corrida <b>para mirar</b>, no un experimento: sin semillas,
    sin réplicas y sin brazos de control. Para medir están
    <code>ablation</code>, <code>social</code>, <code>bottleneck</code> y
    <code>audit</code>.
  </footer>
</template>

<style scoped>
header { display: flex; justify-content: space-between; align-items: baseline; }
h1 { font-size: 1.15rem; margin: 0; }
.on { font-weight: 600; }
.fin { border-left: 3px solid var(--sig-fallo); padding-left: .7rem; font-size: .85rem; }
footer { margin-top: 2rem; padding-top: .8rem; font-size: .78rem; opacity: .65;
         border-top: 1px solid rgba(128,128,128,.25); }
</style>
