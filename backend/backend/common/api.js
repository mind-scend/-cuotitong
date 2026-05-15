const BASE_URL = 'http://你的服务器IP:5000/api'

const request = (url, options = {}) => {
  const token = uni.getStorageSync('token')
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      header: { 'Authorization': token || '' },
      ...options,
      success: (res) => res.statusCode === 200 ? resolve(res.data) : reject(res.data),
      fail: reject
    })
  })
}

export default {
  register: (data) => request('/register', { method: 'POST', data }),
  login: (data) => request('/login', { method: 'POST', data }),
  analyzeMistake: (imagePath, subject = 'math') => new Promise((resolve, reject) => {
    uni.uploadFile({
      url: BASE_URL + '/analyze',
      filePath: imagePath,
      name: 'image',
      formData: { subject },
      header: { 'Authorization': uni.getStorageSync('token') },
      success: (res) => resolve(JSON.parse(res.data)),
      fail: reject
    })
  }),
  getTodayReviews: () => request('/reviews/today'),
  markReviewDone: (id) => request(`/review/${id}/done`, { method: 'POST' }),
  exportPaper: (recordIds) => request('/export_paper', {
    method: 'POST',
    data: { record_ids: recordIds },
    responseType: 'arraybuffer'
  })
}
