export interface Step {
  step: number;
  title: string;
  body: string;
  tip?: string;
}

export interface BeforeYouStart {
  title: string;
  subtitle: string;
  steps: Step[];
  emergencyLinkText: string;
}

export interface Habit {
  num: number;
  title: string;
  body: string;
}

export interface Category {
  id: string;
  title: string;
  guidelines: string[];
}

export interface Resource {
  name: string;
  number: string;
  description: string;
}

export interface GuidanceSection {
  id: string;
  title: string;
  shortIntro?: string;
  details?: string;
  intro?: string;
  habits?: Habit[];
  categories?: Category[];
  mistakes?: string[];
  resources?: Resource[];
}

export const QUICK_EXIT_URL: string;
export const disclaimer: { text: string };
export const quickExitNotice: {
  title: string;
  summary: string;
  warning: string;
  privacyTips: string[];
};
export const beforeYouStart: BeforeYouStart;
export const guidanceSections: GuidanceSection[];
