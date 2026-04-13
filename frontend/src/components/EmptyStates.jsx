import { FileX, Inbox, Calendar, Users } from 'lucide-react';

export function EmptyState({ 
  icon: Icon = Inbox, 
  title = 'No data found', 
  description = 'There is nothing to display here yet.',
  action = null 
}) {
  return (
    <div 
      className="flex flex-col items-center justify-center py-12 px-4 text-center"
      data-testid="empty-state"
    >
      <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-slate-400" />
      </div>
      <h3 className="text-lg font-medium text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 max-w-sm">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function NoInvoices() {
  return (
    <EmptyState
      icon={FileX}
      title="No invoices yet"
      description="Upload your first invoice to get started with automated processing."
    />
  );
}

export function NoMeetings() {
  return (
    <EmptyState
      icon={Calendar}
      title="No meetings recorded"
      description="Upload a meeting audio file or paste a transcript to generate AI-powered summaries."
    />
  );
}

export function NoApprovals() {
  return (
    <EmptyState
      icon={Inbox}
      title="All caught up!"
      description="There are no pending approvals at the moment. Check back later."
    />
  );
}

export function NoVendors() {
  return (
    <EmptyState
      icon={Users}
      title="No vendors added"
      description="Add approved vendors to automatically categorize and process invoices."
    />
  );
}
