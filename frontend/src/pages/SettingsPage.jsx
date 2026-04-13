import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Switch } from '../components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Separator } from '../components/ui/separator';
import { NoVendors, TableSkeleton } from '../components';
import { vendorsApi } from '../api';
import { 
  Mail, 
  RefreshCw, 
  Trash2, 
  Plus, 
  Check,
  X,
  Linkedin
} from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

export default function SettingsPage() {
  const [vendors, setVendors] = useState([]);
  const [isLoadingVendors, setIsLoadingVendors] = useState(true);
  const [showAddVendor, setShowAddVendor] = useState(false);
  const [newVendorName, setNewVendorName] = useState('');
  const [notifications, setNotifications] = useState({
    approvalEmail: localStorage.getItem('notify_approvals') === 'true',
    dailyBriefing: localStorage.getItem('notify_briefing') === 'true',
  });
  const userEmail = localStorage.getItem('user_email');

  const fetchVendors = async () => {
    setIsLoadingVendors(true);
    try {
      const data = await vendorsApi.getVendors(userEmail);
      setVendors(data);
    } catch (error) {
      console.error('Failed to fetch vendors:', error);
    } finally {
      setIsLoadingVendors(false);
    }
  };

  useEffect(() => {
    fetchVendors();
  }, [userEmail]);

  const handleAddVendor = async () => {
    if (!newVendorName.trim()) {
      toast.error('Please enter a vendor name');
      return;
    }

    try {
      await vendorsApi.manageVendor(userEmail, newVendorName, 'add');
      setVendors([...vendors, { 
        id: `VND-${Date.now()}`, 
        name: newVendorName, 
        added_date: new Date().toISOString().split('T')[0] 
      }]);
      setNewVendorName('');
      setShowAddVendor(false);
      toast.success('Vendor added successfully');
    } catch (error) {
      toast.error('Failed to add vendor');
    }
  };

  const handleRemoveVendor = async (vendorId, vendorName) => {
    try {
      await vendorsApi.manageVendor(userEmail, vendorName, 'remove');
      setVendors(vendors.filter(v => v.id !== vendorId));
      toast.success('Vendor removed');
    } catch (error) {
      toast.error('Failed to remove vendor');
    }
  };

  const handleNotificationChange = (key, value) => {
    setNotifications({ ...notifications, [key]: value });
    localStorage.setItem(key === 'approvalEmail' ? 'notify_approvals' : 'notify_briefing', value.toString());
    toast.success('Preference saved');
  };

  const handleReconnectGoogle = () => {
    // In production, this would redirect to OAuth
    toast.success('Google account reconnected');
  };

  return (
    <div className="space-y-6" data-testid="settings-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-outfit font-bold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500 mt-1">Manage your account settings and preferences.</p>
      </div>

      {/* Connected Accounts */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg font-outfit">Connected Accounts</CardTitle>
          <CardDescription>Manage your connected services and integrations.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Google Account */}
          <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm">
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">Google</p>
                <p className="text-xs text-slate-500">{userEmail}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge className="bg-emerald-100 text-emerald-800">Connected</Badge>
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleReconnectGoogle}
                data-testid="reconnect-google-btn"
              >
                <RefreshCw className="w-4 h-4 mr-1" />
                Reconnect
              </Button>
            </div>
          </div>

          {/* LinkedIn (Coming Soon) */}
          <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg opacity-60">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm">
                <Linkedin className="w-5 h-5 text-[#0077B5]" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">LinkedIn</p>
                <p className="text-xs text-slate-500">Connect for professional features</p>
              </div>
            </div>
            <Badge variant="outline">Coming Soon</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Approved Vendors */}
      <Card className="border-slate-200">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-outfit">Approved Vendors</CardTitle>
              <CardDescription>Manage vendors for automatic invoice categorization.</CardDescription>
            </div>
            <Button 
              size="sm"
              onClick={() => setShowAddVendor(true)}
              className="bg-orange-500 hover:bg-orange-600"
              data-testid="add-vendor-btn"
            >
              <Plus className="w-4 h-4 mr-1" />
              Add Vendor
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {/* Add Vendor Form */}
          {showAddVendor && (
            <div className="px-6 py-4 border-b bg-slate-50">
              <div className="flex gap-2">
                <Input
                  value={newVendorName}
                  onChange={(e) => setNewVendorName(e.target.value)}
                  placeholder="Enter vendor name"
                  className="flex-1"
                  data-testid="new-vendor-input"
                />
                <Button 
                  size="icon"
                  onClick={handleAddVendor}
                  className="bg-emerald-500 hover:bg-emerald-600"
                  data-testid="confirm-add-vendor-btn"
                >
                  <Check className="w-4 h-4" />
                </Button>
                <Button 
                  size="icon"
                  variant="outline"
                  onClick={() => { setShowAddVendor(false); setNewVendorName(''); }}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}

          {isLoadingVendors ? (
            <TableSkeleton rows={3} columns={3} />
          ) : vendors.length === 0 ? (
            <NoVendors />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead>Vendor Name</TableHead>
                  <TableHead>Date Added</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {vendors.map((vendor) => (
                  <TableRow key={vendor.id} data-testid={`vendor-row-${vendor.id}`}>
                    <TableCell className="font-medium">{vendor.name}</TableCell>
                    <TableCell className="text-slate-500">
                      {format(new Date(vendor.added_date), 'MMM d, yyyy')}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveVendor(vendor.id, vendor.name)}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        data-testid={`remove-vendor-btn-${vendor.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Notification Preferences */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg font-outfit">Notification Preferences</CardTitle>
          <CardDescription>Configure how you want to receive notifications.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                <Mail className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">Approval Notifications</p>
                <p className="text-xs text-slate-500">Email me when an item requires approval</p>
              </div>
            </div>
            <Switch
              checked={notifications.approvalEmail}
              onCheckedChange={(checked) => handleNotificationChange('approvalEmail', checked)}
              data-testid="approval-notification-toggle"
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Mail className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">Daily Briefing</p>
                <p className="text-xs text-slate-500">Receive a daily summary of processed items</p>
              </div>
            </div>
            <Switch
              checked={notifications.dailyBriefing}
              onCheckedChange={(checked) => handleNotificationChange('dailyBriefing', checked)}
              data-testid="briefing-notification-toggle"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
