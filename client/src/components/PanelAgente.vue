<script setup>
// Una mente, abierta.
//
// Es el componente que más cuidado pide, y el `CLAUDE.md` de esta carpeta
// dice por qué: debe distinguir SIEMPRE lo que el agente sabe por haberlo
// vivido de lo que sabe de oídas. Esa distinción es la base de media
// investigación del proyecto — es la única prueba de que hay transmisión
// cultural y no solo experiencia repetida. Aplanarla en un solo número la
// haría invisible.
//
// Lo demás que se enseña aquí obedece a la misma disciplina: las
// categorías del agente son NÚMEROS SUYOS, no nombres del mundo. Este
// panel nunca traduce el concepto 3 a «bay bolete», porque el agente no
// sabe eso. Solo sabe que su palabra `sla` acompaña a las cosas que él
// mete en el cajón 3, y que ese cajón le ha dado de comer.
defineProps({ agente: { type: Object, default: null }, tribu: Number })
const emit = defineEmits(['cerrar'])
</script>

<template>
  <aside v-if="agente" class="panel">
    <header>
      <b>agente {{ agente.id }}</b>
      <small v-if="tribu != null">tribu {{ tribu + 1 }}</small>
      <button @click="emit('cerrar')" title="cerrar">×</button>
    </header>

    <div class="barras">
      <div>
        <span>energía</span>
        <div class="tira"><i :style="{ width: Math.min(100, agente.e / 0.4) + '%',
                                       background: agente.e < 10 ? '#c0392b' : '#2e9e5b' }"></i></div>
        <b>{{ agente.e }}</b>
      </div>
      <div>
        <span>edad</span>
        <div class="tira"><i :style="{ width: Math.min(100, agente.edad * 3.3) + '%',
                                       background: '#7f8c8d' }"></i></div>
        <b>{{ agente.edad }}</b>
      </div>
    </div>

    <div class="cifras">
      <div><b>{{ agente.cats }}</b><span>conceptos</span></div>
      <div><b>{{ agente.lex }}</b><span>morfos</span></div>
      <div><b>{{ agente.vig }}</b><span>vigilancia</span></div>
    </div>

    <h4>Cómo sabe lo que sabe</h4>
    <div class="saber">
      <div class="tira doble">
        <i class="viv" :style="{ width: (100 * agente.viv / Math.max(1, agente.viv + agente.oid)) + '%' }"></i>
        <i class="oid" :style="{ width: (100 * agente.oid / Math.max(1, agente.viv + agente.oid)) + '%' }"></i>
      </div>
      <p>
        <b class="cviv">{{ agente.viv }} vividos</b> ·
        <b class="coid">{{ agente.oid }} de oídas</b>
      </p>
      <small>
        Lo vivido lo presenció; lo de oídas se lo contaron. El modelo los
        guarda en compartimentos separados y aprende de ellos a ritmos
        distintos — no son la misma clase de saber.
      </small>
    </div>

    <h4>Lo que sabe decir</h4>
    <ul class="dice">
      <li v-for="([forma, cat, peso], i) in agente.dice" :key="i">
        <code>{{ forma }}</code>
        <span class="flecha">→</span>
        <span class="cat">su concepto {{ cat }}</span>
        <div class="tira mini"><i :style="{ width: (peso * 100) + '%' }"></i></div>
      </li>
      <li v-if="!agente.dice?.length" class="vacio">todavía no dice nada</li>
    </ul>

    <h4>Lo que ha aprendido que vale</h4>
    <ul class="vale">
      <li v-for="([cat, v], i) in agente.vale" :key="i">
        <span class="cat">concepto {{ cat }}</span>
        <b :class="v >= 0 ? 'bien' : 'mal'">{{ v > 0 ? '+' : '' }}{{ v }}</b>
      </li>
      <li v-if="!agente.vale?.length" class="vacio">aún no ha probado nada</li>
    </ul>

    <p class="nota">
      Los conceptos van por número a propósito. Son cajones <b>suyos</b>,
      construidos con lo que ha visto; no se corresponden uno a uno con
      las especies del mundo, y ponerles nuestro nombre daría a entender
      que sabe algo que no sabe.
    </p>
  </aside>
</template>

<style scoped>
.panel { border: 1px solid rgba(128,128,128,.3); border-radius: 6px;
         padding: .7rem .8rem; display: flex; flex-direction: column;
         gap: .5rem; overflow-y: auto; }
header { display: flex; align-items: baseline; gap: .5rem; }
header b { font-size: 1rem; }
header small { opacity: .55; font-size: .74rem; }
header button { margin-left: auto; background: transparent; color: inherit;
                border: none; cursor: pointer; font-size: 1.1rem; opacity: .6; }
h4 { font-size: .76rem; margin: .4rem 0 .1rem; opacity: .75;
     text-transform: uppercase; letter-spacing: .04em; }
.barras > div { display: flex; align-items: center; gap: .5rem; font-size: .76rem; }
.barras span { width: 4.2rem; opacity: .65; }
.barras b { width: 2.4rem; text-align: right; font-size: .78rem; }
.tira { flex: 1; height: 9px; background: rgba(128,128,128,.16);
        border-radius: 3px; overflow: hidden; display: flex; }
.tira i { display: block; height: 100%; background: #4a7fd4;
          transition: width .4s ease; }
.tira.mini { height: 5px; margin-top: 2px; }
.tira.doble i.viv { background: #2e9e5b; }
.tira.doble i.oid { background: #d98324; }
.cifras { display: flex; gap: 1.1rem; }
.cifras div { display: flex; flex-direction: column; }
.cifras b { font-size: 1.05rem; }
.cifras span { font-size: .66rem; opacity: .6; }
.saber p { margin: .25rem 0 .1rem; font-size: .78rem; }
.cviv { color: #2e9e5b; } .coid { color: #d98324; }
.saber small { opacity: .6; font-size: .7rem; line-height: 1.3; display: block; }
ul { list-style: none; margin: 0; padding: 0; display: flex;
     flex-direction: column; gap: .22rem; }
.dice li { font-size: .76rem; }
.dice code { font-family: ui-monospace, monospace; font-size: .86rem; }
.flecha { opacity: .4; margin: 0 .3rem; }
.cat { opacity: .7; }
.vale li { display: flex; justify-content: space-between; font-size: .76rem; }
.vale .bien { color: #2e9e5b; } .vale .mal { color: #c0392b; }
.nota, .vacio { opacity: .6; font-size: .7rem; line-height: 1.35; }
</style>
