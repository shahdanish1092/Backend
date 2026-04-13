import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { DashboardSkeleton } from '../components';
import { dashboardApi } from '../api';
import { 
  FileText, 
  Mic, 
  Clock, 
  Activity,
  CheckCircle,
  XCircle,
  ArrowUpRight,
  Users
} from 'lucide-react';
import { cn } from '@/lib/utils';

const activityIcons = {
  invoice: FileText,
  meeting: Mic,
  approval: CheckCircle,
  hr: Users,
  vendor: Users,
};

const activityColors = {
  invoice: 'text-blue-500 bg-blue-50',
  meeting: 'text-purple-500 bg-purple-50',
  approval: 'text-emerald-500 bg-emerald-50',
  hr: 'text-orange-500 bg-orange-50',
  vendor: 'text-slate-500 bg-slate-50',
};

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const userEmail = localStorage.getItem('user_email');

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const result = await dashboardApi.getStatus(userEmail);
        setData(result);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [userEmail]);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  const stats = [
    {
      title: 'Invoices Processed',
      value: data?.invoices_processed || 0,
      icon: FileText,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      title: 'Meetings Summarized',
      value: data?.meetings_summarized || 0,
      icon: Mic,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
    },
    {
      title: 'Pending Approvals',
      value: data?.pending_approvals || 0,
      icon: Clock,
      color: data?.pending_approvals > 0 ? 'text-amber-600' : 'text-slate-600',
      bgColor: data?.pending_approvals > 0 ? 'bg-amber-50' : 'bg-slate-50',
      highlight: data?.pending_approvals > 0,
    },
    {
      title: 'System Status',
      value: data?.system_status === 'active' ? 'All Active' : 'Check',
      icon: data?.system_status === 'active' ? CheckCircle : XCircle,
      color: data?.system_status === 'active' ? 'text-emerald-600' : 'text-red-600',
      bgColor: data?.system_status === 'active' ? 'bg-emerald-50' : 'bg-red-50',
      isStatus: true,
    },
  ];

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-outfit font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-1">Welcome back! Here's your office automation overview.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <Card 
            key={stat.title} 
            className={cn(
              'border-slate-200',
              stat.highlight && 'ring-2 ring-amber-200'
            )}
            data-testid={`stat-card-${stat.title.toLowerCase().replace(/\s+/g, '-')}`}
          >
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-slate-500 font-medium">{stat.title}</p>
                  <p className={cn(
                    'text-3xl font-outfit font-bold mt-1',
                    stat.isStatus ? stat.color : 'text-slate-900'
                  )}>
                    {stat.value}
                  </p>
                </div>
                <div className={cn('p-3 rounded-lg', stat.bgColor)}>
                  <stat.icon className={cn('w-6 h-6', stat.color)} />
                </div>
              </div>
              {stat.highlight && (
                <Badge className="mt-3 bg-amber-100 text-amber-800 hover:bg-amber-100">
                  Requires attention
                </Badge>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Activity */}
      <Card className="border-slate-200">
        <CardHeader className="border-b border-slate-100">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-outfit">Recent Activity</CardTitle>
            <a 
              href="/approvals" 
              className="text-sm text-orange-600 hover:text-orange-700 flex items-center gap-1"
            >
              View all
              <ArrowUpRight className="w-3 h-3" />
            </a>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="divide-y divide-slate-100">
            {data?.recent_activity?.map((activity, index) => {
              const Icon = activityIcons[activity.type] || Activity;
              const colorClass = activityColors[activity.type] || 'text-slate-500 bg-slate-50';
              const [textColor, bgColor] = colorClass.split(' ');

              return (
                <div 
                  key={index} 
                  className="flex items-center gap-4 py-4"
                  data-testid={`activity-item-${index}`}
                >
                  <div className={cn('p-2 rounded-full', bgColor)}>
                    <Icon className={cn('w-4 h-4', textColor)} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900">{activity.action}</p>
                    <p className="text-sm text-slate-500 truncate">{activity.details}</p>
                  </div>
                  <span className="text-xs text-slate-400 whitespace-nowrap">{activity.time}</span>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
