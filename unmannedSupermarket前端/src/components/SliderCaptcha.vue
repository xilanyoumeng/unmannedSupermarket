<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  (e: 'verified', token: string): void
}>()

const trackRef = ref<HTMLDivElement | null>(null)
const sliderLeft = ref(0)
const isDragging = ref(false)
const verified = ref(false)
const startX = ref(0)

function randomToken() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let token = ''
  for (let i = 0; i < 32; i++) {
    token += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return token
}

function onPointerDown(e: PointerEvent) {
  if (verified.value) return
  isDragging.value = true
  startX.value = e.clientX - sliderLeft.value
  const el = trackRef.value
  if (el) {
    el.setPointerCapture(e.pointerId)
  }
}

function onPointerMove(e: PointerEvent) {
  if (!isDragging.value || verified.value) return
  const track = trackRef.value
  if (!track) return
  const trackWidth = track.clientWidth
  const thumbWidth = 44
  const maxLeft = trackWidth - thumbWidth
  const newLeft = e.clientX - startX.value
  sliderLeft.value = Math.max(0, Math.min(newLeft, maxLeft))
}

function onPointerUp(_e: PointerEvent) {
  if (!isDragging.value) return
  isDragging.value = false
  const track = trackRef.value
  if (!track) return
  const trackWidth = track.clientWidth
  const thumbWidth = 44
  const maxLeft = trackWidth - thumbWidth
  if (sliderLeft.value >= maxLeft - 4) {
    sliderLeft.value = maxLeft
    verified.value = true
    emit('verified', randomToken())
  } else {
    sliderLeft.value = 0
  }
}

function refresh() {
  sliderLeft.value = 0
  verified.value = false
}
</script>

<template>
  <div class="slider-captcha">
    <div
      ref="trackRef"
      class="captcha-track"
      :class="{ verified: verified }"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
    >
      <div class="captcha-fill" :style="{ width: sliderLeft + 22 + 'px' }" />
      <div
        class="captcha-thumb"
        :class="{ dragging: isDragging, done: verified }"
        :style="{ left: sliderLeft + 'px' }"
      >
        {{ verified ? '✓' : '→' }}
      </div>
      <span class="captcha-track-text">{{ verified ? '验证通过' : '请按住滑块，拖动到最右边' }}</span>
      <button v-if="!verified" class="captcha-refresh" @click.stop="refresh" title="刷新">↻</button>
    </div>
  </div>
</template>

<style scoped>
.slider-captcha {
  user-select: none;
  width: 100%;
}

.captcha-track {
  position: relative;
  height: 40px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  touch-action: none;
}

.captcha-track.verified {
  border-color: #52c41a;
  background: #f6ffed;
}

.captcha-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  background: linear-gradient(90deg, #e6f7ff, #bae7ff);
  border-radius: 20px 0 0 20px;
  transition: width 0s;
}

.captcha-track.verified .captcha-fill {
  width: 100% !important;
  background: linear-gradient(90deg, #f6ffed, #d9f7be);
  border-radius: 20px;
}

.captcha-track-text {
  position: relative;
  z-index: 1;
  color: #bbb;
  font-size: 0.8rem;
  pointer-events: none;
}

.captcha-thumb {
  position: absolute;
  left: 2px;
  top: 2px;
  width: 36px;
  height: 36px;
  background: #fff;
  border: 2px solid #1677FF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1677FF;
  font-size: 1rem;
  font-weight: 700;
  cursor: grab;
  transition: box-shadow 0.15s;
  z-index: 2;
}

.captcha-thumb.dragging {
  box-shadow: 0 0 0 4px rgba(22, 119, 255, 0.2);
  cursor: grabbing;
}

.captcha-thumb.done {
  border-color: #52c41a;
  color: #52c41a;
  background: #f6ffed;
}

.captcha-refresh {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 3;
  background: none;
  border: none;
  font-size: 1.2rem;
  color: #999;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 50%;
}

.captcha-refresh:hover {
  color: #1677FF;
  background: rgba(22, 119, 255, 0.06);
}
</style>
