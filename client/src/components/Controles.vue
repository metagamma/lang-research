<script setup>
// Control en vivo.
//
// Cambiar un parametro sobre la marcha es util para explorar y PELIGROSO
// para concluir: la serie deja de ser una sola corrida. Por eso cada
// cambio deja una marca visible en las curvas y el aviso de abajo.
import { ref } from 'vue'

const props = defineProps({ control: Function, conectado: Boolean })
const pausado = ref(false)
const eps = ref(30)
const social = ref(0.4)
const deriva = ref(0.035)

const pausar = () => { pausado.value = !pausado.value
                       props.control({ pausa: pausado.value }) }
const ritmo = () => props.control({ episodios_por_seg: Number(eps.value) })
const parametro = (k, v) => props.control({ parametros: { [k]: Number(v) } })
</script>

<template>
  <div class="ctrl">
    <button @click="pausar">{{ pausado ? 'seguir' : 'pausa' }}</button>
    <label>emisión
      <input type="range" min="2" max="60" v-model="eps" @change="ritmo" />
      {{ eps }}/s
    </label>
    <label>social_exp
      <input type="range" min="0" max="1.5" step="0.1" v-model="social"
             @change="parametro('social_exp', social)" /> {{ social }}
    </label>
    <label>deriva
      <input type="range" min="0.01" max="0.2" step="0.005" v-model="deriva"
             @change="parametro('wander', deriva)" /> {{ deriva }}
    </label>
    <span :class="['estado', conectado ? 'on' : 'off']">
      {{ conectado ? 'en vivo' : 'sin conexión' }}
    </span>
  </div>
</template>

<style scoped>
.ctrl { display: flex; gap: 1.2rem; align-items: center; flex-wrap: wrap;
        font-size: .8rem; padding: .5rem 0; }
label { display: flex; gap: .35rem; align-items: center; }
input[type=range] { width: 90px; }
.estado { margin-left: auto; padding: .1rem .5rem; border-radius: 3px; }
.on { background: rgba(46,158,91,.18); }
.off { background: rgba(217,131,36,.18); }
</style>
