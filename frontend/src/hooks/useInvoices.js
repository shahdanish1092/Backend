import { useState, useEffect, useCallback } from 'react';
import { invoicesApi } from '../api';

export function useInvoices() {
  const [invoices, setInvoices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);

  const userEmail = localStorage.getItem('user_email');

  const fetchInvoices = useCallback(async () => {
    if (!userEmail) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const data = await invoicesApi.getInvoices(userEmail);
      setInvoices(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch invoices');
    } finally {
      setIsLoading(false);
    }
  }, [userEmail]);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  const uploadInvoice = useCallback(async (file) => {
    if (!userEmail) return;
    
    setUploadStatus({ status: 'uploading', message: 'Uploading invoice...' });
    try {
      const result = await invoicesApi.uploadInvoice(userEmail, file);
      setUploadStatus({ status: 'success', message: result.message, data: result });
      // Refresh invoices list
      fetchInvoices();
      return result;
    } catch (err) {
      setUploadStatus({ status: 'error', message: err.message || 'Failed to upload invoice' });
      throw err;
    }
  }, [userEmail, fetchInvoices]);

  const clearUploadStatus = useCallback(() => {
    setUploadStatus(null);
  }, []);

  return {
    invoices,
    isLoading,
    error,
    uploadStatus,
    uploadInvoice,
    clearUploadStatus,
    refetch: fetchInvoices,
  };
}
