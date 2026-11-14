import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, ArrowRight, ArrowLeft, X, HeartHandshake, LifeBuoy } from 'lucide-react';
import { beforeYouStart } from '../../content/guidance.js';
import { Button } from './Button';

const STORAGE_KEY = 'evidence_ai_safety_onboarding_completed';

export const SafetyModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const navigate = useNavigate();

  useEffect(() => {
    const isCompleted = localStorage.getItem(STORAGE_KEY);
    if (!isCompleted) {
      setIsOpen(true);
    }

    const handleOpenRequest = () => {
      setCurrentStep(0);
      setIsOpen(true);
    };

    window.addEventListener('evidence-ai-open-safety-modal', handleOpenRequest);
    return () => {
      window.removeEventListener('evidence-ai-open-safety-modal', handleOpenRequest);
    };
  }, []);

  const handleComplete = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    setIsOpen(false);
  };

  const handleEmergencyClick = () => {
    handleComplete();
    navigate('/guide#emergency-help');
  };

  if (!isOpen) return null;

  const totalSteps = beforeYouStart.steps.length;
  const stepData = beforeYouStart.steps[currentStep];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="safety-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-stone-900/50 backdrop-blur-[1px] transition-opacity"
        onClick={handleComplete}
      />

      {/* Dialog Surface */}
      <div className="relative w-full max-w-lg bg-white border border-[#E6E4DF] rounded-lg shadow-xl p-6 z-10 text-[#1C1917] space-y-5 animate-in fade-in zoom-in-95 duration-150">
        {/* Header bar */}
        <div className="flex items-center justify-between border-b border-[#F0EFEB] pb-3">
          <div className="flex items-center gap-2">
            <span className="p-1 rounded bg-[#E6F4F1] text-[#0F766E]">
              <Shield className="w-4 h-4" />
            </span>
            <span className="text-xs font-semibold uppercase tracking-wider text-[#6B6862]">
              {beforeYouStart.title} • Step {currentStep + 1} of {totalSteps}
            </span>
          </div>

          <button
            onClick={handleComplete}
            aria-label="Skip safety introduction"
            className="text-xs text-[#6B6862] hover:text-[#1C1917] hover:underline flex items-center gap-1 p-1"
          >
            <span>Skip</span>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Step Content */}
        <div className="space-y-3 py-1">
          <h2
            id="safety-modal-title"
            className="text-base font-semibold text-[#1C1917]"
          >
            {stepData.title}
          </h2>

          <p className="text-sm text-[#44403C] leading-relaxed">
            {stepData.body}
          </p>

          {stepData.tip && (
            <div className="p-3 bg-[#FBFBF9] border border-[#E6E4DF] rounded text-xs text-[#57534E] leading-normal">
              {stepData.tip}
            </div>
          )}
        </div>

        {/* Emergency Help Link */}
        <div className="pt-1 flex items-center justify-between text-xs">
          <button
            type="button"
            onClick={handleEmergencyClick}
            className="text-[#0F766E] hover:text-[#0D655E] font-medium flex items-center gap-1.5 underline decoration-[#0F766E]/40 hover:decoration-[#0F766E]"
          >
            <LifeBuoy className="w-3.5 h-3.5" />
            <span>{beforeYouStart.emergencyLinkText} (Helplines)</span>
          </button>

          {/* Dots Indicator */}
          <div className="flex items-center gap-1.5" aria-hidden="true">
            {beforeYouStart.steps.map((_, idx) => (
              <span
                key={idx}
                className={`h-1.5 rounded-full transition-all ${
                  idx === currentStep ? 'w-5 bg-[#0F766E]' : 'w-1.5 bg-[#E6E4DF]'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between pt-3 border-t border-[#F0EFEB]">
          <div>
            {currentStep > 0 ? (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setCurrentStep((prev) => prev - 1)}
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleComplete}
              >
                <span>Skip all</span>
              </Button>
            )}
          </div>

          <div>
            {currentStep < totalSteps - 1 ? (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setCurrentStep((prev) => prev + 1)}
              >
                <span>Next</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={handleComplete}
              >
                <span>I understand, continue</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
