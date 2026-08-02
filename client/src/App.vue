<script setup>
// Esqueleto. Ver SPEC.md antes de rellenarlo.
import { ref } from 'vue'

const vista = ref('lab')   // 'lab' primero: valida que los datos llegan
</script>

<template>
  <header class="barra">
    <h1>Emergencia del lenguaje</h1>
    <nav>
      <button :class="{ on: vista === 'world' }" @click="vista = 'world'">
        Mundo
      </button>
      <button :class="{ on: vista === 'lab' }" @click="vista = 'lab'">
        Laboratorio
      </button>
    </nav>
  </header>

  <main>
    <p class="pendiente">
      Sin datos. Falta el exportador <code>--export</code> en
      <code>emergence/run.py</code>; ver <code>SPEC.md</code>.
    </p>
  </main>
</template>

<style scoped>
.barra { display: flex; justify-content: space-between; align-items: center; }
.on { font-weight: 600; }
.pendiente { opacity: .7; }
</style>
