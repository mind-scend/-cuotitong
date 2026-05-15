<template>
  <view v-if="record">
    <view><text>正确答案：</text><rich-text :nodes="record.correct_solution"></rich-text></view>
    <view v-for="(v,key) in record.variants" :key="key">
      <text>{{ {basic:'基础巩固',medium:'中等变形',hard:'拓展挑战'}[key] }}</text>
      <text>{{ v.question }}</text>
      <text @tap="show[key]=!show[key]">{{ show[key] ? v.answer : '点击显示答案' }}</text>
    </view>
    <button @tap="markReview">已复习</button>
  </view>
</template>
<script>
import api from '@/common/api.js'
export default {
  data() { return { record: null, show: {} } },
  onLoad() { this.record = getApp().globalData.selectedRecord },
  methods: {
    async markReview() {
      await api.markReviewDone(this.record.record_id)
      uni.showToast({ title: '记录成功' })
      uni.navigateBack()
    }
  }
}
</script>
