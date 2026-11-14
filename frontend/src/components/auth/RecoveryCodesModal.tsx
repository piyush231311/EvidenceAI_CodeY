import React, { useState } from 'react';
import { ShieldAlert, Copy, Download, Check, KeyRound } from 'lucide-react';
import { Button } from '../common/Button';

interface RecoveryCodesModalProps {
  codes: string[];
  onComplete: () => void;
  title?: string;
}

export const RecoveryCodesModal: React.FC<RecoveryCodesModalProps> = ({
  codes,
  onComplete,
  title = "Save your recovery codes"
}) => {
  const [copied, setCopied] = useState<boolean>(false);
  const [confirmed, setConfirmed] = useState<boolean>(false);

  const formattedCodesText = `Evidence AI - Account Recovery Codes
====================================
Keep these 8 one-time recovery codes in a safe, private place.
If you lose your password, each code can be used once to regain access.

${codes.map((c, i) => `${i + 1}. ${c}`).join('\n')}

Generated: ${new Date().toISOString()}
`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedCodesText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = formattedCodesText;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([formattedCodesText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'evidence-ai-recovery-codes.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-[#1C1917]/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white border border-[#E6E4DF] rounded-lg max-w-lg w-full p-6 shadow-xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded bg-[#F0FDF4] border border-[#DCFCE7] flex items-center justify-center shrink-0 mt-0.5">
            <KeyRound className="w-5 h-5 text-[#0F766E]" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-[#1C1917]">{title}</h2>
            <p className="text-xs text-[#57534E] mt-1 leading-relaxed">
              If you forget your password, these codes are the <span className="font-semibold text-[#1C1917]">only</span> way to regain access. We cannot reset your password for you. Save them in a safe place (a password manager, a hidden note, or write them down).
            </p>
          </div>
        </div>

        {/* Monospace Code Grid */}
        <div className="bg-[#FAF9F5] border border-[#E6E4DF] rounded-md p-4">
          <div className="grid grid-cols-2 gap-2.5">
            {codes.map((code, idx) => (
              <div
                key={idx}
                className="font-mono text-xs text-[#1C1917] bg-white border border-[#E6E4DF] px-3 py-2 rounded text-center tracking-wider select-all font-medium"
              >
                {code}
              </div>
            ))}
          </div>
        </div>

        {/* Copy & Download Actions */}
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleCopy}
            className="flex-1"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-700">Copied to clipboard</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span>Copy all codes</span>
              </>
            )}
          </Button>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleDownload}
            className="flex-1"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download text file</span>
          </Button>
        </div>

        {/* Confirmation Checkbox */}
        <div className="pt-2 border-t border-[#E6E4DF]">
          <label className="flex items-start gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-[#DCDAD4] text-[#0F766E] focus:ring-[#0F766E]"
            />
            <span className="text-xs text-[#44403C] leading-normal font-medium">
              I have saved these codes in a safe place.
            </span>
          </label>
        </div>

        {/* Continue Button */}
        <div>
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={onComplete}
            disabled={!confirmed}
            className="w-full justify-center"
          >
            Continue to my dashboard
          </Button>
        </div>
      </div>
    </div>
  );
};
