/**
 * Evidence AI - Guidance & Awareness Content
 * 
 * NOTE ON LOCALIZATION (i18n):
 * This file is structured with key-value dictionaries to allow smooth localization.
 * Do NOT use automated / machine translation for trauma-informed and legal guidance.
 * Tamil (ta) and Hindi (hi) translations need verified human translation by native
 * speakers or support advocates before being published.
 */

export const QUICK_EXIT_URL = 'https://www.google.com';

export const disclaimer = {
  text: 'Everything here is general information, not legal advice. Laws and legal procedures vary by jurisdiction and situation. If you are in immediate physical danger, contact emergency services right away.',
};

export const quickExitNotice = {
  title: 'About Quick exit & browsing safety',
  summary: 'The "Quick exit" button immediately redirects you to Google and replaces your current page in your browser navigation history so the Back button will not bring you back here.',
  warning: 'Quick exit does not erase your browser history, downloaded files, or device logs.',
  privacyTips: [
    'Use Private Browsing or Incognito mode so pages you visit are not saved to your device history.',
    'To clear browsing history in Google Chrome, Microsoft Edge, or Mozilla Firefox, press Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac) and choose to remove browsing history.',
    'If someone monitors your device, consider viewing and storing your evidence on a device only you have access to.'
  ]
};

export const beforeYouStart = {
  title: 'Before you start',
  subtitle: 'A few quiet reminders to help protect you.',
  steps: [
    {
      step: 1,
      title: 'Your safety comes first.',
      body: 'If you share a device or accounts with someone who may be monitoring you, consider using a device and accounts only you control. Evidence you keep here stays on this device.',
      tip: 'You can exit this app at any time by clicking "Quick exit" or pressing the Escape key twice.'
    },
    {
      step: 2,
      title: "You don't have to confront anyone.",
      body: 'Collecting evidence does not mean replying, warning, or arguing with the person. Staying quiet is often safer.',
      tip: 'You can quietly gather what you need without letting the other person know.'
    },
    {
      step: 3,
      title: 'Go at your own pace.',
      body: 'You can stop and come back any time. You can also ask a trusted person to sit with you while you do this.',
      tip: 'You do not have to finish everything today. Take breaks whenever you need to.'
    }
  ],
  emergencyLinkText: 'Get help now'
};

export const guidanceSections = [
  {
    id: 'start-here',
    title: 'Start here',
    shortIntro: 'Evidence helps when you report to the police, a lawyer, your employer or a platform. You don\'t need to collect everything at once. Start with what you already have.',
    details: 'Take things step by step. Everything you store in Evidence AI is saved directly on your computer and is never uploaded to external servers.'
  },
  {
    id: 'five-habits',
    title: 'Five habits that protect your evidence',
    intro: 'Following these five simple habits helps ensure your files remain credible and legally sound.',
    habits: [
      {
        num: 1,
        title: 'Keep the original',
        body: 'Don\'t edit, crop, rename or forward it as your only copy. Add the original file here and keep it untouched.'
      },
      {
        num: 2,
        title: 'Show the full picture',
        body: 'Capture the whole screen or chat, including the name or number, date, time and the link or app. A message with no context is hard to prove.'
      },
      {
        num: 3,
        title: "Don't delete anything",
        body: 'Even painful messages, accounts, or chats. Deleted items can be hard or impossible to recover.'
      },
      {
        num: 4,
        title: 'Save it in more than one place',
        body: 'Keep a second copy somewhere only you can access.'
      },
      {
        num: 5,
        title: 'Write notes soon',
        body: 'Within a day, if you can, write what happened, when, and how it affected you, in your own words with dates.'
      }
    ]
  },
  {
    id: 'what-to-save',
    title: 'What to save, by type',
    intro: 'Different kinds of evidence have different best practices for preservation.',
    categories: [
      {
        id: 'screenshots-images',
        title: 'Screenshots and images',
        guidelines: [
          'Capture the entire screen, not just the worst part.',
          'Include the sender\'s name, username or number, and the date and time.',
          'Save the link to the profile, post or page as well (copy the web address).',
          'For disappearing messages or stories, capture them straight away.',
          'Take screenshots of the whole conversation, not only selected messages.'
        ]
      },
      {
        id: 'audio-recordings',
        title: 'Audio (voicemails, voice notes, recorded calls)',
        guidelines: [
          'Save the original audio file where possible instead of recording it with another phone.',
          'Note when and how you received it, and who you believe the speaker is.',
          'Laws about recording calls differ. Ask a lawyer or legal aid before relying on a call you recorded yourself.'
        ]
      },
      {
        id: 'chats-emails-documents',
        title: 'Chats, emails and documents',
        guidelines: [
          'Use the app\'s "Export chat" feature for chats such as WhatsApp when available.',
          'For email, save the original message file (with headers) when your email app allows it, not only a screenshot or a forward.',
          'Keep PDFs, invoices and documents in their original form.'
        ]
      },
      {
        id: 'money-fraud',
        title: 'Money and fraud',
        guidelines: [
          'Save bank statements, transaction IDs or reference numbers, payment receipts, invoices, account numbers and UPI IDs the money went to, and any messages around the payment.',
          'Record dates and amounts in your notes.'
        ]
      },
      {
        id: 'social-media-websites',
        title: 'Social media and websites',
        guidelines: [
          'Save the web address, the account name and the account link, plus screenshots.',
          'Do not interact with the account or message the person.'
        ]
      }
    ]
  },
  {
    id: 'common-mistakes',
    title: 'Common mistakes to avoid',
    intro: 'Small accidental actions can weaken or invalidate digital records. Here is what to avoid:',
    mistakes: [
      'Editing, cropping or marking up the only copy of an image.',
      'Saving only the worst message and deleting the rest of the conversation.',
      'Relying on a forwarded message or a re-shared link when you could save the original file.',
      'Deleting an app, chat, or account before backing up screenshots and chat exports.',
      'Waiting weeks before recording notes, which causes dates and context to blur.',
      'Confronting or tipping off the person that you are saving evidence, which may prompt them to delete evidence or change profile settings.'
    ]
  },
  {
    id: 'emergency-help',
    title: 'Emergency help & resources',
    intro: 'If you are in danger right now, please protect yourself first. The following support lines are confidential and available:',
    resources: [
      {
        name: 'National Emergency Response Support',
        number: '112',
        description: 'Toll-free 24/7 all-in-one emergency service for police, fire, and health emergencies.'
      },
      {
        name: 'National Cyber Crime Reporting Helpline',
        number: '1930',
        description: 'Assistance for online financial fraud, stalking, non-consensual images, and digital harassment. Portal: cybercrime.gov.in'
      },
      {
        name: 'Women in Distress Helpline',
        number: '1091 / 181',
        description: '24/7 dedicated confidential counseling, police assistance, and shelter support for women.'
      },
      {
        name: 'Tele-MANAS Mental Health Support',
        number: '14416 / 1800-891-4416',
        description: 'Free 24/7 counseling and emotional support provided by trained mental health professionals.'
      },
      {
        name: 'National Child Helpline',
        number: '1098',
        description: '24-hour free emergency service for children in distress or facing exploitation.'
      },
      {
        name: 'Free Legal Aid (NALSA)',
        number: '15100',
        description: 'Free legal counseling, legal representation, and dispute assistance for eligible victims.'
      }
    ]
  }
];
