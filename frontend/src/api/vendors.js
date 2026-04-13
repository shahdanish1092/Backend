import apiClient from './axios';

export const vendorsApi = {
  // Get all approved vendors
  getVendors: async (userEmail) => {
    try {
      const response = await apiClient.get(`/admin/vendors/${userEmail}`);
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },

  // Add or remove vendor
  manageVendor: async (userEmail, vendorName, action) => {
    try {
      const response = await apiClient.post('/admin/vendors', {
        user_email: userEmail,
        vendor_name: vendorName,
        action,
      });
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },
};
