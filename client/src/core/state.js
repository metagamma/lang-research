// Estado compartido. Lo minimo: un composable, sin Pinia.
//
// `shallowRef` para lo que cambia entero y a menudo (los episodios son
// decenas de miles de objetos planos que nunca se mutan): reactividad
// profunda sobre eso seria un desperdicio caro.

import { ref, shallowRef } from 'vue'
import { Anillo, Serie } from './buffers.js'

export const mundo = shallowRef(null)
export const instantanea = shallowRef(null)
export const episodios = new Anillo(2000)
export const serie = new Serie(300, 10)
export const cortes = ref([])
export const tribusPerdidas = ref([])
export const gen = ref(0)
export const conectado = ref(false)
export const terminado = ref(null)
export const tic = ref(0)          // fuerza redibujado sin reactividad profunda

export const manejadores = {
  mundo: m => { mundo.value = m },
  instantanea: s => {
    instantanea.value = s
    gen.value = s.g
    if (s.cortes) cortes.value = s.cortes
    if (s.tribus_perdidas) tribusPerdidas.value = s.tribus_perdidas
    conectado.value = true
  },
  generacion: f => {
    serie.push(f)
    gen.value = f.g
    tic.value++
  },
  episodio: e => { episodios.push(e); tic.value++ },
  corte: c => { cortes.value = [...cortes.value, c] },
  tribu_perdida: t => { tribusPerdidas.value = [...tribusPerdidas.value, t.tribu] },
  fin: f => { terminado.value = f },
  corte_conexion: () => { conectado.value = false },
}
