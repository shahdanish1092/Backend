import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { ApprovalCard, NoApprovals, CardSkeleton } from '../components';
import { approvalsApi } from '../api';
import { toast } from 'sonner';

export default function ApprovalCenterPage() {
  const [approvals, setApprovals] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const userEmail = localStorage.getItem('user_email');

  const fetchApprovals = async () => {
    setIsLoading(true);
    try {
      const data = await approvalsApi.getPendingApprovals(userEmail);
      setApprovals(data);
    } catch (error) {
      console.error('Failed to fetch approvals:', error);
      toast.error('Failed to load approvals');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, [userEmail]);

  const handleApprove = async (token) => {
    try {
      await approvalsApi.submitApproval(token, 'approve');
      toast.success('Approved successfully');
      setApprovals(approvals.filter(a => a.token !== token));
    } catch (error) {
      toast.error('Failed to approve');
    }
  };

  const handleCancel = async (token) => {
    try {
      await approvalsApi.submitApproval(token, 'cancel');
      toast.success('Cancelled successfully');
      setApprovals(approvals.filter(a => a.token !== token));
    } catch (error) {
      toast.error('Failed to cancel');
    }
  };

  const handleEdit = async (token, editedData) => {
    try {
      await approvalsApi.submitApproval(token, 'approve', editedData);
      toast.success('Approved with edits');
      setApprovals(approvals.filter(a => a.token !== token));
    } catch (error) {
      toast.error('Failed to submit');
    }
  };

  return (
    <div className="space-y-6" data-testid="approval-center-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-outfit font-bold text-slate-900">Approval Center</h1>
        <p className="text-sm text-slate-500 mt-1">Review and approve AI-processed items awaiting your confirmation.</p>
      </div>

      {/* Stats */}
      <Card className="border-slate-200 bg-amber-50">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-amber-800">Pending Approvals</p>
              <p className="text-2xl font-outfit font-bold text-amber-900">{approvals.length}</p>
            </div>
            <div className="text-amber-600">
              {approvals.length > 0 && (
                <span className="text-sm">
                  {approvals.filter(a => a.module === 'Finance').length} Finance, {' '}
                  {approvals.filter(a => a.module === 'Meeting').length} Meeting
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Approvals List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <CardSkeleton key={i} />)}
        </div>
      ) : approvals.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="py-8">
            <NoApprovals />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {approvals.map(approval => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={handleApprove}
              onCancel={handleCancel}
              onEdit={handleEdit}
            />
          ))}
        </div>
      )}
    </div>
  );
}
