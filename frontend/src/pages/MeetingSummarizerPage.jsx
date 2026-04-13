import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../components/ui/collapsible';
import { UploadZone, StatusStepper, TableSkeleton, NoMeetings } from '../components';
import { useMeetings } from '../hooks';
import { Calendar, Eye, ChevronDown, Mail, CalendarDays, CheckSquare, Lightbulb } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const processingSteps = ['Received', 'Transcription', 'AI Analysis', 'Summary Ready'];

const statusColors = {
  completed: 'bg-emerald-100 text-emerald-800',
  pending: 'bg-amber-100 text-amber-800',
  processing: 'bg-blue-100 text-blue-800',
};

export default function MeetingSummarizerPage() {
  const { meetings, isLoading, uploadMeeting, uploadStatus, clearUploadStatus } = useMeetings();
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [transcriptForm, setTranscriptForm] = useState({
    title: '',
    attendees: '',
    transcript: '',
  });

  const handleAudioUpload = useCallback(async (file) => {
    if (!file) return;
    
    setIsUploading(true);
    setCurrentStep(0);

    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= 3) {
          clearInterval(stepInterval);
          return prev;
        }
        return prev + 1;
      });
    }, 1500);

    try {
      // Convert to base64
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = async () => {
        await uploadMeeting({
          type: 'audio',
          content: reader.result.split(',')[1],
          title: file.name.replace(/\.[^/.]+$/, ''),
          attendees: [],
        });
        toast.success('Meeting audio uploaded successfully');
      };
    } catch (error) {
      toast.error('Failed to upload meeting');
    } finally {
      setIsUploading(false);
      setTimeout(() => {
        clearUploadStatus();
        setCurrentStep(0);
      }, 2000);
    }
  }, [uploadMeeting, clearUploadStatus]);

  const handleTranscriptSubmit = async (e) => {
    e.preventDefault();
    if (!transcriptForm.title || !transcriptForm.transcript) {
      toast.error('Please fill in required fields');
      return;
    }

    setIsUploading(true);
    setCurrentStep(0);

    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= 3) {
          clearInterval(stepInterval);
          return prev;
        }
        return prev + 1;
      });
    }, 1000);

    try {
      await uploadMeeting({
        type: 'transcript',
        content: transcriptForm.transcript,
        title: transcriptForm.title,
        attendees: transcriptForm.attendees.split(',').map(a => a.trim()).filter(Boolean),
      });
      toast.success('Transcript submitted successfully');
      setTranscriptForm({ title: '', attendees: '', transcript: '' });
    } catch (error) {
      toast.error('Failed to submit transcript');
    } finally {
      setIsUploading(false);
      setTimeout(() => {
        clearUploadStatus();
        setCurrentStep(0);
      }, 2000);
    }
  };

  return (
    <div className="space-y-6" data-testid="meeting-summarizer-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-outfit font-bold text-slate-900">Meeting Summarizer</h1>
        <p className="text-sm text-slate-500 mt-1">Upload meeting recordings or paste transcripts for AI-powered summaries.</p>
      </div>

      {/* Upload Section */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg font-outfit">New Meeting</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="audio" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="audio" data-testid="audio-tab">Upload Audio</TabsTrigger>
              <TabsTrigger value="transcript" data-testid="transcript-tab">Paste Transcript</TabsTrigger>
            </TabsList>

            <TabsContent value="audio" className="space-y-4">
              <UploadZone
                accept=".mp3,.mp4,.m4a,.wav"
                onFileSelect={handleAudioUpload}
                isUploading={isUploading}
                label="Drop audio file here or click to upload"
                description="Supports MP3, MP4, M4A, WAV files"
              />
            </TabsContent>

            <TabsContent value="transcript" className="space-y-4">
              <form onSubmit={handleTranscriptSubmit} className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-slate-700">Meeting Title *</label>
                  <Input
                    value={transcriptForm.title}
                    onChange={(e) => setTranscriptForm({ ...transcriptForm, title: e.target.value })}
                    placeholder="e.g., Q4 Planning Meeting"
                    className="mt-1"
                    data-testid="meeting-title-input"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700">Attendees</label>
                  <Input
                    value={transcriptForm.attendees}
                    onChange={(e) => setTranscriptForm({ ...transcriptForm, attendees: e.target.value })}
                    placeholder="Comma separated: John Doe, Jane Smith"
                    className="mt-1"
                    data-testid="meeting-attendees-input"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-slate-700">Transcript *</label>
                  <Textarea
                    value={transcriptForm.transcript}
                    onChange={(e) => setTranscriptForm({ ...transcriptForm, transcript: e.target.value })}
                    placeholder="Paste the full meeting transcript here..."
                    rows={8}
                    className="mt-1"
                    data-testid="meeting-transcript-input"
                  />
                </div>
                <Button 
                  type="submit" 
                  className="bg-orange-500 hover:bg-orange-600"
                  disabled={isUploading}
                  data-testid="submit-transcript-btn"
                >
                  Process Transcript
                </Button>
              </form>
            </TabsContent>
          </Tabs>

          {(isUploading || uploadStatus) && (
            <div className="mt-6 p-4 bg-slate-50 rounded-lg">
              <p className="text-sm font-medium text-slate-700 mb-4">Processing Status</p>
              <StatusStepper steps={processingSteps} currentStep={currentStep} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Meeting Log */}
      <Card className="border-slate-200">
        <CardHeader className="border-b border-slate-100">
          <CardTitle className="text-lg font-outfit">Meeting Log</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <TableSkeleton rows={5} columns={5} />
          ) : meetings.length === 0 ? (
            <NoMeetings />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead>Date</TableHead>
                  <TableHead>Meeting Title</TableHead>
                  <TableHead>Action Items</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {meetings.map((meeting) => (
                  <TableRow key={meeting.id} data-testid={`meeting-row-${meeting.id}`}>
                    <TableCell className="text-slate-500">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-slate-400" />
                        {format(new Date(meeting.date), 'MMM d, yyyy')}
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">{meeting.title}</TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {meeting.action_items_count} items
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColors[meeting.status]}>
                        {meeting.status.charAt(0).toUpperCase() + meeting.status.slice(1)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedMeeting(meeting)}
                        disabled={!meeting.summary}
                        data-testid={`view-meeting-btn-${meeting.id}`}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View Summary
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Meeting Summary Modal */}
      <Dialog open={!!selectedMeeting} onOpenChange={() => setSelectedMeeting(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-outfit text-xl">{selectedMeeting?.title}</DialogTitle>
          </DialogHeader>
          {selectedMeeting?.summary && (
            <div className="space-y-6">
              {/* Executive Summary */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Lightbulb className="w-4 h-4 text-orange-500" />
                  <h3 className="font-medium text-slate-900">Executive Summary</h3>
                </div>
                <p className="text-sm text-slate-600 bg-slate-50 p-4 rounded-lg">
                  {selectedMeeting.summary.executive_summary}
                </p>
              </div>

              {/* Action Items */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <CheckSquare className="w-4 h-4 text-emerald-500" />
                  <h3 className="font-medium text-slate-900">Action Items</h3>
                </div>
                <div className="space-y-2">
                  {selectedMeeting.summary.action_items?.map((item, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg">
                      <div className="w-6 h-6 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center text-xs font-medium">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-slate-900">{item.task}</p>
                        <div className="flex gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">{item.owner}</Badge>
                          <Badge variant="outline" className="text-xs">Due: {item.due_date}</Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Key Decisions */}
              {selectedMeeting.summary.key_decisions?.length > 0 && (
                <div>
                  <h3 className="font-medium text-slate-900 mb-2">Key Decisions</h3>
                  <ul className="list-disc list-inside space-y-1">
                    {selectedMeeting.summary.key_decisions.map((decision, index) => (
                      <li key={index} className="text-sm text-slate-600">{decision}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Follow-up Emails */}
              {selectedMeeting.summary.follow_up_emails?.length > 0 && (
                <Collapsible>
                  <CollapsibleTrigger className="flex items-center gap-2 w-full">
                    <Mail className="w-4 h-4 text-blue-500" />
                    <h3 className="font-medium text-slate-900">Draft Follow-up Emails</h3>
                    <ChevronDown className="w-4 h-4 ml-auto" />
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-2 space-y-2">
                    {selectedMeeting.summary.follow_up_emails.map((email, index) => (
                      <div key={index} className="p-3 bg-blue-50 rounded-lg">
                        <p className="text-sm font-medium text-slate-900">To: {email.recipient}</p>
                        <p className="text-sm text-slate-700">Subject: {email.subject}</p>
                        <p className="text-xs text-slate-500 mt-1">{email.preview}</p>
                      </div>
                    ))}
                  </CollapsibleContent>
                </Collapsible>
              )}

              {/* Calendar Invites */}
              {selectedMeeting.summary.calendar_invites?.length > 0 && (
                <Collapsible>
                  <CollapsibleTrigger className="flex items-center gap-2 w-full">
                    <CalendarDays className="w-4 h-4 text-purple-500" />
                    <h3 className="font-medium text-slate-900">Proposed Calendar Invites</h3>
                    <ChevronDown className="w-4 h-4 ml-auto" />
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-2 space-y-2">
                    {selectedMeeting.summary.calendar_invites.map((invite, index) => (
                      <div key={index} className="p-3 bg-purple-50 rounded-lg">
                        <p className="text-sm font-medium text-slate-900">{invite.title}</p>
                        <p className="text-sm text-slate-700">{invite.date}</p>
                        <p className="text-xs text-slate-500">Attendees: {invite.attendees.join(', ')}</p>
                      </div>
                    ))}
                  </CollapsibleContent>
                </Collapsible>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
