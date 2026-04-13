import { useState, useEffect, useCallback } from 'react';
import { meetingsApi } from '../api';

export function useMeetings() {
  const [meetings, setMeetings] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);

  const userEmail = localStorage.getItem('user_email');

  const fetchMeetings = useCallback(async () => {
    if (!userEmail) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const data = await meetingsApi.getMeetings(userEmail);
      setMeetings(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch meetings');
    } finally {
      setIsLoading(false);
    }
  }, [userEmail]);

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  const uploadMeeting = useCallback(async (data) => {
    if (!userEmail) return;
    
    setUploadStatus({ status: 'uploading', message: 'Processing meeting...' });
    try {
      const result = await meetingsApi.uploadMeeting(userEmail, data);
      setUploadStatus({ status: 'success', message: result.message, data: result });
      // Refresh meetings list
      fetchMeetings();
      return result;
    } catch (err) {
      setUploadStatus({ status: 'error', message: err.message || 'Failed to upload meeting' });
      throw err;
    }
  }, [userEmail, fetchMeetings]);

  const clearUploadStatus = useCallback(() => {
    setUploadStatus(null);
  }, []);

  return {
    meetings,
    isLoading,
    error,
    uploadStatus,
    uploadMeeting,
    clearUploadStatus,
    refetch: fetchMeetings,
  };
}
