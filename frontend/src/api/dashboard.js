import apiClient from './axios';

export const dashboardApi = {
  // Get dashboard status and metrics
  getStatus: async (userEmail) => {
    try {
      const response = await apiClient.get(`/status/${userEmail}`);
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },
};
