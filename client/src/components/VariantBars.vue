<script setup>
// Reparto de palabras rivales por tipo.
//
// Enseña TODAS las variantes, no solo la mayoritaria: dos barras parejas
// para la misma cosa son el fenomeno interesante, no un detalle. Ocultarlo
// presentaria como convergido algo que no lo esta.
defineProps({ nombres: Object })
const PALETA = ['#4a7fd4', '#c25bb0', '#2e9e5b', '#d98324', '#8a8f98', '#7b6cd9']
</script>

<template>
  <table>
    <tr v-for="(vs, tipo) in nombres" :key="tipo">
      <th>{{ tipo }}</th>
      <td>
        <span v-for="([forma, cuota], i) in vs" :key="forma"
              class="v" :style="{ width: (cuota * 100) + '%',
                                  background: PALETA[i % 6] }"
              :title="forma + '  ' + (cuota * 100).toFixed(0) + '%'">
          <em v-if="cuota > 0.22">{{ forma }}</em>
        </span>
      </td>
    </tr>
  </table>
</template>

<style scoped>
table { width: 100%; border-collapse: collapse; font-size: .78rem; }
th { text-align: left; font-weight: 400; opacity: .75; width: 8.5rem;
     padding: 1px 6px 1px 0; }
td { padding: 1px 0; }
.v { display: inline-block; height: 15px; overflow: hidden; vertical-align: middle;
     color: #fff; font-size: .68rem; line-height: 15px; }
em { font-style: normal; padding-left: 3px; }
</style>
