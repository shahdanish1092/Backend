import apiClient from './axios';

export const hrApi = {
  // Get HR connection status
  getHRStatus: async (userEmail) => {
    try {
      const response = await apiClient.get(`/hr/status/${userEmail}`);
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },

  // Connect HR webhook
  connectHR: async (userEmail, config) => {
    try {
      const response = await apiClient.post('/webhooks/hr', {
        user_email: userEmail,
        hr_webhook_url: config.webhookUrl,
        input_format: config.inputFormat,
        callback_url: config.callbackUrl,
        secret: config.secret,
      });
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },

  // Test HR connection
  testConnection: async (userEmail) => {
    try {
      const response = await apiClient.post(`/hr/test/${userEmail}`);
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },

  // Disconnect HR
  disconnectHR: async (userEmail) => {
    try {
      const response = await apiClient.delete(`/hr/disconnect/${userEmail}`);
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },
};
