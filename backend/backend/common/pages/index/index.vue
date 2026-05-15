<template>
  <view class="container">
    <input v-model="username" placeholder="用户名" />
    <input v-model="password" type="password" placeholder="密码" />
    <button @tap="doLogin">登录</button>
    <button @tap="doRegister">注册</button>
  </view>
</template>
<script>
import api from '@/common/api.js'
export default {
  data() { return { username: '', password: '' } },
  methods: {
    async doLogin() {
      const res = await api.login({ username: this.username, password: this.password })
      uni.setStorageSync('token', res.token)
      uni.switchTab({ url: '/pages/photo/photo' })
    },
    async doRegister() {
      const res = await api.register({ username: this.username, password: this.password })
      uni.setStorageSync('token', res.token)
      uni.switchTab({ url: '/pages/photo/photo' })
    }
  }
}
</script>
