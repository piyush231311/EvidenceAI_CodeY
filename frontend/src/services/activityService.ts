import { ActivityRecord, ActivityAction } from '../types';
import { INITIAL_ACTIVITIES } from '../data/mockData';

export interface IActivityService {
  getActivities(caseId?: string, actionType?: ActivityAction): Promise<ActivityRecord[]>;
  logActivity(activity: Omit<ActivityRecord, 'id' | 'timestamp'>): Promise<ActivityRecord>;
}

class MockActivityService implements IActivityService {
  private activities: ActivityRecord[] = [...INITIAL_ACTIVITIES];

  async getActivities(caseId?: string, actionType?: ActivityAction): Promise<ActivityRecord[]> {
    return new Promise((resolve) => {
      let filtered = [...this.activities];
      if (caseId) {
        filtered = filtered.filter((a) => a.caseId === caseId);
      }
      if (actionType) {
        filtered = filtered.filter((a) => a.action === actionType);
      }
      setTimeout(() => resolve(filtered), 80);
    });
  }

  async logActivity(activity: Omit<ActivityRecord, 'id' | 'timestamp'>): Promise<ActivityRecord> {
    return new Promise((resolve) => {
      const record: ActivityRecord = {
        ...activity,
        id: `act-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
        timestamp: new Date().toISOString()
      };
      this.activities.unshift(record);
      setTimeout(() => resolve(record), 50);
    });
  }
}

export const activityService = new MockActivityService();
