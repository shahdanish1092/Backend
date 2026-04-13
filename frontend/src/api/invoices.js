import apiClient from './axios';

export const invoicesApi = {
  // Get all invoices for user
  getInvoices: async (userEmail) => {
    try {
      const response = await apiClient.get(`/invoices/${userEmail}`);
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },

  // Upload invoice
  uploadInvoice: async (userEmail, file) => {
    try {
      // Convert file to base64
      const base64 = await fileToBase64(file);
      const response = await apiClient.post('/webhooks/invoice', {
        user_email: userEmail,
        file_base64: base64,
        filename: file.name,
      });
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },
};

// Helper function to convert file to base64
const fileToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = (error) => reject(error);
  });
};
