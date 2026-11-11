<script setup lang="ts">
import {computed,ref,onMounted,onUnmounted} from 'vue'
import trace from '../trace.json'
const steps=trace.events
const position=ref(0)
const event=computed(()=>steps[position.value])
const values=trace.input.values
const prev=()=>position.value=Math.max(0,position.value-1)
const next=()=>position.value=Math.min(steps.length-1,position.value+1)
const reset=()=>position.value=0
function onKey(e:KeyboardEvent){
  // Avoid interfering with Slidev navigation and editable fields.
  if(!(e.target instanceof HTMLElement) || !e.target.closest('.trace-player'))return
  if(e.key==='ArrowLeft'){e.stopPropagation();e.preventDefault();prev()}
  if(e.key==='ArrowRight'){e.stopPropagation();e.preventDefault();next()}
}
onMounted(()=>window.addEventListener('keydown',onKey,true))
onUnmounted(()=>window.removeEventListener('keydown',onKey,true))
</script>

<template>
<section class="trace-player" tabindex="0" aria-label="算法逐步演示，聚焦后可使用左右方向键">
  <div class="track">
    <div v-for="(v,i) in values" :key="i" class="cell" :class="{active:i===event.cursor,inside:i>=event.windowStart&&i<=event.cursor}">
      <strong>{{v}}</strong><small>下标 {{i}}</small>
    </div>
  </div>
  <p>队列下标：{{event.queueIndices.join(' → ')||'空'}}</p>
  <p>队列数值：{{event.queueIndices.map(i=>values[i]).join(' → ')||'空'}}</p>
  <p>已输出：{{event.output.join(', ')||'暂无'}}</p>
  <p class="message" aria-live="polite">{{event.message}}</p>
  <div class="controls">
    <button @click="prev" :disabled="position===0">上一步</button>
    <button @click="reset">重置</button>
    <button @click="next" :disabled="position===steps.length-1">下一步</button>
    <span>步骤 {{position+1}} / {{steps.length}}</span>
  </div>
</section>
</template>

<style scoped>
.trace-player{font-size:0.8em;outline-offset:5px}.trace-player:focus-visible{outline:3px solid #2563eb}
.track{display:flex;gap:0.4rem;flex-wrap:wrap}.cell{border:2px solid #cbd5e1;border-radius:8px;padding:0.35rem;min-width:3.6rem;text-align:center;background:#f8fafc;color:#0f172a}.cell small{display:block;font-size:0.6em}.cell.inside{border-color:#2563eb}.cell.active{background:#dcfce7;border-color:#15803d}.message{font-weight:600}.controls{display:flex;align-items:center;gap:0.6rem;flex-wrap:wrap}.controls button{border:1px solid #64748b;border-radius:8px;padding:0.3rem 0.6rem;background:white;color:#0f172a;cursor:pointer}.controls button:focus-visible{outline:3px solid #2563eb}.controls button:disabled{opacity:0.4;cursor:not-allowed}
</style>
