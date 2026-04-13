import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export function StatusStepper({ steps, currentStep }) {
  return (
    <div className="flex items-center w-full" data-testid="status-stepper">
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;
        const isLast = index === steps.length - 1;

        return (
          <div key={step} className="flex items-center flex-1">
            {/* Step circle */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all',
                  isCompleted && 'bg-emerald-500 text-white',
                  isCurrent && 'bg-orange-500 text-white ring-4 ring-orange-100',
                  !isCompleted && !isCurrent && 'bg-slate-200 text-slate-500'
                )}
              >
                {isCompleted ? (
                  <Check className="w-4 h-4" />
                ) : (
                  index + 1
                )}
              </div>
              <span 
                className={cn(
                  'mt-2 text-xs font-medium text-center max-w-[80px]',
                  isCurrent ? 'text-orange-600' : 'text-slate-500'
                )}
              >
                {step}
              </span>
            </div>

            {/* Connector line */}
            {!isLast && (
              <div 
                className={cn(
                  'flex-1 h-0.5 mx-2 transition-all',
                  isCompleted ? 'bg-emerald-500' : 'bg-slate-200'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
