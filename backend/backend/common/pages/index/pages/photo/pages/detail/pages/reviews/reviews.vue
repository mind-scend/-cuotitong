<template>
  <view>
    <view v-for="item in list" :key="item.id" @tap="goDetail(item)">
      <text>{{ item.question }} ({{ item.error_type }})</text>
    </view>
    <button @tap="exportPaper">导出试卷PDF</button>
  </view>
</template>
<script>
import api from '@/common/api.js'
export default {
  data() { return { list: [] } },
  onShow() { this.loadList() },
  methods: {
    async loadList() { this.list = await api.getTodayReviews() },
    goDetail(item) {
      getApp().globalData.selectedRecord = item
      uni.navigateTo({ url: '/pages/detail/detail' })
    },
    async exportPaper() {
      const ids = this.list.map(i => i.id)
      await api.exportPaper(ids)
      uni.showToast({ title: '试卷生成中' })
    }
  }
}
</script>
