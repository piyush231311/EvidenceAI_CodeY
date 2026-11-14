import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';
import { Button } from './Button';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 max-w-2xl mx-auto my-12 bg-white rounded-lg border border-red-200 shadow-sm text-stone-900">
          <div className="flex items-start gap-4">
            <div className="p-2.5 bg-red-50 text-red-700 rounded-lg border border-red-100 flex-shrink-0">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-bold text-stone-900 font-serif">
                {this.props.fallbackTitle || 'Analysis View Interrupted'}
              </h2>
              <p className="text-sm text-stone-600 mt-1">
                {this.props.fallbackMessage ||
                  'An unexpected rendering issue occurred while displaying case analysis data. Your evidence files and database records are safe.'}
              </p>

              {this.state.error && (
                <div className="mt-4 p-3 bg-stone-50 rounded border border-stone-200 text-xs font-mono text-red-800 break-words overflow-x-auto">
                  {this.state.error.toString()}
                </div>
              )}

              <div className="flex items-center gap-3 mt-6">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={this.handleReload}
                  className="bg-[#0F766E] hover:bg-[#0D655E] text-white flex items-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Reload Page</span>
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={this.handleReset}
                  className="border-[#E6E4DF] text-stone-700 hover:bg-stone-50"
                >
                  <span>Try Again</span>
                </Button>
                <a
                  href="/cases"
                  className="inline-flex items-center gap-1.5 text-xs text-[#0F766E] hover:underline ml-auto font-medium"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Cases</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
