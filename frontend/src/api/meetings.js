import apiClient from './axios';

export const meetingsApi = {
  // Get all meetings for user
  getMeetings: async (userEmail) => {
    try {
      const response = await apiClient.get(`/meetings/${userEmail}`);
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },

  // Upload meeting audio or transcript
  uploadMeeting: async (userEmail, data) => {
    try {
      const response = await apiClient.post('/webhooks/meeting', {
        user_email: userEmail,
        type: data.type,
        content: data.content,
        title: data.title,
        attendees: data.attendees,
      });
      return response.data;
    } catch (error) {
      console.error('API error:', error);
      throw error;
    }
  },
};
