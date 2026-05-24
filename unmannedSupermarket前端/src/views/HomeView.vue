<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="home-page">
    <el-card class="hero-card">
      <h1>✨ 眸界无感智付系统</h1>
      <p>多模态生物识别 · 毫秒级无感结算</p>
    </el-card>

    <div class="feature-grid">
      <el-card shadow="hover" class="feature-card" @click="router.push('/shopping')">
        <div class="feature-icon">🛒</div>
        <h3>无感购物</h3>
        <p>一键进入 · 无感识别支付</p>
        <el-button type="primary">立即体验</el-button>
      </el-card>
      <el-card shadow="hover" class="feature-card" @click="router.push('/profile')">
        <div class="feature-icon">👤</div>
        <h3>个人中心</h3>
        <p>交易记录 · 账号设置</p>
      </el-card>
    </div>

    <p class="home-tagline">无感支付 · 智能零售 · 适老关怀</p>
  </div>
</template>

<style scoped>
.home-page {
  animation: fadeIn 0.25s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.hero-card {
  text-align: center;
  margin-bottom: 32px;
  border-radius: 20px;
}

.hero-card h1 {
  font-size: 1.8rem;
  margin-bottom: 4px;
}

.hero-card p {
  color: #5A6874;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  max-width: 640px;
  margin: 0 auto 32px;
  gap: 28px;
}

.feature-card {
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s;
  border-radius: 24px;
}

.feature-card:hover {
  transform: translateY(-6px);
}

.feature-icon {
  font-size: 3rem;
  margin-bottom: 8px;
}

.feature-card h3 {
  margin-bottom: 4px;
}

.feature-card p {
  color: #5A6874;
  margin-bottom: 12px;
}

.home-tagline {
  text-align: center;
  color: gray;
  margin-top: 12px;
}

@media (max-width: 600px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style>
