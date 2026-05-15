<template>
  <view>
    <view v-if="imagePath"><image :src="imagePath" mode="widthFix"></image></view>
    <button @tap="takePhoto" v-if="!imagePath">拍照</button>
    <button @tap="analyze" :disabled="analyzing" v-if="imagePath">
      {{ analyzing ? '分析中...' : '开始分析' }}
    </button>
    <view v-if="result">
      <text>原题：{{ result.clean_question }}</text>
      <text>错误原因：{{ result.error_reason }}</text>
      <button @tap="goDetail(result)">查看变式题与解答</button>
    </view>
  </view>
</template>
<script>
import api from '@/common/api.js'
export default {
  data() { return { imagePath: '', analyzing: false, result: null } },
  methods: {
    takePhoto() {
      uni.chooseImage({ count: 1, sourceType: ['camera'], success: (res) => {
        this.imagePath = res.tempFilePaths[0]
      }})
    },
    async analyze() {
      this.analyzing = true
      this.result = await api.analyzeMistake(this.imagePath, 'math')
      this.analyzing = false
    },
    goDetail(record) {
      getApp().globalData.selectedRecord = record
      uni.navigateTo({ url: '/pages/detail/detail' })
    }
  }
}
</script>
