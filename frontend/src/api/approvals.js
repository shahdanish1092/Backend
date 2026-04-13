import apiClient from './axios';

export const approvalsApi = {
  // Get all pending approvals
  getPendingApprovals: async (userEmail) => {
    try {
      const response = await apiClient.get(`/approvals/${userEmail}`);
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },

  // Submit approval action
  submitApproval: async (token, action, editedData = null) => {
    try {
      const response = await apiClient.post(`/approve/${token}`, {
        action,
        edited_data: editedData,
      });
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },
};
