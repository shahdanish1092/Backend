import { useState } from 'react';
import { Check, X, Pencil, FileText, Mic } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { formatDistanceToNow } from 'date-fns';

export function ApprovalCard({ approval, onApprove, onCancel, onEdit }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState(approval.ai_output || {});

  const handleSaveEdit = () => {
    onEdit(approval.token, editedData);
    setIsEditing(false);
  };

  const getModuleIcon = () => {
    if (approval.module === 'Finance') return <FileText className="w-4 h-4" />;
    if (approval.module === 'Meeting') return <Mic className="w-4 h-4" />;
    return null;
  };

  const getModuleColor = () => {
    if (approval.module === 'Finance') return 'bg-blue-100 text-blue-800';
    if (approval.module === 'Meeting') return 'bg-purple-100 text-purple-800';
    return 'bg-slate-100 text-slate-800';
  };

  const timeAgo = approval.created_at 
    ? formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })
    : 'Unknown';

  return (
    <Card className="border-slate-200" data-testid={`approval-card-${approval.id}`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Badge className={getModuleColor()}>
                {getModuleIcon()}
                <span className="ml-1">{approval.module}</span>
              </Badge>
              <Badge variant="outline">{approval.type}</Badge>
            </div>
            <CardTitle className="text-lg font-outfit">{approval.id}</CardTitle>
            <p className="text-sm text-slate-500">
              Requested by {approval.requester} • {timeAgo}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* AI Summary */}
        <div className="bg-slate-50 rounded-lg p-4">
          <p className="text-sm font-medium text-slate-700 mb-1">AI Summary</p>
          <p className="text-sm text-slate-600">{approval.ai_summary}</p>
        </div>

        {/* AI Output / Edit Form */}
        {isEditing ? (
          <div className="space-y-3 border rounded-lg p-4">
            <p className="text-sm font-medium text-slate-700">Edit Details</p>
            {approval.module === 'Finance' && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-slate-500">Vendor Name</label>
                    <Input
                      value={editedData.vendor_name || ''}
                      onChange={(e) => setEditedData({ ...editedData, vendor_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-500">Amount</label>
                    <Input
                      type="number"
                      value={editedData.amount || ''}
                      onChange={(e) => setEditedData({ ...editedData, amount: parseFloat(e.target.value) })}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Category</label>
                  <Input
                    value={editedData.category || ''}
                    onChange={(e) => setEditedData({ ...editedData, category: e.target.value })}
                  />
                </div>
              </>
            )}
            {approval.module === 'Meeting' && (
              <>
                <div>
                  <label className="text-xs text-slate-500">Meeting Title</label>
                  <Input
                    value={editedData.meeting_title || ''}
                    onChange={(e) => setEditedData({ ...editedData, meeting_title: e.target.value })}
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Executive Summary</label>
                  <Textarea
                    value={editedData.executive_summary || ''}
                    onChange={(e) => setEditedData({ ...editedData, executive_summary: e.target.value })}
                    rows={3}
                  />
                </div>
              </>
            )}
            <div className="flex gap-2 pt-2">
              <Button size="sm" onClick={handleSaveEdit}>Save Changes</Button>
              <Button size="sm" variant="outline" onClick={() => setIsEditing(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="border rounded-lg p-4 space-y-2">
            <p className="text-sm font-medium text-slate-700">AI Output</p>
            {approval.module === 'Finance' && approval.ai_output && (
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-slate-500">Vendor:</span>{' '}
                  <span className="text-slate-900">{approval.ai_output.vendor_name}</span>
                </div>
                <div>
                  <span className="text-slate-500">Amount:</span>{' '}
                  <span className="text-slate-900 font-medium">${approval.ai_output.amount?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-slate-500">Category:</span>{' '}
                  <span className="text-slate-900">{approval.ai_output.category}</span>
                </div>
                <div>
                  <span className="text-slate-500">Date:</span>{' '}
                  <span className="text-slate-900">{approval.ai_output.date}</span>
                </div>
              </div>
            )}
            {approval.module === 'Meeting' && approval.ai_output && (
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-slate-500">Meeting:</span>{' '}
                  <span className="text-slate-900">{approval.ai_output.meeting_title}</span>
                </div>
                <div>
                  <span className="text-slate-500">Summary:</span>{' '}
                  <span className="text-slate-900">{approval.ai_output.executive_summary}</span>
                </div>
                <div>
                  <span className="text-slate-500">Action Items:</span>{' '}
                  <span className="text-slate-900">{approval.ai_output.action_items?.length || 0} items</span>
                </div>
              </div>
            )}
            {approval.ai_output?.recommended_action && (
              <div className="mt-2 pt-2 border-t">
                <span className="text-xs text-emerald-600 font-medium">
                  Recommendation: {approval.ai_output.recommended_action}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          <Button 
            onClick={() => onApprove(approval.token)}
            className="bg-emerald-500 hover:bg-emerald-600"
            data-testid={`approve-btn-${approval.id}`}
          >
            <Check className="w-4 h-4 mr-1" />
            Approve
          </Button>
          <Button 
            variant="outline" 
            onClick={() => setIsEditing(true)}
            disabled={isEditing}
            data-testid={`edit-btn-${approval.id}`}
          >
            <Pencil className="w-4 h-4 mr-1" />
            Edit
          </Button>
          <Button 
            variant="outline" 
            onClick={() => onCancel(approval.token)}
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
            data-testid={`cancel-btn-${approval.id}`}
          >
            <X className="w-4 h-4 mr-1" />
            Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
