<script setup>
// Oraciones rescatadas de la simulación, segmentadas y glosadas.
//
// Una cadena como `fikrodema` no le dice nada a quien la ve: parece ruido.
// Partida en `fi + kro + dema` y glosada como (fruto · loma · antes) se ve
// que es una lengua — que hay piezas reutilizables y un orden.
//
// La glosa usa nombres latentes (`fruto_dulce`), que son conocimiento
// NUESTRO, no del agente. Va marcado como tal: el agente no sabe que su
// `fi` significa «fruto dulce», solo que va con esas cosas.
defineProps({ oraciones: Array })

const COLOR = {
  cosa: '#4a7fd4', lugar: '#2e9e5b', accion: '#c25bb0',
  tiempo: '#d98324', cita: '#7b6cd9', cosa2: '#4a7fd4',
}
</script>

<template>
  <div class="oraciones">
    <p v-if="!oraciones.length" class="vacio">
      Esperando oraciones compuestas…
    </p>
    <article v-for="(o, i) in oraciones" :key="i" :class="{ perdida: !o.und }">
      <div class="cadena">
        <span v-for="([morfo, ranura], j) in o.piezas" :key="j"
              class="pieza" :style="{ borderColor: COLOR[ranura] || '#888' }">
          {{ morfo }}<em>{{ ranura }}</em>
        </span>
      </div>
      <div class="glosa">
        {{ o.accion }} · <b>{{ o.cosa }}</b> · {{ o.lugar }} · {{ o.tiempo }}
        <small>tribu {{ o.t + 1 }} · {{ o.orden }} · gen {{ o.g }}
          <template v-if="!o.und"> · no le entendieron</template>
        </small>
      </div>
    </article>
    <p class="nota">
      Los nombres de la glosa (<code>fruto_dulce</code>) son etiquetas
      <b>nuestras</b>, para poder leer. El agente solo sabe que su morfo
      acompaña a ciertas cosas.
    </p>
  </div>
</template>

<style scoped>
.oraciones { display: flex; flex-direction: column; gap: .55rem; }
article { border-left: 2px solid rgba(128,128,128,.3); padding-left: .6rem; }
article.perdida { opacity: .5; }
.cadena { display: flex; gap: 3px; flex-wrap: wrap; align-items: flex-end; }
.pieza { border-bottom: 2px solid; padding: 0 3px; font-family: ui-monospace, monospace;
         font-size: .95rem; display: flex; flex-direction: column; }
.pieza em { font-style: normal; font-size: .6rem; opacity: .6;
            font-family: system-ui, sans-serif; }
.glosa { font-size: .78rem; opacity: .85; margin-top: .15rem; }
.glosa small { opacity: .6; margin-left: .4rem; }
.vacio, .nota { opacity: .6; font-size: .78rem; }
.nota { margin-top: .6rem; }
</style>
